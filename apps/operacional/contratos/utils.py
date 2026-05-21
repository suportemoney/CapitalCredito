"""
Utilitários para o app contratos
"""
import csv
import os
from django.conf import settings

def get_campos_comuns():
    """
    Retorna lista de campos comuns baseados no CSV
    Por enquanto retorna uma lista estática baseada no CSV
    """
    campos_comuns = [
        # dados_pessoais
        {'category': 'dados_pessoais', 'label': 'nome', 'type': 'TEXT', 'required': True},
        {'category': 'dados_pessoais', 'label': 'sexo', 'type': 'SELECT', 'choices': ['feminino', 'masculino'], 'required': True},
        {'category': 'dados_pessoais', 'label': 'data_de_nascimento', 'type': 'DATE', 'required': True},
        {'category': 'dados_pessoais', 'label': 'naturalidade', 'type': 'TEXT', 'required': False},
        {'category': 'dados_pessoais', 'label': 'pais_origem', 'type': 'SELECT', 'required': False},
        {'category': 'dados_pessoais', 'label': 'cpf', 'type': 'TEXT', 'required': True},
        {'category': 'dados_pessoais', 'label': 'rg_numero', 'type': 'TEXT', 'required': True},
        {'category': 'dados_pessoais', 'label': 'rg_orgao_emissor', 'type': 'TEXT', 'required': True},
        {'category': 'dados_pessoais', 'label': 'rg_uf_emissao', 'type': 'SELECT', 'required': True},
        {'category': 'dados_pessoais', 'label': 'rg_data_emissao', 'type': 'DATE', 'required': True},
        {'category': 'dados_pessoais', 'label': 'nome_do_pai', 'type': 'TEXT', 'required': False},
        {'category': 'dados_pessoais', 'label': 'nome_da_mae', 'type': 'TEXT', 'required': False},
        # contato
        {'category': 'contato', 'label': 'contato', 'type': 'TEL', 'required': True},
        {'category': 'contato', 'label': 'email', 'type': 'EMAIL', 'required': True},
        # endereco
        {'category': 'endereco', 'label': 'cep', 'type': 'TEXT', 'required': True},
        {'category': 'endereco', 'label': 'numero_endereco', 'type': 'TEXT', 'required': True},
        # financeiro_pessoal
        {'category': 'financeiro_pessoal', 'label': 'valor_salario', 'type': 'NUMBER', 'required': False},
        # bancario
        {'category': 'bancario', 'label': 'tipo_de_pagamento', 'type': 'SELECT', 'required': True},
        {'category': 'bancario', 'label': 'tipo_de_conta', 'type': 'SELECT', 'required': False},
        {'category': 'bancario', 'label': 'banco', 'type': 'TEXT', 'required': False},
        {'category': 'bancario', 'label': 'agencia', 'type': 'TEXT', 'required': False},
        {'category': 'bancario', 'label': 'dv_agencia', 'type': 'TEXT', 'required': False},
        {'category': 'bancario', 'label': 'conta', 'type': 'TEXT', 'required': False},
        {'category': 'bancario', 'label': 'dv_conta', 'type': 'TEXT', 'required': False},
        {'category': 'bancario', 'label': 'incluir_seguro', 'type': 'SELECT', 'required': False},
        # operacao
        {'category': 'operacao', 'label': 'tarifa', 'type': 'NUMBER', 'required': False},
        {'category': 'operacao', 'label': 'valor_negociado', 'type': 'NUMBER', 'required': False},
        {'category': 'operacao', 'label': 'coeficiente', 'type': 'NUMBER', 'required': False},
        {'category': 'operacao', 'label': 'prazo', 'type': 'NUMBER', 'required': True},
        {'category': 'operacao', 'label': 'valor_parcela', 'type': 'NUMBER', 'required': False},
        {'category': 'operacao', 'label': 'valor_operacao', 'type': 'NUMBER', 'required': False},
        {'category': 'operacao', 'label': 'coeficiente_prazo', 'type': 'SELECT', 'required': True},
        # dados_representante
        {'category': 'dados_representante', 'label': 'nome_representante', 'type': 'TEXT', 'required': False},
        {'category': 'dados_representante', 'label': 'cpf_representante', 'type': 'TEXT', 'required': False},
        # outras_informacoes
        {'category': 'outras_informacoes', 'label': 'observacoes', 'type': 'TEXTAREA', 'required': False},
    ]
    return campos_comuns
