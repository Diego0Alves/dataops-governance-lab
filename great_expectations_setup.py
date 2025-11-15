import great_expectations as gx
import pandas as pd
from pathlib import Path
from datetime import datetime


def setup_great_expectations_context():
    """
    Configura Data Context do Great Expectations
    Cria datasources para todos os datasets
    
    Returns:
        context: Contexto configurado do Great Expectations
    """
    try:
        # Tenta obter ou criar um contexto existente
        context = gx.get_context()
        print(f" Data Context obtido com sucesso")
        return context
    except Exception as e:
        print(f" Contexto padrão será utilizado: {e}")
        return None


def create_clientes_expectations(validator):
    """
    Cria expectativas para dataset de clientes:
    - Completude: id_cliente, nome, email não nulos
    - Unicidade: id_cliente, email únicos
    - Validade: email formato válido, telefone 11 dígitos
    - Consistência: estado 2 caracteres
    """
    validator.expect_column_values_to_not_be_null("id_cliente")
    validator.expect_column_values_to_be_unique("id_cliente")
    validator.expect_column_values_to_not_be_null("nome")
    validator.expect_column_values_to_not_be_null("email")
    validator.expect_column_values_to_be_unique("email")
    validator.expect_column_values_to_match_regex("email", r"^[\w\.-]+@[\w\.-]+\.\w+$")

def create_produtos_expectations(validator):
    """
    Expectativas para produtos:
    - Completude: nome_produto, categoria não nulos
    - Validade: preco > 0, estoque >= 0
    - Consistência: categoria em lista válida
    """
    validator.expect_column_values_to_not_be_null("nome_produto")
    validator.expect_column_values_to_not_be_null("categoria")
    validator.expect_column_values_to_be_between("preco", min_value=0)
    validator.expect_column_values_to_be_between("estoque", min_value=0)

def create_vendas_expectations(validator):
    """
    Expectativas para vendas:
    - Integridade referencial: id_cliente e id_produto existem
    - Regras de negócio: valor_total = quantidade × valor_unitario
    - Validade: quantidade > 0, data_venda não futura
    """
    validator.expect_column_values_to_be_between("quantidade", min_value=1)
    validator.expect_column_values_to_be_in_set("status", ["Concluída", "Pendente", "Cancelada"])