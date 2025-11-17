"""
Pipeline de Ingestão de Dados com Schema Validation
Carregamento de múltiplas fontes, validação rigorosa e auditoria
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import hashlib


# ============================================================================
# CONFIGURAÇÃO DE LOGGING E AUDITORIA
# ============================================================================

class LoggerConfig:
    """Configura logging centralizado com auditoria"""
    
    @staticmethod
    def setup_logging(log_dir: str = "logs") -> logging.Logger:
        """
        Configura sistema de logging com múltiplos handlers
        
        Args:
            log_dir: Diretório para armazenar logs
            
        Returns:
            Logger configurado
        """
        Path(log_dir).mkdir(exist_ok=True)
        
        logger = logging.getLogger("DataPipeline")
        logger.setLevel(logging.DEBUG)
        
        # Handler para arquivo de logs gerais
        fh_general = logging.FileHandler(
            f"{log_dir}/pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        )
        fh_general.setLevel(logging.DEBUG)
        
        # Handler para arquivo de auditoria
        fh_audit = logging.FileHandler(
            f"{log_dir}/auditoria_{datetime.now().strftime('%Y%m%d')}.log"
        )
        fh_audit.setLevel(logging.INFO)
        
        # Handler para console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formato detalhado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        fh_general.setFormatter(formatter)
        fh_audit.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh_general)
        logger.addHandler(fh_audit)
        logger.addHandler(ch)
        
        return logger


logger = LoggerConfig.setup_logging()


# ============================================================================
# DEFINIÇÃO DE SCHEMAS E TIPOS
# ============================================================================

class TipoFonte(Enum):
    """Tipos de fontes de dados suportadas"""
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"


@dataclass
class SchemaColuna:
    """Define schema de uma coluna"""
    nome: str
    tipo: str  # 'int', 'float', 'string', 'datetime', 'bool'
    obrigatorio: bool = True
    valores_validos: Optional[List[Any]] = None
    intervalo_min: Optional[float] = None
    intervalo_max: Optional[float] = None
    regex_pattern: Optional[str] = None
    tamanho_max_string: Optional[int] = None


@dataclass
class Schema:
    """Define schema completo de um dataset"""
    nome_dataset: str
    colunas: List[SchemaColuna]
    chave_primaria: Optional[List[str]] = None
    
    def validar_coluna_existe(self, nome_coluna: str) -> bool:
        """Verifica se coluna existe no schema"""
        return any(col.nome == nome_coluna for col in self.colunas)
    
    def obter_coluna(self, nome_coluna: str) -> Optional[SchemaColuna]:
        """Obtém configuração de uma coluna"""
        for col in self.colunas:
            if col.nome == nome_coluna:
                return col
        return None


# ============================================================================
# SCHEMAS PRÉ-DEFINIDOS
# ============================================================================

SCHEMA_CLIENTES = Schema(
    nome_dataset="clientes",
    chave_primaria=["id_cliente"],
    colunas=[
        SchemaColuna("id_cliente", "int", obrigatorio=True),
        SchemaColuna("nome", "string", obrigatorio=True, tamanho_max_string=255),
        SchemaColuna("email", "string", obrigatorio=True, 
                    regex_pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
        SchemaColuna("telefone", "string", obrigatorio=False, 
                    regex_pattern=r"^\d{11}$"),
        SchemaColuna("data_nascimento", "datetime", obrigatorio=False),
        SchemaColuna("cidade", "string", obrigatorio=False),
        SchemaColuna("estado", "string", obrigatorio=False, 
                    valores_validos=['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 
                                    'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 
                                    'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']),
        SchemaColuna("data_cadastro", "datetime", obrigatorio=True),
    ]
)

SCHEMA_PRODUTOS = Schema(
    nome_dataset="produtos",
    chave_primaria=["id_produto"],
    colunas=[
        SchemaColuna("id_produto", "int", obrigatorio=True),
        SchemaColuna("nome_produto", "string", obrigatorio=True, tamanho_max_string=255),
        SchemaColuna("categoria", "string", obrigatorio=True,
                    valores_validos=['Eletrônicos', 'Informática', 'Casa', 'Esportes', 
                                    'Moda', 'Livros', 'Saúde', 'Alimentos', 'Beleza', 'Outros']),
        SchemaColuna("preco", "float", obrigatorio=True, intervalo_min=0.01),
        SchemaColuna("estoque", "int", obrigatorio=True, intervalo_min=0),
        SchemaColuna("data_criacao", "datetime", obrigatorio=True),
        SchemaColuna("ativo", "bool", obrigatorio=True),
    ]
)

SCHEMA_VENDAS = Schema(
    nome_dataset="vendas",
    chave_primaria=["id_venda"],
    colunas=[
        SchemaColuna("id_venda", "int", obrigatorio=True),
        SchemaColuna("id_cliente", "int", obrigatorio=True),
        SchemaColuna("id_produto", "int", obrigatorio=True),
        SchemaColuna("quantidade", "int", obrigatorio=True, intervalo_min=1),
        SchemaColuna("valor_unitario", "float", obrigatorio=True, intervalo_min=0.01),
        SchemaColuna("valor_total", "float", obrigatorio=True, intervalo_min=0.01),
        SchemaColuna("data_venda", "datetime", obrigatorio=True),
        SchemaColuna("status", "string", obrigatorio=True, 
                    valores_validos=["Concluída", "Pendente", "Cancelada"]),
    ]
)


# ============================================================================
# VALIDADOR DE SCHEMA
# ============================================================================

class ValidadorSchema:
    """Valida dados contra um schema definido"""
    
    def __init__(self, schema: Schema, logger_obj: logging.Logger):
        """
        Args:
            schema: Schema a ser aplicado
            logger_obj: Logger para registro de eventos
        """
        self.schema = schema
        self.logger = logger_obj
        self.erros = []
        self.avisos = []
    
    def validar_dataframe(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida um dataframe contra o schema
        
        Args:
            df: DataFrame a ser validado
            
        Returns:
            (sucesso, relatório)
        """
        self.erros = []
        self.avisos = []
        relatorio = {
            "dataset": self.schema.nome_dataset,
            "timestamp": datetime.now().isoformat(),
            "linhas_totais": len(df),
            "colunas_esperadas": len(self.schema.colunas),
            "colunas_encontradas": len(df.columns),
            "validacoes": {}
        }
        
        # Validar estrutura do DataFrame
        self._validar_estrutura(df, relatorio)
        
        # Validar tipos de dados
        self._validar_tipos(df, relatorio)
        
        # Validar valores
        self._validar_valores(df, relatorio)
        
        # Validar completude
        self._validar_completude(df, relatorio)
        
        # Validar unicidade de chave primária
        if self.schema.chave_primaria:
            self._validar_chave_primaria(df, relatorio)
        
        sucesso = len(self.erros) == 0
        relatorio["sucesso"] = sucesso
        relatorio["total_erros"] = len(self.erros)
        relatorio["total_avisos"] = len(self.avisos)
        relatorio["erros"] = self.erros
        relatorio["avisos"] = self.avisos
        
        return sucesso, relatorio
    
    def _validar_estrutura(self, df: pd.DataFrame, relatorio: Dict):
        """Valida colunas e estrutura básica"""
        relatorio["validacoes"]["estrutura"] = {
            "status": "ok",
            "detalhes": []
        }
        
        colunas_esperadas = {col.nome for col in self.schema.colunas}
        colunas_encontradas = set(df.columns)
        
        # Colunas faltantes
        faltantes = colunas_esperadas - colunas_encontradas
        if faltantes:
            msg = f"Colunas faltantes: {', '.join(faltantes)}"
            self.erros.append(msg)
            relatorio["validacoes"]["estrutura"]["status"] = "erro"
            relatorio["validacoes"]["estrutura"]["detalhes"].append(msg)
        
        # Colunas extras
        extras = colunas_encontradas - colunas_esperadas
        if extras:
            msg = f"Colunas extras encontradas: {', '.join(extras)}"
            self.avisos.append(msg)
            relatorio["validacoes"]["estrutura"]["detalhes"].append(msg)
    
    def _validar_tipos(self, df: pd.DataFrame, relatorio: Dict):
        """Valida tipos de dados"""
        relatorio["validacoes"]["tipos"] = {
            "status": "ok",
            "detalhes": []
        }
        
        for col_schema in self.schema.colunas:
            if col_schema.nome not in df.columns:
                continue
            
            col_dados = df[col_schema.nome]
            
            try:
                if col_schema.tipo == "int":
                    if not pd.api.types.is_integer_dtype(col_dados):
                        # Tentar converter
                        try:
                            df[col_schema.nome] = pd.to_numeric(col_dados, errors='coerce')
                        except:
                            msg = f"Coluna '{col_schema.nome}': não é inteiro"
                            self.erros.append(msg)
                            relatorio["validacoes"]["tipos"]["status"] = "erro"
                
                elif col_schema.tipo == "float":
                    if not pd.api.types.is_float_dtype(col_dados):
                        try:
                            df[col_schema.nome] = pd.to_numeric(col_dados, errors='coerce')
                        except:
                            msg = f"Coluna '{col_schema.nome}': não é float"
                            self.erros.append(msg)
                            relatorio["validacoes"]["tipos"]["status"] = "erro"
                
                elif col_schema.tipo == "datetime":
                    try:
                        pd.to_datetime(col_dados)
                    except:
                        msg = f"Coluna '{col_schema.nome}': não é data válida"
                        self.erros.append(msg)
                        relatorio["validacoes"]["tipos"]["status"] = "erro"
                
                elif col_schema.tipo == "bool":
                    if not pd.api.types.is_bool_dtype(col_dados):
                        msg = f"Coluna '{col_schema.nome}': não é booleana"
                        self.avisos.append(msg)
                
            except Exception as e:
                msg = f"Coluna '{col_schema.nome}': erro ao validar tipo - {str(e)}"
                self.erros.append(msg)
                relatorio["validacoes"]["tipos"]["status"] = "erro"
    
    def _validar_valores(self, df: pd.DataFrame, relatorio: Dict):
        """Valida valores contra restrições"""
        relatorio["validacoes"]["valores"] = {
            "status": "ok",
            "detalhes": []
        }
        
        for col_schema in self.schema.colunas:
            if col_schema.nome not in df.columns:
                continue
            
            col_dados = df[col_schema.nome]
            
            # Validar intervalo
            if col_schema.intervalo_min is not None:
                invalidos = (col_dados < col_schema.intervalo_min).sum()
                if invalidos > 0:
                    msg = f"Coluna '{col_schema.nome}': {invalidos} valores < {col_schema.intervalo_min}"
                    self.erros.append(msg)
                    relatorio["validacoes"]["valores"]["status"] = "erro"
            
            if col_schema.intervalo_max is not None:
                invalidos = (col_dados > col_schema.intervalo_max).sum()
                if invalidos > 0:
                    msg = f"Coluna '{col_schema.nome}': {invalidos} valores > {col_schema.intervalo_max}"
                    self.erros.append(msg)
                    relatorio["validacoes"]["valores"]["status"] = "erro"
            
            # Validar valores em conjunto
            if col_schema.valores_validos:
                invalidos = ~col_dados.isin(col_schema.valores_validos).sum()
                if invalidos > 0:
                    msg = f"Coluna '{col_schema.nome}': {invalidos} valores fora do conjunto permitido"
                    self.erros.append(msg)
                    relatorio["validacoes"]["valores"]["status"] = "erro"
            
            # Validar regex
            if col_schema.regex_pattern:
                import re
                invalidos = col_dados.astype(str).apply(
                    lambda x: not re.match(col_schema.regex_pattern, str(x))
                ).sum()
                if invalidos > 0:
                    msg = f"Coluna '{col_schema.nome}': {invalidos} valores não correspondem ao padrão"
                    self.erros.append(msg)
                    relatorio["validacoes"]["valores"]["status"] = "erro"
            
            # Validar tamanho de string
            if col_schema.tamanho_max_string:
                invalidos = (col_dados.astype(str).str.len() > col_schema.tamanho_max_string).sum()
                if invalidos > 0:
                    msg = f"Coluna '{col_schema.nome}': {invalidos} strings excedem {col_schema.tamanho_max_string} caracteres"
                    self.avisos.append(msg)
    
    def _validar_completude(self, df: pd.DataFrame, relatorio: Dict):
        """Valida campos obrigatórios"""
        relatorio["validacoes"]["completude"] = {
            "status": "ok",
            "detalhes": []
        }
        
        for col_schema in self.schema.colunas:
            if col_schema.obrigatorio and col_schema.nome in df.columns:
                nulos = df[col_schema.nome].isna().sum()
                if nulos > 0:
                    msg = f"Coluna '{col_schema.nome}': {nulos} valores nulos (obrigatória)"
                    self.erros.append(msg)
                    relatorio["validacoes"]["completude"]["status"] = "erro"
    
    def _validar_chave_primaria(self, df: pd.DataFrame, relatorio: Dict):
        """Valida unicidade da chave primária"""
        relatorio["validacoes"]["chave_primaria"] = {
            "status": "ok",
            "detalhes": []
        }
        
        try:
            colunas_chave = [col for col in self.schema.chave_primaria if col in df.columns]
            
            if len(colunas_chave) != len(self.schema.chave_primaria):
                msg = f"Colunas de chave primária faltando"
                self.erros.append(msg)
                relatorio["validacoes"]["chave_primaria"]["status"] = "erro"
                return
            
            # Verificar duplicatas
            duplicatas = df.duplicated(subset=colunas_chave).sum()
            if duplicatas > 0:
                msg = f"Chave primária: {duplicatas} registros duplicados"
                self.erros.append(msg)
                relatorio["validacoes"]["chave_primaria"]["status"] = "erro"
            
            # Verificar nulos na chave
            nulos_chave = df[colunas_chave].isna().sum().sum()
            if nulos_chave > 0:
                msg = f"Chave primária: {nulos_chave} valores nulos"
                self.erros.append(msg)
                relatorio["validacoes"]["chave_primaria"]["status"] = "erro"
        
        except Exception as e:
            msg = f"Erro ao validar chave primária: {str(e)}"
            self.erros.append(msg)
            relatorio["validacoes"]["chave_primaria"]["status"] = "erro"


# ============================================================================
# CARREGADOR DE DADOS
# ============================================================================

class CarregadorDados:
    """Carrega dados de múltiplas fontes com tratamento de erros"""
    
    def __init__(self, logger_obj: logging.Logger):
        """
        Args:
            logger_obj: Logger para registro de eventos
        """
        self.logger = logger_obj
    
    def carregar(self, caminho: str, tipo: TipoFonte = None) -> Optional[pd.DataFrame]:
        """
        Carrega dados de arquivo
        
        Args:
            caminho: Caminho do arquivo
            tipo: Tipo de arquivo (inferido se não especificado)
            
        Returns:
            DataFrame carregado ou None em caso de erro
        """
        try:
            caminho_obj = Path(caminho)
            
            if not caminho_obj.exists():
                self.logger.error(f"Arquivo não encontrado: {caminho}")
                return None
            
            # Inferir tipo se não especificado
            if tipo is None:
                extensao = caminho_obj.suffix.lower()
                tipo_map = {
                    '.csv': TipoFonte.CSV,
                    '.json': TipoFonte.JSON,
                    '.parquet': TipoFonte.PARQUET,
                    '.xlsx': TipoFonte.EXCEL,
                    '.xls': TipoFonte.EXCEL,
                }
                tipo = tipo_map.get(extensao, TipoFonte.CSV)
            
            # Registrar auditoria
            self.logger.info(f"Iniciando carregamento: {caminho} (tipo: {tipo.value})")
            
            # Carregar conforme tipo
            if tipo == TipoFonte.CSV:
                df = self._carregar_csv(caminho)
            elif tipo == TipoFonte.JSON:
                df = self._carregar_json(caminho)
            elif tipo == TipoFonte.PARQUET:
                df = self._carregar_parquet(caminho)
            elif tipo == TipoFonte.EXCEL:
                df = self._carregar_excel(caminho)
            else:
                self.logger.error(f"Tipo de arquivo não suportado: {tipo}")
                return None
            
            if df is not None:
                self.logger.info(f"✓ Carregamento bem-sucedido: {len(df)} linhas, {len(df.columns)} colunas")
                # Registrar hash para auditoria
                hash_dados = self._calcular_hash(df)
                self.logger.info(f"  Hash dos dados: {hash_dados}")
            
            return df
        
        except Exception as e:
            self.logger.error(f"Erro ao carregar {caminho}: {type(e).__name__}: {str(e)}")
            return None
    
    def _carregar_csv(self, caminho: str) -> Optional[pd.DataFrame]:
        """Carrega arquivo CSV com tratamento de erros"""
        try:
            # Tentar várias codificações
            for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                try:
                    df = pd.read_csv(caminho, encoding=encoding)
                    return df
                except UnicodeDecodeError:
                    continue
            
            self.logger.error(f"Não foi possível decodificar {caminho} com nenhuma codificação")
            return None
        
        except pd.errors.ParserError as e:
            self.logger.error(f"Erro ao parsear CSV: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Erro inesperado ao carregar CSV: {str(e)}")
            return None
    
    def _carregar_json(self, caminho: str) -> Optional[pd.DataFrame]:
        """Carrega arquivo JSON"""
        try:
            df = pd.read_json(caminho)
            return df
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON inválido: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao carregar JSON: {str(e)}")
            return None
    
    def _carregar_parquet(self, caminho: str) -> Optional[pd.DataFrame]:
        """Carrega arquivo Parquet"""
        try:
            df = pd.read_parquet(caminho)
            return df
        except Exception as e:
            self.logger.error(f"Erro ao carregar Parquet: {str(e)}")
            return None
    
    def _carregar_excel(self, caminho: str) -> Optional[pd.DataFrame]:
        """Carrega arquivo Excel"""
        try:
            df = pd.read_excel(caminho)
            return df
        except Exception as e:
            self.logger.error(f"Erro ao carregar Excel: {str(e)}")
            return None
    
    @staticmethod
    def _calcular_hash(df: pd.DataFrame) -> str:
        """Calcula hash dos dados para auditoria"""
        try:
            conteudo = pd.util.hash_pandas_object(df, index=True).sum()
            return hashlib.md5(str(conteudo).encode()).hexdigest()[:16]
        except:
            return "hash_indisponivel"


# ============================================================================
# PIPELINE DE INGESTÃO
# ============================================================================

class PipelineIngestao:
    """Orquestra o pipeline de ingestão com validação"""
    
    def __init__(self, logger_obj: logging.Logger = None):
        """
        Args:
            logger_obj: Logger (usa o global se não especificado)
        """
        self.logger = logger_obj or logger
        self.carregador = CarregadorDados(self.logger)
        self.relatorios = []
    
    def processar_dataset(self, caminho: str, schema: Schema) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        Processa um dataset completo: carregamento e validação
        
        Args:
            caminho: Caminho do arquivo
            schema: Schema a aplicar
            
        Returns:
            (DataFrame validado, relatório de validação)
        """
        # Carregar
        df = self.carregador.carregar(caminho)
        
        if df is None:
            relatorio = {
                "dataset": schema.nome_dataset,
                "carregamento": "erro",
                "timestamp": datetime.now().isoformat()
            }
            self.relatorios.append(relatorio)
            return None, relatorio
        
        # Validar
        validador = ValidadorSchema(schema, self.logger)
        sucesso, relatorio_validacao = validador.validar_dataframe(df)
        
        # Log do resultado
        if sucesso:
            self.logger.info(f"✓ Validação bem-sucedida para {schema.nome_dataset}")
        else:
            self.logger.warning(f"✗ Validação com erros para {schema.nome_dataset}")
            for erro in relatorio_validacao["erros"]:
                self.logger.error(f"  - {erro}")
        
        relatorio_validacao["carregamento"] = "sucesso"
        self.relatorios.append(relatorio_validacao)
        
        return df if sucesso else None, relatorio_validacao
    
    def processar_multiplas_fontes(self, sources: Dict[str, Tuple[str, Schema]]) -> Dict[str, Tuple[Optional[pd.DataFrame], Dict]]:
        """
        Processa múltiplas fontes de dados
        
        Args:
            sources: Dict com {nome: (caminho, schema)}
            
        Returns:
            Dict com {nome: (DataFrame, relatório)}
        """
        self.logger.info(f"Iniciando processamento de {len(sources)} fontes de dados")
        
        resultados = {}
        for nome, (caminho, schema) in sources.items():
            self.logger.info(f"Processando: {nome}")
            df, relatorio = self.processar_dataset(caminho, schema)
            resultados[nome] = (df, relatorio)
        
        self.logger.info(f"Processamento concluído")
        return resultados
    
    def gerar_relatorio_final(self) -> Dict:
        """Gera relatório consolidado de auditoria"""
        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "total_datasets": len(self.relatorios),
            "datasets_sucesso": sum(1 for r in self.relatorios if r.get("sucesso", False)),
            "datasets_erro": sum(1 for r in self.relatorios if not r.get("sucesso", True)),
            "detalhes": self.relatorios
        }
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"RELATÓRIO FINAL DE AUDITORIA")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Timestamp: {relatorio['timestamp']}")
        self.logger.info(f"Total de datasets: {relatorio['total_datasets']}")
        self.logger.info(f"Sucesso: {relatorio['datasets_sucesso']}")
        self.logger.info(f"Erros: {relatorio['datasets_erro']}")
        self.logger.info(f"{'='*60}\n")
        
        return relatorio
    
    def salvar_relatorio(self, caminho: str = "logs/relatorio_auditoria.json"):
        """Salva relatório em JSON para análise"""
        Path(Path(caminho).parent).mkdir(parents=True, exist_ok=True)
        
        relatorio = self.gerar_relatorio_final()
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Relatório salvo em: {caminho}")


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Inicializar pipeline
    pipeline = PipelineIngestao()
    
    # Definir fontes de dados
    datasets_path = Path("notebooks/datasets")
    
    sources = {
        "clientes": (str(datasets_path / "clientes.csv"), SCHEMA_CLIENTES),
        "produtos": (str(datasets_path / "produtos.csv"), SCHEMA_PRODUTOS),
        "vendas": (str(datasets_path / "vendas.csv"), SCHEMA_VENDAS),
    }
    
    # Processar múltiplas fontes
    resultados = pipeline.processar_multiplas_fontes(sources)
    
    # Gerar relatório de auditoria
    pipeline.salvar_relatorio()
    
    # Exibir resumo
    print("\n" + "="*60)
    print("RESUMO DO PROCESSAMENTO")
    print("="*60)
    
    for nome, (df, relatorio) in resultados.items():
        status = "✓ OK" if relatorio.get("sucesso", False) else "✗ ERRO"
        print(f"{nome}: {status}")
        if df is not None:
            print(f"  - Linhas: {len(df)}")
            print(f"  - Colunas: {len(df.columns)}")
        if relatorio.get("total_erros", 0) > 0:
            print(f"  - Erros: {relatorio['total_erros']}")
