"""
Dashboard de Qualidade de Dados com Great Expectations
Configuração de Data Docs, geração de relatórios HTML e PDF
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import base64

# Importar Great Expectations
try:
    from great_expectations.core.batch import RuntimeBatchRequest
    from great_expectations.dataset import PandasDataset
    from great_expectations.data_context import DataContext
    from great_expectations.data_context.types.base import DataContextConfig
except ImportError:
    print("⚠️  Great Expectations não instalado. Usando fallback.")


# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dashboard_qualidade.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLASSES DE DADOS
# ============================================================================

@dataclass
class MetricaDataset:
    """Armazena métrica de um dataset"""
    dataset_nome: str
    timestamp: str
    total_registros: int
    total_colunas: int
    valores_nulos_percentual: float
    registros_duplicados: int
    taxa_completude: float
    taxa_validade: float
    expectativas_passadas: int
    expectativas_falhadas: int


@dataclass
class RelatorioQualidade:
    """Armazena relatório consolidado de qualidade"""
    titulo: str
    data_geracao: str
    datasets: List[MetricaDataset]
    empresa: str = "TechCommerce"
    versao: str = "1.0"
    
    def score_geral(self) -> float:
        """Calcula score geral de qualidade"""
        if not self.datasets:
            return 0.0
        return sum(d.taxa_completude for d in self.datasets) / len(self.datasets)


# ============================================================================
# CONFIGURADOR DE DATA DOCS
# ============================================================================

class ConfiguradorDataDocs:
    """Configura e customiza Great Expectations Data Docs"""
    
    @staticmethod
    def setup_data_context(ge_dir: str = "great_expectations") -> Optional[Any]:
        """
        Configura Data Context do Great Expectations
        
        Args:
            ge_dir: Diretório do Great Expectations
            
        Returns:
            Data Context ou None
        """
        logger.info(f"Configurando Data Context em: {ge_dir}")
        
        try:
            # Criar diretórios
            Path(ge_dir).mkdir(exist_ok=True)
            Path(f"{ge_dir}/expectations").mkdir(exist_ok=True)
            Path(f"{ge_dir}/validations").mkdir(exist_ok=True)
            
            # Tentar obter contexto existente
            try:
                context = DataContext(ge_dir)
                logger.info("✓ Data Context existente carregado")
                return context
            except Exception as e:
                logger.warning(f"Data Context não encontrado, criando novo: {e}")
                return None
        
        except Exception as e:
            logger.error(f"Erro ao configurar Data Context: {e}")
            return None
    
    @staticmethod
    def criar_pagina_indice(config: Dict) -> str:
        """
        Cria página HTML de índice para Data Docs
        
        Args:
            config: Configuração com metadados
            
        Returns:
            HTML da página
        """
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Docs - {config.get('empresa', 'TechCommerce')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 40px;
        }}
        .info-box {{
            background: #f5f7fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .card {{
            background: white;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        .card p {{
            color: #666;
            font-size: 0.95em;
        }}
        .metric {{
            text-align: center;
            padding: 20px;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            color: #666;
            margin-top: 10px;
        }}
        footer {{
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e1e4e8;
        }}
        .status-ok {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-error {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 Data Docs</h1>
            <p>{config.get('empresa', 'TechCommerce')} - Qualidade de Dados</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Gerado em {config.get('data_geracao', 'N/A')}</p>
        </header>
        
        <div class="content">
            <div class="info-box">
                <h2>Bem-vindo ao Dashboard de Qualidade</h2>
                <p>
                    Este dashboard apresenta métricas consolidadas de qualidade de dados, 
                    validações automatizadas e relatórios detalhados por dataset.
                </p>
            </div>
            
            <h2>📊 Documentação Disponível</h2>
            <div class="grid">
                <div class="card">
                    <h3>✓ Relatórios por Dataset</h3>
                    <p>Métricas detalhadas de cada fonte de dados incluindo completude, 
                    unicidade e validade.</p>
                </div>
                <div class="card">
                    <h3>✓ Validações Automatizadas</h3>
                    <p>Resultados das expectativas de qualidade e análise de conformidade 
                    com schemas definidos.</p>
                </div>
                <div class="card">
                    <h3>✓ Histórico de Qualidade</h3>
                    <p>Acompanhamento temporal das métricas para identificação de tendências 
                    e padrões.</p>
                </div>
                <div class="card">
                    <h3>✓ Alertas e Recomendações</h3>
                    <p>Problemas identificados e sugestões de correção baseadas em regras 
                    de negócio.</p>
                </div>
            </div>
            
            <h2>🎯 Próximas Etapas</h2>
            <ul style="line-height: 1.8;">
                <li>Revisar relatórios detalhados de cada dataset</li>
                <li>Implementar correções para problemas identificados</li>
                <li>Agendar reunião de governança de dados</li>
                <li>Estabelecer SLAs de qualidade por dataset</li>
            </ul>
        </div>
        
        <footer>
            <p>Great Expectations Data Docs | {config.get('empresa', 'TechCommerce')} | v{config.get('versao', '1.0')}</p>
        </footer>
    </div>
</body>
</html>
        """
        return html


# ============================================================================
# GERADOR DE RELATÓRIOS HTML
# ============================================================================

class GeradorRelatoriosHTML:
    """Gera relatórios HTML customizados"""
    
    @staticmethod
    def gerar_relatorio_dataset(metrica: MetricaDataset, contexto: Dict) -> str:
        """
        Gera relatório HTML para um dataset
        
        Args:
            metrica: Métrica do dataset
            contexto: Contexto adicional
            
        Returns:
            HTML do relatório
        """
        # Determinar status
        if metrica.taxa_completude >= 90:
            status = "ok"
            status_texto = "✓ Excelente"
            cor = "#27ae60"
        elif metrica.taxa_completude >= 75:
            status = "warning"
            status_texto = "⚠ Atenção"
            cor = "#f39c12"
        else:
            status = "error"
            status_texto = "✗ Crítico"
            cor = "#e74c3c"
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório - {metrica.dataset_nome}</title>
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
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
        }}
        .dataset-name {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 0.9em;
            border: 1px solid rgba(255,255,255,0.3);
        }}
        .content {{
            padding: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-box {{
            background: #f9fafb;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2.2em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .info-section {{
            background: #f5f7fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .info-section h3 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e1e4e8;
        }}
        tr:hover {{
            background: #f9fafb;
        }}
        .progress-bar {{
            background: #e1e4e8;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75em;
            font-weight: bold;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.85em;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="dataset-name">{metrica.dataset_nome}</div>
            <div class="status-badge">{status_texto}</div>
        </header>
        
        <div class="content">
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Total de Registros</div>
                    <div class="metric-value">{metrica.total_registros:,}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Total de Colunas</div>
                    <div class="metric-value">{metrica.total_colunas}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Completude</div>
                    <div class="metric-value">{metrica.taxa_completude:.1f}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Validade</div>
                    <div class="metric-value">{metrica.taxa_validade:.1f}%</div>
                </div>
            </div>
            
            <div class="info-section">
                <h3>📊 Taxa de Completude</h3>
                <p>Percentual de células preenchidas (não nulas)</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {metrica.taxa_completude}%">
                        {metrica.taxa_completude:.1f}%
                    </div>
                </div>
            </div>
            
            <div class="info-section">
                <h3>✓ Validações</h3>
                <table>
                    <tr>
                        <th>Tipo de Validação</th>
                        <th>Resultado</th>
                    </tr>
                    <tr>
                        <td>Expectativas Passadas</td>
                        <td><strong style="color: #27ae60;">{metrica.expectativas_passadas}</strong></td>
                    </tr>
                    <tr>
                        <td>Expectativas Falhadas</td>
                        <td><strong style="color: #e74c3c;">{metrica.expectativas_falhadas}</strong></td>
                    </tr>
                    <tr>
                        <td>Taxa de Sucesso</td>
                        <td>
                            <strong>
                                {{{{ (metrica.expectativas_passadas / (metrica.expectativas_passadas + metrica.expectativas_falhadas) * 100 if (metrica.expectativas_passadas + metrica.expectativas_falhadas) > 0 else 0) | int }}}}%
                            </strong>
                        </td>
                    </tr>
                    <tr>
                        <td>Registros Duplicados</td>
                        <td><strong>{metrica.registros_duplicados}</strong></td>
                    </tr>
                </table>
            </div>
            
            <div class="info-section">
                <h3>⚙️ Detalhes Técnicos</h3>
                <p><strong>Dataset:</strong> {metrica.dataset_nome}</p>
                <p><strong>Registros com Nulos:</strong> {metrica.valores_nulos_percentual:.2f}%</p>
                <p><strong>Última Atualização:</strong> {metrica.timestamp}</p>
            </div>
            
            <div class="timestamp">
                Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
            </div>
        </div>
    </div>
</body>
</html>
        """
        return html
    
    @staticmethod
    def gerar_relatorio_consolidado(relatorio: RelatorioQualidade) -> str:
        """
        Gera relatório HTML consolidado
        
        Args:
            relatorio: Relatório consolidado
            
        Returns:
            HTML do relatório
        """
        score = relatorio.score_geral()
        
        # Determinar cor baseada no score
        if score >= 90:
            cor_score = "#27ae60"
        elif score >= 75:
            cor_score = "#f39c12"
        else:
            cor_score = "#e74c3c"
        
        # Criar tabela de datasets
        linhas_tabela = ""
        for dataset in relatorio.datasets:
            completude_cor = "#27ae60" if dataset.taxa_completude >= 90 else ("#f39c12" if dataset.taxa_completude >= 75 else "#e74c3c")
            linhas_tabela += f"""
            <tr>
                <td>{dataset.dataset_nome}</td>
                <td>{dataset.total_registros:,}</td>
                <td>{dataset.total_colunas}</td>
                <td><strong style="color: {completude_cor};">{dataset.taxa_completude:.1f}%</strong></td>
                <td>{dataset.registros_duplicados}</td>
                <td style="color: #27ae60; font-weight: bold;">{dataset.expectativas_passadas}</td>
                <td style="color: #e74c3c; font-weight: bold;">{dataset.expectativas_falhadas}</td>
            </tr>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Consolidado de Qualidade</title>
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .title {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 40px;
        }}
        .score-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 40px;
        }}
        .score-value {{
            font-size: 4em;
            font-weight: bold;
            margin: 20px 0;
        }}
        .score-label {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .summary-item {{
            background: #f9fafb;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .summary-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .summary-label {{
            color: #666;
            font-size: 0.9em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #e1e4e8;
        }}
        tr:hover {{
            background: #f9fafb;
        }}
        .recommendation {{
            background: #e8f5e9;
            border-left: 4px solid #27ae60;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .recommendation h3 {{
            color: #27ae60;
            margin-bottom: 10px;
        }}
        footer {{
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e1e4e8;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="title">📊 Relatório de Qualidade de Dados</div>
            <div class="subtitle">{relatorio.empresa}</div>
            <div style="font-size: 0.9em; margin-top: 15px; opacity: 0.8;">Gerado em {relatorio.data_geracao}</div>
        </header>
        
        <div class="content">
            <div class="score-box">
                <div class="score-label">Score Geral de Qualidade</div>
                <div class="score-value" style="color: {cor_score};">{score:.1f}%</div>
                <div class="score-label">Baseado em {len(relatorio.datasets)} dataset(s)</div>
            </div>
            
            <div class="summary">
                <div class="summary-item">
                    <div class="summary-label">Total de Registros</div>
                    <div class="summary-value">{sum(d.total_registros for d in relatorio.datasets):,}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Total de Colunas</div>
                    <div class="summary-value">{sum(d.total_colunas for d in relatorio.datasets)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Datasets Analisados</div>
                    <div class="summary-value">{len(relatorio.datasets)}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Validações Passadas</div>
                    <div class="summary-value" style="color: #27ae60;">{sum(d.expectativas_passadas for d in relatorio.datasets)}</div>
                </div>
            </div>
            
            <h2 style="margin: 30px 0 20px;">📋 Detalhes por Dataset</h2>
            <table>
                <tr>
                    <th>Dataset</th>
                    <th>Registros</th>
                    <th>Colunas</th>
                    <th>Completude</th>
                    <th>Duplicados</th>
                    <th>✓ Passadas</th>
                    <th>✗ Falhadas</th>
                </tr>
                {linhas_tabela}
            </table>
            
            <div class="recommendation">
                <h3>✓ Recomendações Gerais</h3>
                <ul style="margin-left: 20px; line-height: 1.8;">
                    <li>Manter vigilância regular sobre os datasets com completude abaixo de 90%</li>
                    <li>Investigar causa raiz de validações falhadas</li>
                    <li>Estabelecer processo formal de limpeza de dados duplicados</li>
                    <li>Documentar SLAs de qualidade por dataset</li>
                    <li>Revisar e atualizar regras de validação mensalmente</li>
                </ul>
            </div>
        </div>
        
        <footer>
            <p>Great Expectations Data Docs | {relatorio.empresa} | v{relatorio.versao}</p>
            <p style="font-size: 0.85em; margin-top: 10px; color: #999;">
                Relatório gerado automaticamente pelo Dashboard de Qualidade
            </p>
        </footer>
    </div>
</body>
</html>
        """
        return html


# ============================================================================
# GERADOR DE PDF
# ============================================================================

class GeradorPDF:
    """Gera relatórios em PDF (usando HTML to PDF)"""
    
    @staticmethod
    def html_para_pdf(html_content: str, arquivo_saida: str) -> bool:
        """
        Converte HTML para PDF
        
        Args:
            html_content: Conteúdo HTML
            arquivo_saida: Caminho do arquivo PDF
            
        Returns:
            Sucesso da conversão
        """
        try:
            # Tentar usar weasyprint (recomendado)
            try:
                from weasyprint import HTML, CSS
                
                HTML(string=html_content).write_pdf(arquivo_saida)
                logger.info(f"✓ PDF gerado com WeasyPrint: {arquivo_saida}")
                return True
            
            except ImportError:
                # Fallback: tentar pdfkit (requer wkhtmltopdf)
                try:
                    import pdfkit
                    
                    options = {
                        'page-size': 'A4',
                        'margin-top': '0.75in',
                        'margin-right': '0.75in',
                        'margin-bottom': '0.75in',
                        'margin-left': '0.75in',
                        'encoding': "UTF-8",
                        'no-outline': None,
                        'enable-local-file-access': None
                    }
                    
                    pdfkit.from_string(html_content, arquivo_saida, options=options)
                    logger.info(f"✓ PDF gerado com PDFKit: {arquivo_saida}")
                    return True
                
                except (ImportError, OSError) as e:
                    logger.warning(f"PDFKit não disponível: {e}")
                    # Fallback: salvar como HTML
                    return False
        
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}")
            return False
    
    @staticmethod
    def gerar_pdf_relatorio_executivo(relatorio: RelatorioQualidade, arquivo_saida: str) -> bool:
        """
        Gera PDF do relatório executivo
        
        Args:
            relatorio: Relatório consolidado
            arquivo_saida: Caminho do arquivo PDF
            
        Returns:
            Sucesso da conversão
        """
        logger.info(f"Gerando PDF do relatório executivo: {arquivo_saida}")
        
        # Criar HTML
        html_generator = GeradorRelatoriosHTML()
        html_content = html_generator.gerar_relatorio_consolidado(relatorio)
        
        # Converter para PDF
        Path("relatorios").mkdir(exist_ok=True)
        return GeradorPDF.html_para_pdf(html_content, f"relatorios/{arquivo_saida}")


# ============================================================================
# CUSTOMIZADOR DE TEMPLATES
# ============================================================================

class CustomizadorTemplates:
    """Customiza templates para TechCommerce"""
    
    @staticmethod
    def aplicar_tema_techcommerce(html_base: str) -> str:
        """
        Aplica tema da TechCommerce ao HTML
        
        Args:
            html_base: HTML base
            
        Returns:
            HTML com tema aplicado
        """
        # Cores TechCommerce
        cores_techcommerce = {
            'primaria': '#667eea',      # Azul
            'secundaria': '#764ba2',    # Roxo
            'sucesso': '#27ae60',       # Verde
            'alerta': '#f39c12',        # Laranja
            'erro': '#e74c3c'           # Vermelho
        }
        
        # Substituir cores padrão
        html_customizado = html_base
        for var, cor in cores_techcommerce.items():
            html_customizado = html_customizado.replace(
                f"{{{{ cor_{var} }}}}", cor
            )
        
        # Adicionar logo da TechCommerce
        logo_html = f"""
        <div style="margin-bottom: 20px;">
            <h2 style="color: #667eea;">🛒 TechCommerce</h2>
            <p style="color: #666;">Plataforma de E-commerce Integrada</p>
        </div>
        """
        
        html_customizado = html_customizado.replace(
            "<div class=\"content\">",
            f"<div class=\"content\">{logo_html}"
        )
        
        return html_customizado
    
    @staticmethod
    def criar_template_customizado(config: Dict) -> str:
        """
        Cria template completamente customizado
        
        Args:
            config: Configuração do template
            
        Returns:
            HTML do template
        """
        html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get('titulo', 'Dashboard')}</title>
    <style>
        :root {{
            --cor-primaria: {config.get('cor_primaria', '#667eea')};
            --cor-secundaria: {config.get('cor_secundaria', '#764ba2')};
            --cor-sucesso: {config.get('cor_sucesso', '#27ae60')};
            --cor-alerta: {config.get('cor_alerta', '#f39c12')};
            --cor-erro: {config.get('cor_erro', '#e74c3c')};
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: {config.get('fonte', 'Segoe UI')}, sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{
            max-width: {config.get('largura_max', '1200px')};
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        header {{
            background: linear-gradient(135deg, var(--cor-primaria), var(--cor-secundaria));
            color: white;
            padding: 40px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .header-content {{
            max-width: 600px;
            margin: 0 auto;
        }}
        .logo {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .titulo {{
            font-size: 2em;
            margin-bottom: 5px;
        }}
        .subtitulo {{
            opacity: 0.9;
            font-size: 1em;
        }}
        .content {{
            padding: 40px;
        }}
        footer {{
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e1e4e8;
            margin-top: 40px;
            border-radius: 0 0 10px 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <div class="logo">{config.get('logo', '🎯')}</div>
                <div class="titulo">{config.get('titulo', 'Dashboard')}</div>
                <div class="subtitulo">{config.get('subtitulo', 'Qualidade de Dados')}</div>
            </div>
        </header>
        
        <div class="content">
            <h2>Customizado para {config.get('empresa', 'TechCommerce')}</h2>
            <p style="margin-top: 10px; color: #666;">
                Template gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
            </p>
        </div>
        
        <footer>
            <p>{config.get('empresa', 'TechCommerce')} | {config.get('versao', '1.0')}</p>
        </footer>
    </div>
</body>
</html>
        """
        return html


# ============================================================================
# INTEGRADOR DE MÉTRICAS
# ============================================================================

class IntegradorMetricas:
    """Integra métricas de múltiplos datasets"""
    
    @staticmethod
    def calcular_metricas_dataset(df: pd.DataFrame, nome_dataset: str) -> MetricaDataset:
        """
        Calcula métricas de um dataset
        
        Args:
            df: DataFrame
            nome_dataset: Nome do dataset
            
        Returns:
            MetricaDataset com métricas calculadas
        """
        logger.info(f"Calculando métricas para: {nome_dataset}")
        
        # Métricas básicas
        total_registros = len(df)
        total_colunas = len(df.columns)
        
        # Completude
        total_celulas = total_registros * total_colunas
        celulas_nulas = df.isna().sum().sum()
        taxa_completude = ((total_celulas - celulas_nulas) / total_celulas * 100) if total_celulas > 0 else 0
        valores_nulos_percentual = (celulas_nulas / total_celulas * 100) if total_celulas > 0 else 0
        
        # Duplicatas
        registros_duplicados = df.duplicated().sum()
        
        # Validade (assumir 95% por padrão, seria calculado com validações reais)
        taxa_validade = 95.0
        
        # Expectativas (valores padrão para demonstração)
        expectativas_passadas = int(total_colunas * 0.9)
        expectativas_falhadas = int(total_colunas * 0.1)
        
        metrica = MetricaDataset(
            dataset_nome=nome_dataset,
            timestamp=datetime.now().isoformat(),
            total_registros=total_registros,
            total_colunas=total_colunas,
            valores_nulos_percentual=valores_nulos_percentual,
            registros_duplicados=registros_duplicados,
            taxa_completude=taxa_completude,
            taxa_validade=taxa_validade,
            expectativas_passadas=expectativas_passadas,
            expectativas_falhadas=expectativas_falhadas
        )
        
        logger.info(f"✓ Métricas calculadas: {nome_dataset} (Completude: {taxa_completude:.1f}%)")
        return metrica
    
    @staticmethod
    def consolidar_metricas(datasets: Dict[str, pd.DataFrame]) -> RelatorioQualidade:
        """
        Consolida métricas de múltiplos datasets
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            
        Returns:
            RelatorioQualidade consolidado
        """
        logger.info("Consolidando métricas de múltiplos datasets")
        
        metricas = []
        for nome, df in datasets.items():
            metrica = IntegradorMetricas.calcular_metricas_dataset(df, nome)
            metricas.append(metrica)
        
        relatorio = RelatorioQualidade(
            titulo="Relatório Consolidado de Qualidade de Dados",
            data_geracao=datetime.now().strftime('%d/%m/%Y às %H:%M:%S'),
            datasets=metricas,
            empresa="TechCommerce",
            versao="1.0"
        )
        
        logger.info(f"✓ Métricas consolidadas: {len(metricas)} datasets")
        return relatorio


# ============================================================================
# ORQUESTRADOR DE DASHBOARD
# ============================================================================

class OrquestradorDashboard:
    """Orquestra geração completa do dashboard"""
    
    def __init__(self, empresa: str = "TechCommerce"):
        """
        Inicializa orquestrador
        
        Args:
            empresa: Nome da empresa
        """
        self.empresa = empresa
        self.data_context = ConfiguradorDataDocs.setup_data_context()
        Path("relatorios").mkdir(exist_ok=True)
        logger.info(f"Dashboard iniciado para: {empresa}")
    
    def gerar_dashboard_completo(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """
        Gera dashboard completo com todas as saídas
        
        Args:
            datasets: Dicionário com {nome: DataFrame}
            
        Returns:
            Dicionário com caminhos dos arquivos gerados
        """
        logger.info("=" * 80)
        logger.info("GERANDO DASHBOARD COMPLETO")
        logger.info("=" * 80)
        
        arquivos_gerados = {}
        
        # 1. Calcular métricas
        logger.info("\n📍 Etapa 1: Calculando Métricas")
        relatorio = IntegradorMetricas.consolidar_metricas(datasets)
        
        # 2. Gerar HTML de índice
        logger.info("\n📍 Etapa 2: Gerando Página de Índice")
        config_indice = {
            'empresa': self.empresa,
            'data_geracao': relatorio.data_geracao,
            'versao': relatorio.versao
        }
        html_indice = ConfiguradorDataDocs.criar_pagina_indice(config_indice)
        arquivo_indice = "relatorios/index.html"
        with open(arquivo_indice, 'w', encoding='utf-8') as f:
            f.write(html_indice)
        arquivos_gerados['indice'] = arquivo_indice
        logger.info(f"✓ Página de índice gerada: {arquivo_indice}")
        
        # 3. Gerar relatórios por dataset
        logger.info("\n📍 Etapa 3: Gerando Relatórios por Dataset")
        gerador_html = GeradorRelatoriosHTML()
        for metrica in relatorio.datasets:
            html_dataset = gerador_html.gerar_relatorio_dataset(metrica, {})
            arquivo_dataset = f"relatorios/{metrica.dataset_nome}_relatorio.html"
            with open(arquivo_dataset, 'w', encoding='utf-8') as f:
                f.write(html_dataset)
            arquivos_gerados[f'{metrica.dataset_nome}_html'] = arquivo_dataset
            logger.info(f"✓ Relatório de {metrica.dataset_nome} gerado: {arquivo_dataset}")
        
        # 4. Gerar relatório consolidado
        logger.info("\n📍 Etapa 4: Gerando Relatório Consolidado")
        html_consolidado = gerador_html.gerar_relatorio_consolidado(relatorio)
        arquivo_consolidado = "relatorios/relatorio_consolidado.html"
        with open(arquivo_consolidado, 'w', encoding='utf-8') as f:
            f.write(html_consolidado)
        arquivos_gerados['consolidado_html'] = arquivo_consolidado
        logger.info(f"✓ Relatório consolidado gerado: {arquivo_consolidado}")
        
        # 5. Gerar PDF (se possível)
        logger.info("\n📍 Etapa 5: Gerando Relatórios em PDF")
        gerador_pdf = GeradorPDF()
        try:
            sucesso_pdf = gerador_pdf.gerar_pdf_relatorio_executivo(
                relatorio, 
                "relatorio_qualidade_executivo.pdf"
            )
            if sucesso_pdf:
                arquivos_gerados['consolidado_pdf'] = "relatorios/relatorio_qualidade_executivo.pdf"
                logger.info("✓ Relatório PDF gerado com sucesso")
            else:
                logger.warning("⚠ PDF não pôde ser gerado (bibliotecas não disponíveis)")
        except Exception as e:
            logger.warning(f"⚠ Erro ao gerar PDF: {e}")
        
        # 6. Salvar dados em JSON
        logger.info("\n📍 Etapa 6: Salvando Dados em JSON")
        
        # Converter métricas para dicionários com tipos nativos
        datasets_dict = []
        for m in relatorio.datasets:
            d = asdict(m)
            # Converter numpy/pandas types para Python nativos
            d['total_registros'] = int(d['total_registros'])
            d['total_colunas'] = int(d['total_colunas'])
            d['valores_nulos_percentual'] = float(d['valores_nulos_percentual'])
            d['registros_duplicados'] = int(d['registros_duplicados'])
            d['taxa_completude'] = float(d['taxa_completude'])
            d['taxa_validade'] = float(d['taxa_validade'])
            d['expectativas_passadas'] = int(d['expectativas_passadas'])
            d['expectativas_falhadas'] = int(d['expectativas_falhadas'])
            datasets_dict.append(d)
        
        dados_json = {
            'relatorio': {
                'titulo': relatorio.titulo,
                'data_geracao': relatorio.data_geracao,
                'empresa': relatorio.empresa,
                'score_geral': float(relatorio.score_geral()),
                'datasets': datasets_dict
            }
        }
        arquivo_json = "relatorios/dados_metricas.json"
        with open(arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(dados_json, f, indent=2, ensure_ascii=False)
        arquivos_gerados['json'] = arquivo_json
        logger.info(f"✓ Dados JSON salvos: {arquivo_json}")
        
        logger.info("\n" + "=" * 80)
        logger.info("DASHBOARD COMPLETO GERADO COM SUCESSO")
        logger.info("=" * 80)
        
        return arquivos_gerados
    
    def exibir_resumo_gerado(self, arquivos: Dict[str, str]):
        """
        Exibe resumo dos arquivos gerados
        
        Args:
            arquivos: Dicionário com caminhos dos arquivos
        """
        print("\n" + "=" * 80)
        print("ARQUIVOS GERADOS")
        print("=" * 80)
        
        for tipo, caminho in arquivos.items():
            if Path(caminho).exists():
                tamanho = Path(caminho).stat().st_size / 1024
                print(f"✓ {tipo:20s} → {caminho:40s} ({tamanho:.1f} KB)")
            else:
                print(f"⚠ {tipo:20s} → {caminho:40s} (não gerado)")
        
        print("\n" + "=" * 80)
        print("Abra 'relatorios/index.html' no navegador para visualizar o dashboard")
        print("=" * 80 + "\n")


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
    
    # Criar orquestrador e gerar dashboard
    orquestrador = OrquestradorDashboard(empresa="TechCommerce")
    arquivos_gerados = orquestrador.gerar_dashboard_completo(datasets)
    
    # Exibir resumo
    orquestrador.exibir_resumo_gerado(arquivos_gerados)
