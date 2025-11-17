"""
Sistema de Correção Automática de Dados
Padronização, remoção de duplicatas, preenchimento e validação de dados
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import re
from dataclasses import dataclass
import logging


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/correcao_automatica.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLASSES DE RESULTADO
# ============================================================================

@dataclass
class ResultadoCorrecao:
    """Armazena resultado de uma operação de correção"""
    sucesso: bool
    registros_processados: int
    registros_corrigidos: int
    registros_rejeitados: int
    mensagens: List[str]
    dados_corrigidos: Optional[pd.DataFrame] = None
    
    @property
    def taxa_sucesso(self) -> float:
        """Calcula taxa de sucesso"""
        if self.registros_processados == 0:
            return 0.0
        return (self.registros_corrigidos / self.registros_processados) * 100


# ============================================================================
# CORRETORES DE FORMATO
# ============================================================================

class PadronizadorFormatos:
    """Padroniza formatos de dados"""
    
    @staticmethod
    def padronizar_data(data_str: str, formatos: List[str] = None) -> Optional[str]:
        """
        Padroniza data para formato ISO (YYYY-MM-DD)
        
        Args:
            data_str: String de data
            formatos: Formatos a tentar (se None, tenta detectar)
            
        Returns:
            Data em formato YYYY-MM-DD ou None
        """
        if pd.isna(data_str):
            return None
        
        data_str = str(data_str).strip()
        
        # Formatos a tentar
        formatos_padrao = [
            '%Y-%m-%d',      # ISO
            '%d/%m/%Y',      # Brasileiro
            '%d-%m-%Y',      # Brasileiro com hífen
            '%Y/%m/%d',      # Alternativo
            '%d.%m.%Y',      # Ponto
            '%Y%m%d',        # Sem separador
            '%d %m %Y',      # Com espaço
        ]
        
        if formatos:
            formatos_padrao = formatos + formatos_padrao
        
        for fmt in formatos_padrao:
            try:
                data = pd.to_datetime(data_str, format=fmt)
                return data.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue
        
        # Último recurso: tentar conversão automática
        try:
            data = pd.to_datetime(data_str)
            return data.strftime('%Y-%m-%d')
        except:
            return None
    
    @staticmethod
    def padronizar_telefone(telefone: str, pais: str = 'BR') -> Optional[str]:
        """
        Padroniza telefone
        
        Args:
            telefone: String de telefone
            pais: Código do país (BR = Brasil)
            
        Returns:
            Telefone padronizado ou None
        """
        if pd.isna(telefone):
            return None
        
        # Remover caracteres não numéricos
        telefone_limpo = re.sub(r'\D', '', str(telefone))
        
        if pais == 'BR':
            # Brasil: 11 dígitos (2 área + 9 número)
            if len(telefone_limpo) == 11:
                return telefone_limpo
            elif len(telefone_limpo) == 10:
                # Telefone fixo, adicionar 9 no meio
                return telefone_limpo[:2] + '9' + telefone_limpo[2:]
            elif len(telefone_limpo) > 11:
                # Remover 55 (código do Brasil) se presente
                if telefone_limpo.startswith('55'):
                    return telefone_limpo[2:]
        
        return None
    
    @staticmethod
    def padronizar_email(email: str) -> Optional[str]:
        """
        Padroniza email (lowercase, sem espaços)
        
        Args:
            email: String de email
            
        Returns:
            Email padronizado ou None
        """
        if pd.isna(email):
            return None
        
        email = str(email).strip().lower()
        
        # Validar formato básico
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if re.match(pattern, email):
            return email
        
        return None
    
    @staticmethod
    def padronizar_estado(estado: str) -> Optional[str]:
        """
        Padroniza estado para UF (2 caracteres maiúsculos)
        
        Args:
            estado: String de estado ou UF
            
        Returns:
            UF padronizada ou None
        """
        if pd.isna(estado):
            return None
        
        # Mapeamento de nomes para UF
        mapa_estados = {
            'acre': 'AC', 'alagoas': 'AL', 'amapá': 'AP', 'amapa': 'AP',
            'amazonas': 'AM', 'bahia': 'BA', 'ceará': 'CE', 'ceara': 'CE',
            'distrito federal': 'DF', 'espírito santo': 'ES', 'espiritu santo': 'ES',
            'goiás': 'GO', 'goias': 'GO', 'maranhão': 'MA', 'maranhao': 'MA',
            'mato grosso': 'MT', 'mato grosso do sul': 'MS', 'minas gerais': 'MG',
            'pará': 'PA', 'para': 'PA', 'paraíba': 'PB', 'paraiba': 'PB',
            'paraná': 'PR', 'parana': 'PR', 'pernambuco': 'PE', 'piauí': 'PI',
            'piaui': 'PI', 'rio de janeiro': 'RJ', 'rio grande do norte': 'RN',
            'rio grande do sul': 'RS', 'rondônia': 'RO', 'rondonia': 'RO',
            'roraima': 'RR', 'santa catarina': 'SC', 'são paulo': 'SP',
            'sao paulo': 'SP', 'sergipe': 'SE', 'tocantins': 'TO'
        }
        
        estado_upper = str(estado).strip().upper()
        
        # Se já é UF válida
        if estado_upper in mapa_estados.values():
            return estado_upper
        
        # Procurar no mapa
        estado_lower = estado_upper.lower()
        return mapa_estados.get(estado_lower, None)
    
    @staticmethod
    def padronizar_nome(nome: str) -> Optional[str]:
        """
        Padroniza nome (title case, sem espaços extras)
        
        Args:
            nome: String de nome
            
        Returns:
            Nome padronizado ou None
        """
        if pd.isna(nome):
            return None
        
        nome = str(nome).strip()
        
        # Remover espaços múltiplos
        nome = ' '.join(nome.split())
        
        # Title case
        nome = nome.title()
        
        # Palavras especiais
        palavras_especiais = {'da', 'de', 'do', 'e', 'ou', 'à'}
        palavras = nome.split()
        nome_corrigido = []
        
        for i, palavra in enumerate(palavras):
            if i > 0 and palavra.lower() in palavras_especiais:
                nome_corrigido.append(palavra.lower())
            else:
                nome_corrigido.append(palavra)
        
        return ' '.join(nome_corrigido)


# ============================================================================
# REMOVEDOR DE DUPLICATAS
# ============================================================================

class RemovedorDuplicatas:
    """Remove duplicatas com lógica inteligente"""
    
    @staticmethod
    def encontrar_duplicatas(df: pd.DataFrame, coluna_id: str) -> Dict[Any, List[int]]:
        """
        Encontra duplicatas por ID
        
        Args:
            df: DataFrame
            coluna_id: Coluna de ID
            
        Returns:
            Dicionário com {id: [índices duplicados]}
        """
        duplicatas = {}
        
        for id_valor in df[coluna_id].unique():
            indices = df[df[coluna_id] == id_valor].index.tolist()
            if len(indices) > 1:
                duplicatas[id_valor] = indices
        
        return duplicatas
    
    @staticmethod
    def avaliar_qualidade_registro(row: pd.Series) -> int:
        """
        Avalia qualidade de um registro (score 0-100)
        Registros com menos NaNs têm melhor score
        
        Args:
            row: Série pandas
            
        Returns:
            Score de qualidade
        """
        nulos = row.isna().sum()
        total = len(row)
        completude = ((total - nulos) / total) * 100
        return int(completude)
    
    @classmethod
    def remover_duplicatas_inteligentes(cls, df: pd.DataFrame, coluna_id: str) -> ResultadoCorrecao:
        """
        Remove duplicatas mantendo registro de melhor qualidade
        
        Args:
            df: DataFrame
            coluna_id: Coluna de ID
            
        Returns:
            ResultadoCorrecao
        """
        logger.info(f"Iniciando remoção de duplicatas por {coluna_id}")
        
        duplicatas = cls.encontrar_duplicatas(df, coluna_id)
        indices_remover = []
        
        for id_valor, indices in duplicatas.items():
            # Calcular score de qualidade para cada duplicata
            scores = []
            for idx in indices:
                score = cls.avaliar_qualidade_registro(df.loc[idx])
                scores.append((idx, score))
            
            # Ordenar por score (descendente)
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # Manter o primeiro (melhor), remover o resto
            indices_remover.extend([s[0] for s in scores[1:]])
        
        df_corrigido = df.drop(indices_remover).reset_index(drop=True)
        
        resultado = ResultadoCorrecao(
            sucesso=True,
            registros_processados=len(df),
            registros_corrigidos=len(indices_remover),
            registros_rejeitados=0,
            mensagens=[f"Removidas {len(indices_remover)} duplicatas inteligentes"],
            dados_corrigidos=df_corrigido
        )
        
        logger.info(f"✓ {len(indices_remover)} duplicatas removidas")
        return resultado


# ============================================================================
# PREENCHEDOR DE CAMPOS VAZIOS
# ============================================================================

class PreenchedorCamposVazios:
    """Preenche campos vazios com regras de negócio"""
    
    # Regras de negócio por coluna
    REGRAS_PREENCHIMENTO = {
        'data_cadastro': lambda: datetime.now().strftime('%Y-%m-%d'),
        'data_criacao': lambda: datetime.now().strftime('%Y-%m-%d'),
        'estoque': lambda: 0,
        'ativo': lambda: True,
        'status': lambda: 'Ativo'
    }
    
    @staticmethod
    def preencher_por_forwarding(df: pd.DataFrame, coluna: str, limite_vazio: float = 0.5) -> pd.DataFrame:
        """
        Preenche campos vazios usando método forward fill
        
        Args:
            df: DataFrame
            coluna: Coluna a preencher
            limite_vazio: Limite de valores vazios (%)
            
        Returns:
            DataFrame com preenchimento
        """
        if coluna not in df.columns:
            return df
        
        percentual_vazio = df[coluna].isna().sum() / len(df)
        
        if percentual_vazio == 0:
            return df
        
        if percentual_vazio > limite_vazio:
            logger.warning(f"Coluna {coluna}: {percentual_vazio*100:.1f}% vazia (limite: {limite_vazio*100:.0f}%). Não preenchida.")
            return df
        
        # Forward fill seguido de backward fill
        df[coluna] = df[coluna].fillna(method='ffill').fillna(method='bfill')
        
        logger.info(f"✓ Coluna {coluna} preenchida por forward fill")
        return df
    
    @staticmethod
    def preencher_por_media(df: pd.DataFrame, coluna: str, limite_vazio: float = 0.2) -> pd.DataFrame:
        """
        Preenche valores numéricos com média
        
        Args:
            df: DataFrame
            coluna: Coluna numérica
            limite_vazio: Limite de valores vazios (%)
            
        Returns:
            DataFrame com preenchimento
        """
        if coluna not in df.columns or not pd.api.types.is_numeric_dtype(df[coluna]):
            return df
        
        percentual_vazio = df[coluna].isna().sum() / len(df)
        
        if percentual_vazio == 0:
            return df
        
        if percentual_vazio > limite_vazio:
            logger.warning(f"Coluna {coluna}: {percentual_vazio*100:.1f}% vazia. Não preenchida.")
            return df
        
        media = df[coluna].mean()
        df[coluna] = df[coluna].fillna(media)
        
        logger.info(f"✓ Coluna {coluna} preenchida com média ({media:.2f})")
        return df
    
    @classmethod
    def preencher_campos_vazios(cls, df: pd.DataFrame, estrategia: str = 'inteligente') -> ResultadoCorrecao:
        """
        Preenche campos vazios com estratégia configurável
        
        Args:
            df: DataFrame
            estrategia: 'inteligente', 'media', 'forwarding'
            
        Returns:
            ResultadoCorrecao
        """
        logger.info(f"Iniciando preenchimento de campos vazios (estratégia: {estrategia})")
        
        df_corrigido = df.copy()
        preenchimentos = []
        
        for coluna in df_corrigido.columns:
            nulos_antes = df_corrigido[coluna].isna().sum()
            
            if nulos_antes == 0:
                continue
            
            # Aplicar regra específica se existir
            if coluna in cls.REGRAS_PREENCHIMENTO:
                valor = cls.REGRAS_PREENCHIMENTO[coluna]()
                df_corrigido[coluna] = df_corrigido[coluna].fillna(valor)
                nulos_depois = df_corrigido[coluna].isna().sum()
                preenchimentos.append(f"{coluna}: preenchida com valor padrão")
            
            # Estratégia por tipo de dado
            elif estrategia == 'inteligente':
                if pd.api.types.is_numeric_dtype(df_corrigido[coluna]):
                    df_corrigido = cls.preencher_por_media(df_corrigido, coluna)
                elif pd.api.types.is_object_dtype(df_corrigido[coluna]):
                    df_corrigido = cls.preencher_por_forwarding(df_corrigido, coluna)
            
            elif estrategia == 'media' and pd.api.types.is_numeric_dtype(df_corrigido[coluna]):
                df_corrigido = cls.preencher_por_media(df_corrigido, coluna)
            
            elif estrategia == 'forwarding':
                df_corrigido = cls.preencher_por_forwarding(df_corrigido, coluna)
        
        resultado = ResultadoCorrecao(
            sucesso=True,
            registros_processados=len(df),
            registros_corrigidos=df[df.isna().any(axis=1)].shape[0],
            registros_rejeitados=0,
            mensagens=preenchimentos,
            dados_corrigidos=df_corrigido
        )
        
        logger.info(f"✓ Preenchimento de campos vazios concluído")
        return resultado


# ============================================================================
# CORRETOR DE INCONSISTÊNCIAS
# ============================================================================

class CorrectorInconsistencias:
    """Corrige inconsistências entre datasets"""
    
    @staticmethod
    def normalizar_dataset_clientes(df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza dados de clientes"""
        df = df.copy()
        padronizador = PadronizadorFormatos()
        
        # Padronizar nome
        if 'nome' in df.columns:
            df['nome'] = df['nome'].apply(padronizador.padronizar_nome)
        
        # Padronizar email
        if 'email' in df.columns:
            df['email'] = df['email'].apply(padronizador.padronizar_email)
        
        # Padronizar telefone
        if 'telefone' in df.columns:
            df['telefone'] = df['telefone'].apply(padronizador.padronizar_telefone)
        
        # Padronizar estado
        if 'estado' in df.columns:
            df['estado'] = df['estado'].apply(padronizador.padronizar_estado)
        
        # Padronizar datas
        colunas_data = [col for col in df.columns if 'data' in col.lower()]
        for coluna in colunas_data:
            df[coluna] = df[coluna].apply(padronizador.padronizar_data)
        
        return df
    
    @staticmethod
    def normalizar_dataset_produtos(df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza dados de produtos"""
        df = df.copy()
        padronizador = PadronizadorFormatos()
        
        # Padronizar nome
        if 'nome_produto' in df.columns:
            df['nome_produto'] = df['nome_produto'].apply(padronizador.padronizar_nome)
        
        # Converter preço para float
        if 'preco' in df.columns:
            df['preco'] = pd.to_numeric(df['preco'], errors='coerce')
        
        # Converter estoque para int
        if 'estoque' in df.columns:
            df['estoque'] = pd.to_numeric(df['estoque'], errors='coerce').astype('Int64')
        
        # Padronizar datas
        colunas_data = [col for col in df.columns if 'data' in col.lower()]
        for coluna in colunas_data:
            df[coluna] = df[coluna].apply(padronizador.padronizar_data)
        
        # Converter ativo para bool
        if 'ativo' in df.columns:
            df['ativo'] = df['ativo'].astype(bool)
        
        return df
    
    @staticmethod
    def normalizar_dataset_vendas(df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza dados de vendas"""
        df = df.copy()
        padronizador = PadronizadorFormatos()
        
        # Converter IDs para int
        colunas_id = [col for col in df.columns if 'id_' in col.lower()]
        for coluna in colunas_id:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce').astype('Int64')
        
        # Converter quantidade para int
        if 'quantidade' in df.columns:
            df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce').astype('Int64')
        
        # Converter valores para float
        colunas_valor = [col for col in df.columns if 'valor' in col.lower() or 'preco' in col.lower()]
        for coluna in colunas_valor:
            if coluna in df.columns:
                df[coluna] = pd.to_numeric(df[coluna], errors='coerce')
        
        # Padronizar datas
        colunas_data = [col for col in df.columns if 'data' in col.lower()]
        for coluna in colunas_data:
            df[coluna] = df[coluna].apply(padronizador.padronizar_data)
        
        return df
    
    @classmethod
    def corrigir_inconsistencias(cls, datasets: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[pd.DataFrame, ResultadoCorrecao]]:
        """
        Corrige inconsistências em todos os datasets
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            
        Returns:
            Dicionário com {nome: (DataFrame corrigido, ResultadoCorrecao)}
        """
        logger.info("Iniciando correção de inconsistências")
        
        resultados = {}
        
        for nome, df in datasets.items():
            logger.info(f"Normalizando: {nome}")
            df_antes = df.copy()
            
            if nome == 'clientes':
                df_corrigido = cls.normalizar_dataset_clientes(df)
            elif nome == 'produtos':
                df_corrigido = cls.normalizar_dataset_produtos(df)
            elif nome == 'vendas':
                df_corrigido = cls.normalizar_dataset_vendas(df)
            else:
                df_corrigido = df
            
            # Contar mudanças
            mudancas = (df_antes != df_corrigido).sum().sum()
            
            resultado = ResultadoCorrecao(
                sucesso=True,
                registros_processados=len(df),
                registros_corrigidos=mudancas,
                registros_rejeitados=0,
                mensagens=[f"Normalizados {mudancas} campos"],
                dados_corrigidos=df_corrigido
            )
            
            resultados[nome] = (df_corrigido, resultado)
            logger.info(f"✓ {nome}: {mudancas} campos normalizados")
        
        return resultados


# ============================================================================
# VALIDADOR DE RELACIONAMENTOS (FOREIGN KEYS)
# ============================================================================

class ValidadorChavesEstrangeiras:
    """Valida relacionamentos entre datasets"""
    
    @staticmethod
    def validar_fk_clientes_em_vendas(df_clientes: pd.DataFrame, df_vendas: pd.DataFrame) -> ResultadoCorrecao:
        """
        Valida se todos os id_cliente em vendas existem em clientes
        
        Args:
            df_clientes: DataFrame de clientes
            df_vendas: DataFrame de vendas
            
        Returns:
            ResultadoCorrecao
        """
        logger.info("Validando FK: id_cliente (vendas → clientes)")
        
        ids_clientes = set(df_clientes['id_cliente'].unique())
        ids_vendas_invalidos = df_vendas[~df_vendas['id_cliente'].isin(ids_clientes)]
        
        if len(ids_vendas_invalidos) > 0:
            mensagem = f"Encontrados {len(ids_vendas_invalidos)} registros de vendas com cliente não existente"
            logger.warning(mensagem)
            
            resultado = ResultadoCorrecao(
                sucesso=False,
                registros_processados=len(df_vendas),
                registros_corrigidos=0,
                registros_rejeitados=len(ids_vendas_invalidos),
                mensagens=[mensagem]
            )
        else:
            resultado = ResultadoCorrecao(
                sucesso=True,
                registros_processados=len(df_vendas),
                registros_corrigidos=0,
                registros_rejeitados=0,
                mensagens=["Todas as vendas têm cliente válido"]
            )
        
        return resultado
    
    @staticmethod
    def validar_fk_produtos_em_vendas(df_produtos: pd.DataFrame, df_vendas: pd.DataFrame) -> ResultadoCorrecao:
        """
        Valida se todos os id_produto em vendas existem em produtos
        
        Args:
            df_produtos: DataFrame de produtos
            df_vendas: DataFrame de vendas
            
        Returns:
            ResultadoCorrecao
        """
        logger.info("Validando FK: id_produto (vendas → produtos)")
        
        ids_produtos = set(df_produtos['id_produto'].unique())
        ids_vendas_invalidos = df_vendas[~df_vendas['id_produto'].isin(ids_produtos)]
        
        if len(ids_vendas_invalidos) > 0:
            mensagem = f"Encontrados {len(ids_vendas_invalidos)} registros de vendas com produto não existente"
            logger.warning(mensagem)
            
            resultado = ResultadoCorrecao(
                sucesso=False,
                registros_processados=len(df_vendas),
                registros_corrigidos=0,
                registros_rejeitados=len(ids_vendas_invalidos),
                mensagens=[mensagem]
            )
        else:
            resultado = ResultadoCorrecao(
                sucesso=True,
                registros_processados=len(df_vendas),
                registros_corrigidos=0,
                registros_rejeitados=0,
                mensagens=["Todos os produtos em vendas existem"]
            )
        
        return resultado
    
    @staticmethod
    def remover_vendas_invalidas(df_vendas: pd.DataFrame, ids_clientes_validos: set, ids_produtos_validos: set) -> pd.DataFrame:
        """
        Remove vendas com referências inválidas
        
        Args:
            df_vendas: DataFrame de vendas
            ids_clientes_validos: Conjunto de IDs válidos de clientes
            ids_produtos_validos: Conjunto de IDs válidos de produtos
            
        Returns:
            DataFrame filtrado
        """
        df_filtrado = df_vendas[
            (df_vendas['id_cliente'].isin(ids_clientes_validos)) &
            (df_vendas['id_produto'].isin(ids_produtos_validos))
        ].reset_index(drop=True)
        
        removidas = len(df_vendas) - len(df_filtrado)
        logger.info(f"✓ {removidas} vendas com FK inválida removidas")
        
        return df_filtrado
    
    @classmethod
    def validar_todas_chaves(cls, datasets: Dict[str, pd.DataFrame]) -> Dict[str, ResultadoCorrecao]:
        """
        Valida todas as chaves estrangeiras
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            
        Returns:
            Dicionário com resultados de validação
        """
        logger.info("Iniciando validação de chaves estrangeiras")
        
        resultados = {}
        
        # Validar FK de vendas
        if 'clientes' in datasets and 'vendas' in datasets:
            resultado_fk_clientes = cls.validar_fk_clientes_em_vendas(
                datasets['clientes'], datasets['vendas']
            )
            resultados['fk_clientes_vendas'] = resultado_fk_clientes
        
        if 'produtos' in datasets and 'vendas' in datasets:
            resultado_fk_produtos = cls.validar_fk_produtos_em_vendas(
                datasets['produtos'], datasets['vendas']
            )
            resultados['fk_produtos_vendas'] = resultado_fk_produtos
        
        return resultados


# ============================================================================
# ORQUESTRADOR DE CORREÇÕES
# ============================================================================

class OrquestradorCorrecoes:
    """Orquestra todas as operações de correção"""
    
    def __init__(self):
        """Inicializa orquestrador"""
        self.padronizador = PadronizadorFormatos()
        self.removedor = RemovedorDuplicatas()
        self.preenchedor = PreenchedorCamposVazios()
        self.corretor = CorrectorInconsistencias()
        self.validador = ValidadorChavesEstrangeiras()
        self.relatorio = {}
    
    def corrigir_datasets(self, datasets: Dict[str, pd.DataFrame], 
                         operacoes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Aplica todas as correções aos datasets
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            operacoes: Lista de operações a executar (se None, executa todas)
            
        Returns:
            Dicionário com {nome: DataFrame corrigido}
        """
        if operacoes is None:
            operacoes = [
                'remover_duplicatas',
                'preencher_vazios',
                'normalizar_formatos',
                'validar_chaves'
            ]
        
        datasets_corrigidos = {nome: df.copy() for nome, df in datasets.items()}
        
        logger.info("=" * 80)
        logger.info("INICIANDO PIPELINE DE CORREÇÕES")
        logger.info("=" * 80)
        
        # 1. Remover duplicatas
        if 'remover_duplicatas' in operacoes:
            logger.info("\n📍 Etapa 1: Removendo Duplicatas")
            for nome in ['clientes', 'produtos', 'vendas']:
                if nome in datasets_corrigidos:
                    coluna_id = f'id_{nome.rstrip("s")}'
                    resultado = self.removedor.remover_duplicatas_inteligentes(
                        datasets_corrigidos[nome], coluna_id
                    )
                    datasets_corrigidos[nome] = resultado.dados_corrigidos
                    self.relatorio[f'{nome}_duplicatas'] = resultado
        
        # 2. Preencher campos vazios
        if 'preencher_vazios' in operacoes:
            logger.info("\n📍 Etapa 2: Preenchendo Campos Vazios")
            for nome in ['clientes', 'produtos', 'vendas']:
                if nome in datasets_corrigidos:
                    resultado = self.preenchedor.preencher_campos_vazios(
                        datasets_corrigidos[nome], estrategia='inteligente'
                    )
                    datasets_corrigidos[nome] = resultado.dados_corrigidos
                    self.relatorio[f'{nome}_vazios'] = resultado
        
        # 3. Normalizar formatos
        if 'normalizar_formatos' in operacoes:
            logger.info("\n📍 Etapa 3: Normalizando Formatos")
            resultados_norm = self.corretor.corrigir_inconsistencias(datasets_corrigidos)
            for nome, (df_corrigido, resultado) in resultados_norm.items():
                datasets_corrigidos[nome] = df_corrigido
                self.relatorio[f'{nome}_normalizacao'] = resultado
        
        # 4. Validar chaves estrangeiras
        if 'validar_chaves' in operacoes:
            logger.info("\n📍 Etapa 4: Validando Chaves Estrangeiras")
            resultados_fk = self.validador.validar_todas_chaves(datasets_corrigidos)
            self.relatorio.update(resultados_fk)
            
            # Se houver erros, remover registros inválidos
            if 'vendas' in datasets_corrigidos:
                ids_clientes = set(datasets_corrigidos['clientes']['id_cliente'].unique())
                ids_produtos = set(datasets_corrigidos['produtos']['id_produto'].unique())
                datasets_corrigidos['vendas'] = self.validador.remover_vendas_invalidas(
                    datasets_corrigidos['vendas'], ids_clientes, ids_produtos
                )
        
        logger.info("\n" + "=" * 80)
        logger.info("PIPELINE DE CORREÇÕES CONCLUÍDO")
        logger.info("=" * 80)
        
        return datasets_corrigidos
    
    def gerar_relatorio(self) -> pd.DataFrame:
        """
        Gera relatório consolidado das correções
        
        Returns:
            DataFrame com resumo de todas as operações
        """
        relatorio_data = []
        
        for operacao, resultado in self.relatorio.items():
            relatorio_data.append({
                'operacao': operacao,
                'sucesso': resultado.sucesso,
                'registros_processados': resultado.registros_processados,
                'registros_corrigidos': resultado.registros_corrigidos,
                'registros_rejeitados': resultado.registros_rejeitados,
                'taxa_sucesso': f"{resultado.taxa_sucesso:.1f}%",
                'mensagens': '; '.join(resultado.mensagens[:3])  # Primeiras 3 mensagens
            })
        
        return pd.DataFrame(relatorio_data)
    
    def salvar_datasets_corrigidos(self, datasets: Dict[str, pd.DataFrame], 
                                    diretorio: str = 'datasets_corrigidos'):
        """
        Salva datasets corrigidos em CSV
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            diretorio: Diretório de saída
        """
        Path(diretorio).mkdir(exist_ok=True)
        
        for nome, df in datasets.items():
            caminho = Path(diretorio) / f'{nome}_corrigido.csv'
            df.to_csv(caminho, index=False, encoding='utf-8')
            logger.info(f"✓ Salvo: {caminho}")


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Carregar datasets
    datasets_path = Path("notebooks/datasets")
    
    datasets = {
        "clientes": pd.read_csv(datasets_path / "clientes.csv"),
        "produtos": pd.read_csv(datasets_path / "produtos.csv"),
        "vendas": pd.read_csv(datasets_path / "vendas.csv"),
    }
    
    # Exibir datasets antes
    print("\n" + "=" * 80)
    print("DATASETS ANTES DA CORREÇÃO")
    print("=" * 80)
    for nome, df in datasets.items():
        print(f"\n{nome.upper()}: {len(df)} registros, {len(df.columns)} colunas")
        print(f"  Valores nulos: {df.isna().sum().sum()}")
    
    # Criar orquestrador e executar correções
    orquestrador = OrquestradorCorrecoes()
    datasets_corrigidos = orquestrador.corrigir_datasets(datasets)
    
    # Exibir datasets depois
    print("\n" + "=" * 80)
    print("DATASETS APÓS CORREÇÃO")
    print("=" * 80)
    for nome, df in datasets_corrigidos.items():
        print(f"\n{nome.upper()}: {len(df)} registros, {len(df.columns)} colunas")
        print(f"  Valores nulos: {df.isna().sum().sum()}")
    
    # Gerar e exibir relatório
    print("\n" + "=" * 80)
    print("RELATÓRIO DE CORREÇÕES")
    print("=" * 80)
    relatorio_df = orquestrador.gerar_relatorio()
    print(relatorio_df.to_string(index=False))
    
    # Salvar datasets corrigidos
    orquestrador.salvar_datasets_corrigidos(datasets_corrigidos)
    
    print("\n✓ Processo completo! Datasets corrigidos salvos em 'datasets_corrigidos/'")
