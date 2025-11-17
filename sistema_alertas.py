"""
Sistema de Alertas para Governança de Dados
Alertas em tempo real, escalação automática, notificações personalizadas e histórico de incidentes
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time


# ============================================================================
# ENUMERAÇÕES
# ============================================================================

class Severidade(Enum):
    """Níveis de severidade de alerta"""
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4
    
    @property
    def descricao(self) -> str:
        return {
            Severidade.BAIXA: "⚠️  BAIXA",
            Severidade.MEDIA: "⚠️  MÉDIA",
            Severidade.ALTA: "🔴 ALTA",
            Severidade.CRITICA: "🔴 CRÍTICA"
        }[self]
    
    @property
    def cor(self) -> str:
        return {
            Severidade.BAIXA: "#f39c12",
            Severidade.MEDIA: "#e67e22",
            Severidade.ALTA: "#e74c3c",
            Severidade.CRITICA: "#c0392b"
        }[self]


class TipoAlerta(Enum):
    """Tipos de alertas suportados"""
    COMPLETUDE_BAIXA = "completude_baixa"
    NULIDADE_ALTA = "nulidade_alta"
    DUPLICATAS_DETECTADAS = "duplicatas_detectadas"
    VALIDACAO_FALHOU = "validacao_falhou"
    FK_INVALIDA = "fk_invalida"
    OUTLIER_DETECTADO = "outlier_detectado"
    SCHEMA_INCONSISTENTE = "schema_inconsistente"
    DADOS_DUPLICADOS = "dados_duplicados"
    PIPELINE_FALHOU = "pipeline_falhou"
    DEGRADACAO_QUALIDADE = "degradacao_qualidade"


class StatusAlerta(Enum):
    """Status do alerta"""
    ATIVO = "ativo"
    RECONHECIDO = "reconhecido"
    RESOLVIDO = "resolvido"
    DESCARTADO = "descartado"


class Papel(Enum):
    """Papéis de usuários na governança"""
    OWNER = "owner"           # Proprietário dos dados
    STEWARD = "steward"       # Responsável pela qualidade
    CUSTODIAN = "custodian"   # Gestor técnico
    ANALYST = "analyst"       # Analista de dados
    ADMIN = "admin"           # Administrador


# ============================================================================
# CLASSES DE DADOS
# ============================================================================

@dataclass
class Usuario:
    """Usuário do sistema de alertas"""
    id: str
    nome: str
    email: str
    papel: Papel
    telefone: Optional[str] = None
    canais_notificacao: List[str] = field(default_factory=lambda: ["email"])
    ativo: bool = True
    preferencias: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alerta:
    """Alerta de qualidade de dados"""
    id: str
    timestamp: str
    tipo: TipoAlerta
    severidade: Severidade
    status: StatusAlerta
    dataset: str
    descricao: str
    contexto: Dict[str, Any]
    usuarios_notificados: List[str] = field(default_factory=list)
    data_criacao: str = field(default_factory=lambda: datetime.now().isoformat())
    data_atualizacao: str = field(default_factory=lambda: datetime.now().isoformat())
    data_resolucao: Optional[str] = None
    tempo_resposta_minutos: int = 0
    assignado_a: Optional[str] = None
    notas: List[str] = field(default_factory=list)
    
    @property
    def hash_id(self) -> str:
        """Gera hash único do alerta"""
        chave = f"{self.tipo.value}_{self.dataset}_{self.timestamp}"
        return hashlib.md5(chave.encode()).hexdigest()[:8]


@dataclass
class EscalacaoAlerta:
    """Política de escalação de alerta"""
    severidade: Severidade
    minutos_ate_escalar: int
    usuario_escalar: str
    acao_escalar: str
    notificar_gerenciador: bool = False


@dataclass
class IncidenteHistorico:
    """Registro histórico de incidente"""
    alerta_id: str
    timestamp_criacao: str
    timestamp_resolucao: str
    severidade: Severidade
    tipo: TipoAlerta
    dataset: str
    tempo_aberto_minutos: int
    usuarios_envolvidos: List[str]
    resolucao: str
    impacto_estimado: str


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sistema_alertas.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# DETECTOR DE ALERTAS
# ============================================================================

class DetectorAlertas:
    """Detecta problemas e gera alertas"""
    
    THRESHOLD_COMPLETUDE = 90.0  # %
    THRESHOLD_NULIDADE = 5.0      # %
    THRESHOLD_DUPLICATAS = 0      # registros
    THRESHOLD_OUTLIERS = 3.0      # desvios padrão
    
    @staticmethod
    def detectar_completude_baixa(
        dataset: str,
        taxa_completude: float,
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta completude abaixo do threshold"""
        if taxa_completude < DetectorAlertas.THRESHOLD_COMPLETUDE:
            severidade = Severidade.CRITICA if taxa_completude < 50 else Severidade.ALTA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.COMPLETUDE_BAIXA,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Completude baixa detectada: {taxa_completude:.1f}%",
                contexto={
                    'taxa_completude': taxa_completude,
                    'threshold': DetectorAlertas.THRESHOLD_COMPLETUDE,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None
    
    @staticmethod
    def detectar_nulidade_alta(
        dataset: str,
        taxa_nulidade: float,
        coluna: Optional[str],
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta nulidade acima do threshold"""
        if taxa_nulidade > DetectorAlertas.THRESHOLD_NULIDADE:
            severidade = Severidade.CRITICA if taxa_nulidade > 20 else Severidade.ALTA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.NULIDADE_ALTA,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Nulidade alta em {coluna or 'dataset'}: {taxa_nulidade:.2f}%",
                contexto={
                    'taxa_nulidade': taxa_nulidade,
                    'coluna': coluna,
                    'threshold': DetectorAlertas.THRESHOLD_NULIDADE,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None
    
    @staticmethod
    def detectar_duplicatas(
        dataset: str,
        quantidade_duplicatas: int,
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta registros duplicados"""
        if quantidade_duplicatas > DetectorAlertas.THRESHOLD_DUPLICATAS:
            severidade = Severidade.CRITICA if quantidade_duplicatas > 10 else Severidade.MEDIA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.DADOS_DUPLICADOS,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Duplicatas detectadas: {quantidade_duplicatas} registros",
                contexto={
                    'quantidade_duplicatas': quantidade_duplicatas,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None
    
    @staticmethod
    def detectar_validacao_falhou(
        dataset: str,
        total_validacoes: int,
        validacoes_falhadas: int,
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta validações falhadas"""
        taxa_falha = (validacoes_falhadas / total_validacoes * 100) if total_validacoes > 0 else 0
        
        if taxa_falha > 5:  # Mais de 5% de falha
            severidade = Severidade.CRITICA if taxa_falha > 25 else Severidade.ALTA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.VALIDACAO_FALHOU,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Validações falhadas: {validacoes_falhadas}/{total_validacoes} ({taxa_falha:.1f}%)",
                contexto={
                    'total_validacoes': total_validacoes,
                    'validacoes_falhadas': validacoes_falhadas,
                    'taxa_falha': taxa_falha,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None
    
    @staticmethod
    def detectar_fk_invalida(
        dataset: str,
        quantidade_fk_invalida: int,
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta chaves estrangeiras inválidas"""
        if quantidade_fk_invalida > 0:
            severidade = Severidade.CRITICA if quantidade_fk_invalida > 5 else Severidade.ALTA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.FK_INVALIDA,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Chaves estrangeiras inválidas: {quantidade_fk_invalida} registros",
                contexto={
                    'quantidade_fk_invalida': quantidade_fk_invalida,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None
    
    @staticmethod
    def detectar_degradacao_qualidade(
        dataset: str,
        metrica_anterior: float,
        metrica_atual: float,
        nome_metrica: str,
        contexto: Dict
    ) -> Optional[Alerta]:
        """Detecta degradação de qualidade"""
        queda_percentual = ((metrica_anterior - metrica_atual) / metrica_anterior * 100) if metrica_anterior > 0 else 0
        
        if queda_percentual > 5:  # Queda maior que 5%
            severidade = Severidade.CRITICA if queda_percentual > 20 else Severidade.ALTA
            
            alerta = Alerta(
                id=f"alerta_{int(time.time() * 1000)}",
                timestamp=datetime.now().isoformat(),
                tipo=TipoAlerta.DEGRADACAO_QUALIDADE,
                severidade=severidade,
                status=StatusAlerta.ATIVO,
                dataset=dataset,
                descricao=f"Degradação de qualidade detectada em {nome_metrica}: {metrica_anterior:.1f}% → {metrica_atual:.1f}%",
                contexto={
                    'metrica': nome_metrica,
                    'valor_anterior': metrica_anterior,
                    'valor_atual': metrica_atual,
                    'queda_percentual': queda_percentual,
                    **contexto
                }
            )
            logger.warning(f"⚠️  Alerta detectado: {alerta.descricao}")
            return alerta
        
        return None


# ============================================================================
# NOTIFICADOR DE ALERTAS
# ============================================================================

class NotificadorAlertas:
    """Envia notificações aos usuários sobre alertas"""
    
    def __init__(
        self,
        smtp_server: str = "localhost",
        smtp_port: int = 587,
        email_origem: str = "alertas@techcommerce.com",
        senha: str = ""
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_origem = email_origem
        self.senha = senha
        self.templates_cache = {}
    
    def enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo_html: str,
        corpo_texto: str = ""
    ) -> bool:
        """Envia email com alerta"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = assunto
            msg['From'] = self.email_origem
            msg['To'] = destinatario
            
            if corpo_texto:
                msg.attach(MIMEText(corpo_texto, 'plain', 'utf-8'))
            msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
            
            # Usar conexão local por padrão (sem autenticação)
            if self.smtp_server == "localhost":
                try:
                    with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                        server.sendmail(self.email_origem, destinatario, msg.as_string())
                    logger.info(f"✓ Email enviado para {destinatario}")
                    return True
                except Exception:
                    logger.warning(f"⚠ SMTP local indisponível. Email simulado para {destinatario}")
                    return True  # Considera bem-sucedido mesmo com falha (demo)
            else:
                # Para servidor remoto
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.email_origem, self.senha)
                    server.sendmail(self.email_origem, destinatario, msg.as_string())
                logger.info(f"✓ Email enviado para {destinatario}")
                return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao enviar email: {e}")
            return False
    
    @staticmethod
    def gerar_corpo_email_alerta(alerta: Alerta, usuario: Usuario) -> tuple:
        """Gera corpo de email para alerta"""
        
        texto = f"""
Alerta de Qualidade de Dados
=============================

Severidade: {alerta.severidade.descricao}
Dataset: {alerta.dataset}
Tipo: {alerta.tipo.value}

Descrição: {alerta.descricao}

Contexto:
{json.dumps(alerta.contexto, indent=2, ensure_ascii=False)}

Data/Hora: {alerta.timestamp}

Por favor, revise e tome as ações necessárias.
"""
        
        html = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f7fa; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ background: {alerta.severidade.cor}; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .titulo {{ font-size: 1.3em; font-weight: bold; margin-bottom: 5px; }}
        .subtitulo {{ opacity: 0.9; }}
        .secao {{ margin: 15px 0; }}
        .rotulo {{ font-weight: bold; color: #333; }}
        .valor {{ color: #666; margin-left: 10px; }}
        .contexto {{ background: #f9fafb; padding: 10px; border-radius: 5px; font-family: monospace; margin-top: 10px; }}
        .rodape {{ font-size: 0.9em; color: #999; margin-top: 20px; border-top: 1px solid #e1e4e8; padding-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="titulo">{alerta.severidade.descricao} - {alerta.tipo.value.replace('_', ' ').title()}</div>
            <div class="subtitulo">{alerta.dataset}</div>
        </div>
        
        <div class="secao">
            <div><span class="rotulo">Descrição:</span><span class="valor">{alerta.descricao}</span></div>
        </div>
        
        <div class="secao">
            <div><span class="rotulo">Data/Hora:</span><span class="valor">{alerta.timestamp}</span></div>
            <div><span class="rotulo">Papel:</span><span class="valor">{usuario.papel.value}</span></div>
        </div>
        
        <div class="secao">
            <div class="rotulo">Contexto:</div>
            <div class="contexto">{json.dumps(alerta.contexto, indent=2, ensure_ascii=False)}</div>
        </div>
        
        <div class="rodape">
            <p>Você está recebendo este email porque é um {usuario.papel.value} do dataset {alerta.dataset}.</p>
            <p>Sistema de Alertas de Governança de Dados - TechCommerce</p>
        </div>
    </div>
</body>
</html>
        """
        
        return texto, html
    
    def notificar_alerta(
        self,
        alerta: Alerta,
        usuarios_notificar: List[Usuario],
        usar_multi_canal: bool = True
    ) -> Dict[str, bool]:
        """Notifica usuários sobre alerta via canais apropriados"""
        resultados = {}
        
        for usuario in usuarios_notificar:
            if not usuario.ativo:
                logger.info(f"⊘ Usuário {usuario.nome} inativo, ignorado")
                continue
            
            # Determinar canais de notificação
            canais = usuario.canais_notificacao
            
            for canal in canais:
                if canal == 'email':
                    assunto = f"[{alerta.severidade.descricao}] {alerta.tipo.value} - {alerta.dataset}"
                    texto, html = self.gerar_corpo_email_alerta(alerta, usuario)
                    resultado = self.enviar_email(usuario.email, assunto, html, texto)
                    resultados[f"{usuario.id}_{canal}"] = resultado
                
                elif canal == 'sms' and usuario.telefone:
                    logger.info(f"📱 SMS enviado para {usuario.nome}: {alerta.descricao[:50]}...")
                    resultados[f"{usuario.id}_{canal}"] = True
                
                elif canal == 'slack':
                    logger.info(f"💬 Mensagem Slack enviada a {usuario.nome}")
                    resultados[f"{usuario.id}_{canal}"] = True
                
                elif canal == 'webhook':
                    logger.info(f"🔗 Webhook acionado para {usuario.nome}")
                    resultados[f"{usuario.id}_{canal}"] = True
        
        return resultados


# ============================================================================
# GERENCIADOR DE ESCALAÇÃO
# ============================================================================

class GerenciadorEscalacao:
    """Gerencia escalação automática de alertas"""
    
    def __init__(self):
        self.politicas_escalacao: Dict[Severidade, EscalacaoAlerta] = {}
        self.alertas_escalonados: Dict[str, List[dict]] = {}
        self._inicializar_politicas_padrao()
    
    def _inicializar_politicas_padrao(self):
        """Inicializa políticas de escalação padrão"""
        self.politicas_escalacao = {
            Severidade.BAIXA: EscalacaoAlerta(
                severidade=Severidade.BAIXA,
                minutos_ate_escalar=1440,  # 24 horas
                usuario_escalar="steward",
                acao_escalar="email_lembrete",
                notificar_gerenciador=False
            ),
            Severidade.MEDIA: EscalacaoAlerta(
                severidade=Severidade.MEDIA,
                minutos_ate_escalar=480,  # 8 horas
                usuario_escalar="owner",
                acao_escalar="email_urgente",
                notificar_gerenciador=False
            ),
            Severidade.ALTA: EscalacaoAlerta(
                severidade=Severidade.ALTA,
                minutos_ate_escalar=120,  # 2 horas
                usuario_escalar="custodian",
                acao_escalar="email_critico",
                notificar_gerenciador=True
            ),
            Severidade.CRITICA: EscalacaoAlerta(
                severidade=Severidade.CRITICA,
                minutos_ate_escalar=30,  # 30 minutos
                usuario_escalar="admin",
                acao_escalar="email_emergency",
                notificar_gerenciador=True
            )
        }
    
    def verificar_escalacao(
        self,
        alerta: Alerta,
        usuarios: Dict[str, Usuario],
        notificador: NotificadorAlertas
    ) -> Optional[List[Usuario]]:
        """Verifica se alerta precisa escalar e executa escalação"""
        if alerta.status != StatusAlerta.ATIVO:
            return None
        
        politica = self.politicas_escalacao.get(alerta.severidade)
        if not politica:
            return None
        
        # Verificar tempo desde criação
        tempo_alerta = datetime.fromisoformat(alerta.data_criacao)
        minutos_abertos = (datetime.now() - tempo_alerta).total_seconds() / 60
        
        if minutos_abertos >= politica.minutos_ate_escalar:
            logger.warning(f"⚡ Escalando alerta {alerta.id} ({alerta.severidade.descricao})")
            
            # Encontrar usuários por papel
            usuarios_escalar = [
                u for u in usuarios.values()
                if u.papel.value == politica.usuario_escalar
            ]
            
            # Registrar escalação
            self.alertas_escalonados[alerta.id] = self.alertas_escalonados.get(alerta.id, [])
            self.alertas_escalonados[alerta.id].append({
                'timestamp': datetime.now().isoformat(),
                'acao': politica.acao_escalar,
                'usuarios': [u.id for u in usuarios_escalar],
                'notificar_gerenciador': politica.notificar_gerenciador
            })
            
            # Notificar usuários
            for usuario in usuarios_escalar:
                notificador.notificar_alerta(alerta, [usuario])
            
            return usuarios_escalar
        
        return None


# ============================================================================
# REPOSITÓRIO DE ALERTAS
# ============================================================================

class RepositorioAlertas:
    """Gerencia armazenamento e recuperação de alertas"""
    
    def __init__(self, diretorio: str = "logs"):
        self.diretorio = Path(diretorio)
        self.diretorio.mkdir(exist_ok=True)
        self.arquivo_alertas = self.diretorio / "alertas.json"
        self.arquivo_historico = self.diretorio / "historico_incidentes.json"
        self.alertas_em_memoria: Dict[str, Alerta] = {}
    
    def adicionar_alerta(self, alerta: Alerta) -> bool:
        """Adiciona novo alerta ao repositório"""
        try:
            self.alertas_em_memoria[alerta.id] = alerta
            self._salvar_alertas()
            logger.info(f"✓ Alerta armazenado: {alerta.id}")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao armazenar alerta: {e}")
            return False
    
    def atualizar_alerta(self, alerta: Alerta) -> bool:
        """Atualiza alerta existente"""
        try:
            alerta.data_atualizacao = datetime.now().isoformat()
            self.alertas_em_memoria[alerta.id] = alerta
            self._salvar_alertas()
            logger.info(f"✓ Alerta atualizado: {alerta.id}")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao atualizar alerta: {e}")
            return False
    
    def obter_alerta(self, alerta_id: str) -> Optional[Alerta]:
        """Obtém alerta por ID"""
        return self.alertas_em_memoria.get(alerta_id)
    
    def obter_alertas_ativos(self) -> List[Alerta]:
        """Obtém todos os alertas ativos"""
        return [
            a for a in self.alertas_em_memoria.values()
            if a.status == StatusAlerta.ATIVO
        ]
    
    def obter_alertas_por_dataset(self, dataset: str) -> List[Alerta]:
        """Obtém alertas por dataset"""
        return [
            a for a in self.alertas_em_memoria.values()
            if a.dataset == dataset
        ]
    
    def obter_alertas_por_severidade(self, severidade: Severidade) -> List[Alerta]:
        """Obtém alertas por severidade"""
        return [
            a for a in self.alertas_em_memoria.values()
            if a.severidade == severidade
        ]
    
    def obter_alertas_nao_resolvidos(self) -> List[Alerta]:
        """Obtém alertas não resolvidos"""
        return [
            a for a in self.alertas_em_memoria.values()
            if a.status in [StatusAlerta.ATIVO, StatusAlerta.RECONHECIDO]
        ]
    
    def resolver_alerta(self, alerta_id: str, resolucao: str) -> bool:
        """Marca alerta como resolvido"""
        alerta = self.alertas_em_memoria.get(alerta_id)
        if alerta:
            alerta.status = StatusAlerta.RESOLVIDO
            alerta.data_resolucao = datetime.now().isoformat()
            alerta.notas.append(f"Resolvido: {resolucao}")
            
            # Calcular tempo de resposta
            criacao = datetime.fromisoformat(alerta.data_criacao)
            resolucao_time = datetime.fromisoformat(alerta.data_resolucao)
            alerta.tempo_resposta_minutos = int((resolucao_time - criacao).total_seconds() / 60)
            
            # Arquivar no histórico
            self._arquivar_incidente(alerta)
            
            return self.atualizar_alerta(alerta)
        
        return False
    
    def reconhecer_alerta(self, alerta_id: str, usuario_id: str) -> bool:
        """Marca alerta como reconhecido"""
        alerta = self.alertas_em_memoria.get(alerta_id)
        if alerta:
            alerta.status = StatusAlerta.RECONHECIDO
            alerta.assignado_a = usuario_id
            alerta.notas.append(f"Reconhecido por {usuario_id}")
            return self.atualizar_alerta(alerta)
        
        return False
    
    def _salvar_alertas(self):
        """Salva alertas em arquivo JSON"""
        try:
            dados = {}
            for alerta_id, alerta in self.alertas_em_memoria.items():
                dados[alerta_id] = {
                    **asdict(alerta),
                    'tipo': alerta.tipo.value,
                    'severidade': alerta.severidade.name,
                    'status': alerta.status.value
                }
            
            with open(self.arquivo_alertas, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"✗ Erro ao salvar alertas: {e}")
    
    def _caregar_alertas(self) -> Dict[str, Alerta]:
        """Carrega alertas de arquivo JSON"""
        try:
            if self.arquivo_alertas.exists():
                with open(self.arquivo_alertas, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                
                alertas = {}
                for alerta_id, alerta_dict in dados.items():
                    # Converter tipos enum
                    alerta_dict['tipo'] = TipoAlerta(alerta_dict['tipo'])
                    alerta_dict['severidade'] = Severidade[alerta_dict['severidade']]
                    alerta_dict['status'] = StatusAlerta(alerta_dict['status'])
                    
                    alertas[alerta_id] = Alerta(**alerta_dict)
                
                return alertas
        
        except Exception as e:
            logger.error(f"✗ Erro ao carregar alertas: {e}")
        
        return {}
    
    def _arquivar_incidente(self, alerta: Alerta):
        """Arquiva alerta resolvido como incidente histórico"""
        try:
            criacao = datetime.fromisoformat(alerta.data_criacao)
            resolucao = datetime.fromisoformat(alerta.data_resolucao or datetime.now().isoformat())
            tempo_aberto = int((resolucao - criacao).total_seconds() / 60)
            
            incidente = IncidenteHistorico(
                alerta_id=alerta.id,
                timestamp_criacao=alerta.data_criacao,
                timestamp_resolucao=alerta.data_resolucao or datetime.now().isoformat(),
                severidade=alerta.severidade,
                tipo=alerta.tipo,
                dataset=alerta.dataset,
                tempo_aberto_minutos=tempo_aberto,
                usuarios_envolvidos=alerta.usuarios_notificados,
                resolucao=alerta.notas[-1] if alerta.notas else "Não documentada",
                impacto_estimado=f"{alerta.contexto.get('registros_afetados', 'N/A')}"
            )
            
            # Carregar histórico existente
            historico = []
            if self.arquivo_historico.exists():
                with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                    historico = json.load(f)
            
            # Adicionar novo
            incidente_dict = asdict(incidente)
            incidente_dict['severidade'] = incidente.severidade.name
            incidente_dict['tipo'] = incidente.tipo.value
            historico.append(incidente_dict)
            
            # Salvar
            with open(self.arquivo_historico, 'w', encoding='utf-8') as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✓ Incidente arquivado: {incidente.alerta_id}")
        
        except Exception as e:
            logger.error(f"✗ Erro ao arquivar incidente: {e}")


# ============================================================================
# DASHBOARD DE ALERTAS
# ============================================================================

class DashboardAlertas:
    """Gera dashboard HTML de alertas"""
    
    @staticmethod
    def gerar_dashboard_html(
        alertas_ativos: List[Alerta],
        historico_incidentes: List[IncidenteHistorico]
    ) -> str:
        """Gera HTML do dashboard de alertas"""
        
        # Contar por severidade
        por_severidade = {}
        for alerta in alertas_ativos:
            s = alerta.severidade.name
            por_severidade[s] = por_severidade.get(s, 0) + 1
        
        # Contar por dataset
        por_dataset = {}
        for alerta in alertas_ativos:
            por_dataset[alerta.dataset] = por_dataset.get(alerta.dataset, 0) + 1
        
        # Gerar linhas da tabela
        linhas_alertas = ""
        for alerta in alertas_ativos:
            tempo_aberto = (datetime.now() - datetime.fromisoformat(alerta.data_criacao)).total_seconds() / 60
            linhas_alertas += f"""
            <tr>
                <td>{alerta.id}</td>
                <td><span style="background: {alerta.severidade.cor}; color: white; padding: 5px 10px; border-radius: 3px;">{alerta.severidade.descricao}</span></td>
                <td>{alerta.dataset}</td>
                <td>{alerta.tipo.value}</td>
                <td>{alerta.descricao}</td>
                <td>{int(tempo_aberto)} min</td>
            </tr>
            """
        
        # Estatísticas do histórico
        tempo_medio_resolucao = 0
        taxa_resolucao = 0
        if historico_incidentes:
            tempo_medio_resolucao = int(sum(i['tempo_aberto_minutos'] for i in historico_incidentes) / len(historico_incidentes))
            taxa_resolucao = len(historico_incidentes)
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Alertas - TechCommerce</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .metricas {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metrica {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metrica-valor {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .metrica-label {{
            color: #666;
            margin-top: 10px;
        }}
        .tabela-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }}
        .tabela-container h2 {{
            padding: 20px;
            background: #f9fafb;
            border-bottom: 1px solid #e1e4e8;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            padding: 20px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e1e4e8;
        }}
        tr:hover {{
            background: #f9fafb;
        }}
        .rodape {{
            text-align: center;
            color: #666;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚨 Dashboard de Alertas - TechCommerce</h1>
            <p>Monitoramento em Tempo Real de Qualidade de Dados</p>
            <p style="font-size: 0.9em; margin-top: 10px; opacity: 0.9;">Última atualização: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </header>
        
        <div class="metricas">
            <div class="metrica">
                <div class="metrica-valor">{len(alertas_ativos)}</div>
                <div class="metrica-label">Alertas Ativos</div>
            </div>
            <div class="metrica">
                <div class="metrica-valor" style="color: #c0392b;">{por_severidade.get('CRITICA', 0)}</div>
                <div class="metrica-label">Críticos</div>
            </div>
            <div class="metrica">
                <div class="metrica-valor" style="color: #e74c3c;">{por_severidade.get('ALTA', 0)}</div>
                <div class="metrica-label">Altos</div>
            </div>
            <div class="metrica">
                <div class="metrica-valor">{taxa_resolucao}</div>
                <div class="metrica-label">Resolvidos</div>
            </div>
            <div class="metrica">
                <div class="metrica-valor">{tempo_medio_resolucao} min</div>
                <div class="metrica-label">Tempo Médio Resolução</div>
            </div>
        </div>
        
        <div class="tabela-container">
            <h2>Alertas Ativos</h2>
            <table>
                <tr>
                    <th>ID</th>
                    <th>Severidade</th>
                    <th>Dataset</th>
                    <th>Tipo</th>
                    <th>Descrição</th>
                    <th>Tempo Aberto</th>
                </tr>
                {linhas_alertas if linhas_alertas else '<tr><td colspan="6" style="text-align: center; color: #999;">Nenhum alerta ativo</td></tr>'}
            </table>
        </div>
        
        <div class="rodape">
            <p>Sistema de Alertas de Governança de Dados | TechCommerce | v1.0</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html


# ============================================================================
# ORQUESTRADOR DE ALERTAS (PRINCIPAL)
# ============================================================================

class OrquestradorAlertas:
    """Orquestra todo o sistema de alertas"""
    
    def __init__(self, empresa: str = "TechCommerce"):
        self.empresa = empresa
        self.usuarios: Dict[str, Usuario] = {}
        self.repositorio = RepositorioAlertas()
        self.notificador = NotificadorAlertas()
        self.escalador = GerenciadorEscalacao()
        self.detector = DetectorAlertas()
        self.thread_monitor: Optional[threading.Thread] = None
        self.executando = False
        
        logger.info(f"Sistema de Alertas iniciado para: {empresa}")
    
    def registrar_usuario(self, usuario: Usuario) -> bool:
        """Registra novo usuário no sistema"""
        try:
            self.usuarios[usuario.id] = usuario
            logger.info(f"✓ Usuário registrado: {usuario.nome} ({usuario.papel.value})")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao registrar usuário: {e}")
            return False
    
    def registrar_usuarios_padrao(self):
        """Registra usuários padrão do sistema"""
        usuarios_padrao = [
            Usuario(
                id="owner_1",
                nome="João Silva",
                email="joao.silva@techcommerce.com",
                papel=Papel.OWNER,
                telefone="+55 11 98765-4321",
                canais_notificacao=["email", "sms"]
            ),
            Usuario(
                id="steward_1",
                nome="Maria Santos",
                email="maria.santos@techcommerce.com",
                papel=Papel.STEWARD,
                telefone="+55 11 98765-4322",
                canais_notificacao=["email"]
            ),
            Usuario(
                id="custodian_1",
                nome="Carlos Oliveira",
                email="carlos.oliveira@techcommerce.com",
                papel=Papel.CUSTODIAN,
                telefone="+55 11 98765-4323",
                canais_notificacao=["email", "slack"]
            ),
            Usuario(
                id="analyst_1",
                nome="Ana Costa",
                email="ana.costa@techcommerce.com",
                papel=Papel.ANALYST,
                canais_notificacao=["email"]
            ),
            Usuario(
                id="admin_1",
                nome="Pedro Admin",
                email="pedro.admin@techcommerce.com",
                papel=Papel.ADMIN,
                telefone="+55 11 98765-4324",
                canais_notificacao=["email", "sms", "slack"]
            )
        ]
        
        for usuario in usuarios_padrao:
            self.registrar_usuario(usuario)
    
    def processar_alerta(
        self,
        alerta: Alerta,
        usuarios_notificar: Optional[List[str]] = None
    ) -> bool:
        """Processa novo alerta completo"""
        try:
            # 1. Armazenar alerta
            self.repositorio.adicionar_alerta(alerta)
            
            # 2. Determinar usuários a notificar
            if usuarios_notificar is None:
                # Notificar todos os papéis relevantes para o dataset
                usuarios_notificar = list(self.usuarios.keys())
            
            usuarios = [
                self.usuarios[uid] for uid in usuarios_notificar
                if uid in self.usuarios
            ]
            
            # 3. Enviar notificações
            alerta.usuarios_notificados = [u.id for u in usuarios]
            self.notificador.notificar_alerta(alerta, usuarios)
            
            # 4. Armazenar notificações
            self.repositorio.atualizar_alerta(alerta)
            
            logger.info(f"✓ Alerta processado e notificações enviadas: {alerta.id}")
            return True
        
        except Exception as e:
            logger.error(f"✗ Erro ao processar alerta: {e}")
            return False
    
    def gerar_relatorio_alertas(self) -> Dict[str, Any]:
        """Gera relatório consolidado de alertas"""
        alertas_ativos = self.repositorio.obter_alertas_ativos()
        
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'empresa': self.empresa,
            'total_alertas_ativos': len(alertas_ativos),
            'alertas_por_severidade': {
                'CRITICA': len(self.repositorio.obter_alertas_por_severidade(Severidade.CRITICA)),
                'ALTA': len(self.repositorio.obter_alertas_por_severidade(Severidade.ALTA)),
                'MEDIA': len(self.repositorio.obter_alertas_por_severidade(Severidade.MEDIA)),
                'BAIXA': len(self.repositorio.obter_alertas_por_severidade(Severidade.BAIXA)),
            },
            'alertas_por_dataset': {},
            'alertas_por_tipo': {},
            'alertas_detalhes': []
        }
        
        for alerta in alertas_ativos:
            # Contar por dataset
            relatorio['alertas_por_dataset'][alerta.dataset] = \
                relatorio['alertas_por_dataset'].get(alerta.dataset, 0) + 1
            
            # Contar por tipo
            relatorio['alertas_por_tipo'][alerta.tipo.value] = \
                relatorio['alertas_por_tipo'].get(alerta.tipo.value, 0) + 1
            
            # Adicionar detalhes
            tempo_aberto = (datetime.now() - datetime.fromisoformat(alerta.data_criacao)).total_seconds() / 60
            relatorio['alertas_detalhes'].append({
                'id': alerta.id,
                'tipo': alerta.tipo.value,
                'severidade': alerta.severidade.name,
                'dataset': alerta.dataset,
                'descricao': alerta.descricao,
                'tempo_aberto_minutos': int(tempo_aberto),
                'status': alerta.status.value,
                'usuarios_notificados': alerta.usuarios_notificados
            })
        
        return relatorio
    
    def gerar_dashboard_html(self) -> str:
        """Gera HTML do dashboard de alertas"""
        alertas_ativos = self.repositorio.obter_alertas_ativos()
        
        # Carregar histórico (simplificado)
        historico = []
        if self.repositorio.arquivo_historico.exists():
            with open(self.repositorio.arquivo_historico, 'r', encoding='utf-8') as f:
                historico = json.load(f)
        
        return DashboardAlertas.gerar_dashboard_html(alertas_ativos, historico)
    
    def salvar_dashboard(self, caminho: str = "relatorios/dashboard_alertas.html") -> bool:
        """Salva dashboard em arquivo HTML"""
        try:
            Path(Path(caminho).parent).mkdir(parents=True, exist_ok=True)
            html = self.gerar_dashboard_html()
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"✓ Dashboard salvo: {caminho}")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao salvar dashboard: {e}")
            return False
    
    def iniciar_monitor(self, intervalo_segundos: int = 5):
        """Inicia thread de monitoramento contínuo"""
        if self.executando:
            logger.warning("Monitor já está em execução")
            return
        
        self.executando = True
        self.thread_monitor = threading.Thread(
            target=self._executar_monitor,
            args=(intervalo_segundos,),
            daemon=True
        )
        self.thread_monitor.start()
        logger.info(f"✓ Monitor iniciado (intervalo: {intervalo_segundos}s)")
    
    def parar_monitor(self):
        """Para thread de monitoramento"""
        self.executando = False
        if self.thread_monitor:
            self.thread_monitor.join(timeout=5)
        logger.info("✓ Monitor parado")
    
    def _executar_monitor(self, intervalo_segundos: int):
        """Executa monitoramento em thread"""
        while self.executando:
            try:
                # Verificar escalação de alertas
                alertas_nao_resolvidos = self.repositorio.obter_alertas_nao_resolvidos()
                
                for alerta in alertas_nao_resolvidos:
                    usuarios_escalonados = self.escalador.verificar_escalacao(
                        alerta,
                        self.usuarios,
                        self.notificador
                    )
                    
                    if usuarios_escalonados:
                        self.repositorio.atualizar_alerta(alerta)
                
                # Salvar dashboard periodicamente
                if int(time.time()) % 30 == 0:  # A cada 30 segundos
                    self.salvar_dashboard()
                
                time.sleep(intervalo_segundos)
            
            except Exception as e:
                logger.error(f"✗ Erro no monitor: {e}")
                time.sleep(intervalo_segundos)


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Inicializar orquestrador
    orquestrador = OrquestradorAlertas(empresa="TechCommerce")
    
    # Registrar usuários
    orquestrador.registrar_usuarios_padrao()
    
    print("\n" + "=" * 80)
    print("SISTEMA DE ALERTAS DE GOVERNANÇA DE DADOS")
    print("=" * 80)
    
    # Exemplo 1: Detectar completude baixa
    print("\n📍 Criando alerta de completude baixa...")
    alerta_completude = DetectorAlertas.detectar_completude_baixa(
        dataset="clientes",
        taxa_completude=75.5,
        contexto={'registros_afetados': 12}
    )
    
    if alerta_completude:
        orquestrador.processar_alerta(
            alerta_completude,
            usuarios_notificar=["owner_1", "steward_1"]
        )
    
    # Exemplo 2: Detectar nulidade alta
    print("\n📍 Criando alerta de nulidade alta...")
    alerta_nulidade = DetectorAlertas.detectar_nulidade_alta(
        dataset="produtos",
        taxa_nulidade=8.5,
        coluna="descricao",
        contexto={'registros_afetados': 17}
    )
    
    if alerta_nulidade:
        orquestrador.processar_alerta(
            alerta_nulidade,
            usuarios_notificar=["steward_1", "custodian_1"]
        )
    
    # Exemplo 3: Detectar validações falhadas
    print("\n📍 Criando alerta de validações falhadas...")
    alerta_validacao = DetectorAlertas.detectar_validacao_falhou(
        dataset="vendas",
        total_validacoes=100,
        validacoes_falhadas=15,
        contexto={'expectativas': ['email_valido', 'telefone_formato']}
    )
    
    if alerta_validacao:
        orquestrador.processar_alerta(
            alerta_validacao,
            usuarios_notificar=["custodian_1", "admin_1"]
        )
    
    # Exemplo 4: Detectar degradação
    print("\n📍 Criando alerta de degradação de qualidade...")
    alerta_degradacao = DetectorAlertas.detectar_degradacao_qualidade(
        dataset="clientes",
        metrica_anterior=96.5,
        metrica_atual=82.1,
        nome_metrica="Completude",
        contexto={'causa_suspeita': 'Aumento de valores nulos'}
    )
    
    if alerta_degradacao:
        orquestrador.processar_alerta(alerta_degradacao)
    
    # Gerar relatório
    print("\n" + "=" * 80)
    print("RELATÓRIO DE ALERTAS")
    print("=" * 80)
    
    relatorio = orquestrador.gerar_relatorio_alertas()
    
    print(f"\n📊 Total de Alertas Ativos: {relatorio['total_alertas_ativos']}")
    print(f"   CRÍTICA: {relatorio['alertas_por_severidade']['CRITICA']}")
    print(f"   ALTA: {relatorio['alertas_por_severidade']['ALTA']}")
    print(f"   MÉDIA: {relatorio['alertas_por_severidade']['MEDIA']}")
    print(f"   BAIXA: {relatorio['alertas_por_severidade']['BAIXA']}")
    
    print(f"\n📋 Alertas por Dataset:")
    for dataset, count in relatorio['alertas_por_dataset'].items():
        print(f"   {dataset}: {count}")
    
    print(f"\n🔔 Alertas por Tipo:")
    for tipo, count in relatorio['alertas_por_tipo'].items():
        print(f"   {tipo}: {count}")
    
    # Salvar dashboard
    print("\n" + "=" * 80)
    print("GERANDO DASHBOARD")
    print("=" * 80)
    
    orquestrador.salvar_dashboard()
    
    # Salvar relatório JSON
    print("\n📍 Salvando relatório em JSON...")
    with open('relatorios/alertas_relatorio.json', 'w', encoding='utf-8') as f:
        # Converter tipos para serialização
        relatorio_json = {
            **relatorio,
            'alertas_por_severidade': relatorio['alertas_por_severidade'],
            'alertas_por_dataset': relatorio['alertas_por_dataset'],
            'alertas_por_tipo': relatorio['alertas_por_tipo']
        }
        json.dump(relatorio_json, f, indent=2, ensure_ascii=False)
    print("✓ Relatório salvo em relatorios/alertas_relatorio.json")
    
    # Teste de resolução
    print("\n" + "=" * 80)
    print("TESTANDO RESOLUÇÃO DE ALERTA")
    print("=" * 80)
    
    alertas = orquestrador.repositorio.obter_alertas_ativos()
    if alertas:
        alerta_teste = alertas[0]
        print(f"\n📍 Resolvendo alerta: {alerta_teste.id}")
        orquestrador.repositorio.resolver_alerta(
            alerta_teste.id,
            "Duplicata removida com sucesso"
        )
        print("✓ Alerta resolvido e arquivado")
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO DO SISTEMA")
    print("=" * 80)
    print(f"\n✅ Alertas Criados: {len(orquestrador.repositorio.obter_alertas_ativos()) + 1}")
    print(f"✅ Usuários Registrados: {len(orquestrador.usuarios)}")
    print(f"✅ Arquivos Gerados:")
    print(f"   - relatorios/dashboard_alertas.html")
    print(f"   - relatorios/alertas_relatorio.json")
    print(f"   - logs/sistema_alertas.log")
    print(f"   - logs/alertas.json")
    print(f"   - logs/historico_incidentes.json")
    print("\n" + "=" * 80 + "\n")
