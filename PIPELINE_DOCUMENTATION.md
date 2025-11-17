# Pipeline de Ingestão de Dados - Documentação

## 📋 Resumo Executivo

O `pipeline_ingestao.py` implementa um sistema robusto e auditável de carregamento e validação de dados de múltiplas fontes com schema validation rigoroso.

---

## ✅ Funcionalidades Implementadas

### 1. **Carregamento de Múltiplas Fontes**
- ✓ CSV com suporte a múltiplas codificações (UTF-8, Latin-1, ISO-8859-1, CP1252)
- ✓ JSON
- ✓ Parquet
- ✓ Excel (XLSX/XLS)
- ✓ Tratamento automático de erros de formato
- ✓ Inferência automática de tipo de arquivo pela extensão

**Classe:** `CarregadorDados`

```python
carregador = CarregadorDados(logger)
df = carregador.carregar("dados.csv")  # Inferência automática de tipo
df = carregador.carregar("dados.json", tipo=TipoFonte.JSON)  # Tipo explícito
```

---

### 2. **Schema Validation Rigoroso**

#### Definição de Schemas
Cada coluna possui validações específicas:
- Tipo de dado (int, float, string, datetime, bool)
- Obrigatoriedade
- Intervalo numérico (min/max)
- Lista de valores válidos
- Padrão regex
- Tamanho máximo de string

**Classes:** `SchemaColuna`, `Schema`

```python
schema = Schema(
    nome_dataset="produtos",
    chave_primaria=["id_produto"],
    colunas=[
        SchemaColuna("id_produto", "int", obrigatorio=True),
        SchemaColuna("preco", "float", obrigatorio=True, intervalo_min=0.01),
        SchemaColuna("categoria", "string", obrigatorio=True,
                    valores_validos=['Eletrônicos', 'Moda', ...]),
    ]
)
```

#### Validações Implementadas

**`ValidadorSchema.validar_dataframe(df)`** executa:

1. **Validação de Estrutura**
   - Colunas obrigatórias presentes
   - Detecta colunas extras

2. **Validação de Tipos**
   - Verifica tipos de dados
   - Tenta conversões automáticas
   - Registra erros de tipo

3. **Validação de Valores**
   - Intervalo numérico (min/max)
   - Valores em conjunto permitido
   - Padrões regex
   - Tamanho de strings

4. **Validação de Completude**
   - Campos obrigatórios não nulos
   - Conta de valores nulos

5. **Validação de Chave Primária**
   - Unicidade (sem duplicatas)
   - Sem valores nulos

**Retorno:**
```python
sucesso, relatorio = validador.validar_dataframe(df)

# relatorio contém:
{
    "dataset": "clientes",
    "sucesso": true/false,
    "total_erros": 5,
    "total_avisos": 2,
    "erros": [...],
    "validacoes": {
        "estrutura": {...},
        "tipos": {...},
        "valores": {...},
        "completude": {...},
        "chave_primaria": {...}
    }
}
```

---

### 3. **Schemas Pré-Definidos**

Três schemas prontos para uso:

#### **SCHEMA_CLIENTES**
- Campos: id_cliente, nome, email, telefone, data_nascimento, cidade, estado, data_cadastro
- Validações: Email regex, telefone 11 dígitos, estado em UFs válidas

#### **SCHEMA_PRODUTOS**
- Campos: id_produto, nome_produto, categoria, preco, estoque, data_criacao, ativo
- Validações: Preço > 0, estoque >= 0, categoria em lista válida

#### **SCHEMA_VENDAS**
- Campos: id_venda, id_cliente, id_produto, quantidade, valor_unitario, valor_total, data_venda, status
- Validações: Quantidade >= 1, status em conjunto válido

---

### 4. **Testes de Schema Automatizados**

O `ValidadorSchema` fornece testes completos:

```python
validador = ValidadorSchema(SCHEMA_CLIENTES, logger)
sucesso, relatorio = validador.validar_dataframe(df)

# Acesso a detalhes específicos:
print(relatorio["validacoes"]["tipos"]["status"])  # ok/erro
print(relatorio["erros"])  # Lista de erros
print(relatorio["avisos"])  # Lista de avisos
```

---

### 5. **Logging e Auditoria**

#### Sistema de Logging Centralizado
- **3 handlers simultâneos:**
  1. Arquivo de log geral: `logs/pipeline_YYYYMMDD.log`
  2. Arquivo de auditoria: `logs/auditoria_YYYYMMDD.log`
  3. Console (INFO e superior)

**Classe:** `LoggerConfig`

```python
logger = LoggerConfig.setup_logging(log_dir="logs")
logger.info("Mensagem informativa")
logger.error("Mensagem de erro")
logger.warning("Aviso")
```

#### Auditoria Detalhada
Cada operação registra:
- ✓ Timestamp
- ✓ Tipo de operação
- ✓ Arquivo/fonte de dados
- ✓ Número de linhas e colunas
- ✓ Hash MD5 dos dados (para rastreabilidade)
- ✓ Status (sucesso/erro)
- ✓ Detalhes de validação

**Exemplo de log:**
```
2025-11-15 05:32:24 - DataPipeline - INFO - Iniciando carregamento: clientes.csv (tipo: csv)
2025-11-15 05:32:24 - DataPipeline - INFO - ✓ Carregamento bem-sucedido: 16 linhas, 8 colunas
2025-11-15 05:32:24 - DataPipeline - INFO -   Hash dos dados: 8161560748514b75
2025-11-15 05:32:24 - DataPipeline - WARNING - ✗ Validação com erros para clientes
2025-11-15 05:32:24 - DataPipeline - ERROR -   - Coluna 'email': 4 valores não correspondem ao padrão
```

---

### 6. **Tratamento de Erros**

#### Erros de Formato de Arquivo
- ✓ Arquivo não encontrado
- ✓ CSV com múltiplas codificações (fallback automático)
- ✓ JSON inválido
- ✓ Excel corrompido
- ✓ Parquet inválido

#### Erros de Dados
- ✓ Valores nulos obrigatórios
- ✓ Tipos de dados incorretos
- ✓ Valores fora de intervalo
- ✓ Padrões regex não correspondentes
- ✓ Duplicatas em chave primária
- ✓ Tamanho de string excedido

Todos os erros são:
- Registrados em log
- Inclusos no relatório de validação
- Não causam crash do pipeline (graceful degradation)

---

### 7. **Pipeline de Ingestão Orquestrado**

**Classe:** `PipelineIngestao`

```python
# Inicializar
pipeline = PipelineIngestao()

# Processar dataset individual
df, relatorio = pipeline.processar_dataset("clientes.csv", SCHEMA_CLIENTES)

# Processar múltiplas fontes
sources = {
    "clientes": ("clientes.csv", SCHEMA_CLIENTES),
    "produtos": ("produtos.csv", SCHEMA_PRODUTOS),
    "vendas": ("vendas.csv", SCHEMA_VENDAS),
}
resultados = pipeline.processar_multiplas_fontes(sources)

# Gerar relatório consolidado
relatorio_final = pipeline.gerar_relatorio_final()

# Salvar relatório em JSON
pipeline.salvar_relatorio("relatorio_auditoria.json")
```

**Fluxo:**
1. Carrega arquivo (com tratamento de erros)
2. Valida contra schema
3. Registra resultado em log
4. Retorna DataFrame (se válido) e relatório detalhado

---

## 📊 Saídas Geradas

### Arquivos de Log
```
logs/
├── pipeline_20251115.log        # Log detalhado de todas as operações
├── auditoria_20251115.log       # Log de auditoria
└── relatorio_auditoria.json     # Relatório estruturado em JSON
```

### Estrutura do Relatório JSON
```json
{
  "timestamp": "2025-11-15T05:32:24.085739",
  "total_datasets": 3,
  "datasets_sucesso": 1,
  "datasets_erro": 2,
  "detalhes": [
    {
      "dataset": "clientes",
      "carregamento": "sucesso",
      "linhas_totais": 16,
      "colunas_esperadas": 8,
      "sucesso": false,
      "total_erros": 5,
      "validacoes": {
        "estrutura": {"status": "ok"},
        "tipos": {"status": "ok"},
        "valores": {"status": "erro"},
        "completude": {"status": "erro"},
        "chave_primaria": {"status": "erro"}
      },
      "erros": [
        "Coluna 'email': 4 valores não correspondem ao padrão",
        "Coluna 'nome': 2 valores nulos (obrigatória)",
        "Chave primária: 1 registros duplicados"
      ]
    }
  ]
}
```

---

## 🚀 Exemplo de Uso Completo

```python
from pipeline_ingestao import (
    PipelineIngestao, 
    SCHEMA_CLIENTES, 
    SCHEMA_PRODUTOS, 
    SCHEMA_VENDAS,
    LoggerConfig
)
from pathlib import Path

# 1. Configurar logging
logger = LoggerConfig.setup_logging("logs")

# 2. Criar pipeline
pipeline = PipelineIngestao(logger)

# 3. Definir fontes
datasets_path = Path("notebooks/datasets")
sources = {
    "clientes": (str(datasets_path / "clientes.csv"), SCHEMA_CLIENTES),
    "produtos": (str(datasets_path / "produtos.csv"), SCHEMA_PRODUTOS),
    "vendas": (str(datasets_path / "vendas.csv"), SCHEMA_VENDAS),
}

# 4. Processar
resultados = pipeline.processar_multiplas_fontes(sources)

# 5. Análise de resultados
for nome, (df, relatorio) in resultados.items():
    if relatorio["sucesso"]:
        print(f"✓ {nome}: {len(df)} linhas carregadas com sucesso")
    else:
        print(f"✗ {nome}: {relatorio['total_erros']} erros de validação")
        for erro in relatorio["erros"]:
            print(f"  - {erro}")

# 6. Gerar relatório final
pipeline.salvar_relatorio("logs/relatorio_final.json")
```

---

## 📈 Métricas de Qualidade

O sistema fornece:
- ✓ Contagem de linhas e colunas
- ✓ Taxa de completude (valores nulos)
- ✓ Análise de tipos de dados
- ✓ Conformidade com schema
- ✓ Detecção de duplicatas
- ✓ Rastreabilidade via hash de dados

---

## 🔍 Extensibilidade

Para adicionar novos datasets:

```python
from pipeline_ingestao import Schema, SchemaColuna

MEU_SCHEMA = Schema(
    nome_dataset="meu_dataset",
    chave_primaria=["id"],
    colunas=[
        SchemaColuna("id", "int", obrigatorio=True),
        SchemaColuna("nome", "string", obrigatorio=True),
        # ... mais colunas
    ]
)

# Usar no pipeline
df, relatorio = pipeline.processar_dataset("dados.csv", MEU_SCHEMA)
```

---

## ⚠️ Notas Importantes

1. **Ordem de Validação:** Estrutura → Tipos → Valores → Completude → Chave Primária
2. **Conversão Automática:** Tipos são convertidos automaticamente quando possível
3. **Graceful Degradation:** Erros de validação não impedem o retorno do DataFrame (verificar `relatorio["sucesso"]`)
4. **Hashes:** Calculados para auditoria de integridade de dados
5. **Timezone:** Timestamps em UTC

---

## 📝 Alterações Futuras Recomendadas

- [ ] Suporte a banco de dados (PostgreSQL, MySQL)
- [ ] Validação de integridade referencial cruzada
- [ ] Detecção automática de outliers
- [ ] Limpeza automática de dados (trimming, padronização)
- [ ] Cache de validações
- [ ] API REST para pipeline
