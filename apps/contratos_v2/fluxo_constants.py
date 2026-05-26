# -*- coding: utf-8 -*-
"""Constantes do fluxo operacional de propostas/contratos (nexos / plano)."""
import os

# Tag exibida no container Propostas (consulta_cliente)
class TagPropostaContainer:
    AGUARDANDO = 'AGUARDANDO'
    SUCESSO = 'SUCESSO'
    INELEGIVEL = 'INELEGIVEL'
    CHOICES = (
        (AGUARDANDO, 'Aguardando'),
        (SUCESSO, 'Sucesso'),
        (INELEGIVEL, 'Inelegível'),
    )


# Estado da solicitação inicial (vendedor → operacional)
class EstadoSolicitacaoProposta:
    ENVIADA = 'ENVIADA'
    EM_ANALISE_OPERACIONAL = 'EM_ANALISE_OPERACIONAL'
    RESULTADO_PROPOSTAS = 'RESULTADO_PROPOSTAS'
    RESULTADO_INELEGIVEL = 'RESULTADO_INELEGIVEL'
    CHOICES = (
        (ENVIADA, 'Enviada'),
        (EM_ANALISE_OPERACIONAL, 'Em análise (operacional)'),
        (RESULTADO_PROPOSTAS, 'Propostas disponíveis'),
        (RESULTADO_INELEGIVEL, 'Inelegível'),
    )


# Macro-etapa operacional (ContratoExecucao — nexos)
# Nova aba "FORMALIZACAO" separa a etapa de formalização da digitação pura
# (Aguardando/Digitado) conforme redesenho da esteira.
class EtapaOperacional:
    DIGITACAO = 'DIGITACAO'
    FORMALIZACAO = 'FORMALIZACAO'
    ANALISE = 'ANALISE'
    CIP = 'CIP'
    REFIN = 'REFIN'
    ANUENCIA = 'ANUENCIA'
    PAGAMENTO = 'PAGAMENTO'
    PENDENCIAS = 'PENDENCIAS'
    CANCELADO = 'CANCELADO'
    CHOICES = (
        (DIGITACAO, 'Digitando'),
        (FORMALIZACAO, 'Formalização'),
        (ANALISE, 'Analisando'),
        (CIP, 'CIP'),
        (REFIN, 'REFIN'),
        (ANUENCIA, 'Anuência'),
        (PAGAMENTO, 'Pagamento'),
        (PENDENCIAS, 'Pendente'),
        (CANCELADO, 'Cancelado'),
    )


# Sub-status por macro-etapa (valores persistidos; validação por etapa no serviço)
class SubStatusOperacional:
    # Digitação (novo fluxo: somente Aguardando/Digitado)
    DIG_AGUARDANDO = 'DIG_AGUARDANDO'
    DIG_DIGITADO = 'DIG_DIGITADO'
    # Digitação (legado — mantido para histórico e migração de dados)
    DIG_LINK_DISPONIBILIZADO = 'DIG_LINK_DISPONIBILIZADO'
    DIG_CHECADO = 'DIG_CHECADO'
    DIG_FORMALIZADO = 'DIG_FORMALIZADO'
    # Formalização (nova etapa separada)
    FORM_LINK_DISPONIVEL = 'FORM_LINK_DISPONIVEL'
    FORM_CHECADO = 'FORM_CHECADO'
    FORM_FORMALIZADO = 'FORM_FORMALIZADO'
    # Análise
    ANL_AGUARDANDO = 'ANL_AGUARDANDO'
    ANL_SUCESSO = 'ANL_SUCESSO'
    # CIP / Refin
    CIP_AGUARDANDO = 'CIP_AGUARDANDO'
    CIP_SUCESSO = 'CIP_SUCESSO'
    REFIN_AGUARDANDO = 'REFIN_AGUARDANDO'
    REFIN_SUCESSO = 'REFIN_SUCESSO'
    # Anuência
    ANU_AGUARDANDO = 'ANU_AGUARDANDO'
    ANU_AVERBADO = 'ANU_AVERBADO'
    # Pagamento
    PG_AGUARDANDO_CLIENTE = 'PG_AGUARDANDO_CLIENTE'
    PG_PAGO_CLIENTE = 'PG_PAGO_CLIENTE'
    PG_AGUARDANDO_TC = 'PG_AGUARDANDO_TC'
    PG_PAGO_TC = 'PG_PAGO_TC'  # legado — mantido para compatibilidade do histórico
    PG_PAGO_TC_PARCIAL = 'PG_PAGO_TC_PARCIAL'
    PG_PAGO_TC_TOTAL = 'PG_PAGO_TC_TOTAL'
    PG_AGUARDANDO_CMS = 'PG_AGUARDANDO_CMS'
    PG_PAGO_CMS = 'PG_PAGO_CMS'
    PG_PAGO_CMS_EMPRESA = 'PG_PAGO_CMS_EMPRESA'
    # Pendências
    PEND_AGUARDANDO = 'PEND_AGUARDANDO'
    PEND_CORRIGIDO = 'PEND_CORRIGIDO'
    # Cancelado
    CAN_ENCERRADO = 'CAN_ENCERRADO'
    CAN_CLIENTE = 'CAN_CLIENTE'
    CAN_CORRETOR = 'CAN_CORRETOR'
    CAN_BANCO = 'CAN_BANCO'
    CAN_REEMBOLSO = 'CAN_REEMBOLSO'

    CHOICES = (
        (DIG_AGUARDANDO, 'Aguardando operacional'),
        (DIG_DIGITADO, 'Digitado'),
        (DIG_LINK_DISPONIBILIZADO, 'Link disponibilizado (legado)'),
        (DIG_CHECADO, 'Checado (legado)'),
        (DIG_FORMALIZADO, 'Formalizado (legado)'),
        (FORM_LINK_DISPONIVEL, 'Link disponível'),
        (FORM_CHECADO, 'Checado'),
        (FORM_FORMALIZADO, 'Formalizado'),
        (ANL_AGUARDANDO, 'Aguardando análise'),
        (ANL_SUCESSO, 'Análise aprovada'),
        (CIP_AGUARDANDO, 'Aguardando CIP'),
        (CIP_SUCESSO, 'CIP aprovado'),
        (REFIN_AGUARDANDO, 'Aguardando REFIN'),
        (REFIN_SUCESSO, 'REFIN aprovado'),
        (ANU_AGUARDANDO, 'Aguardando anuência'),
        (ANU_AVERBADO, 'Averbado'),
        (PG_AGUARDANDO_CLIENTE, 'Aguardando Pagamento Cliente'),
        (PG_PAGO_CLIENTE, 'Pago Cliente'),
        (PG_AGUARDANDO_TC, 'Aguardando Verificação de Valores'),
        (PG_PAGO_TC, 'Pago TC (legado)'),
        (PG_PAGO_TC_PARCIAL, 'Pago TC Parcial'),
        (PG_PAGO_TC_TOTAL, 'Pago TC Total'),
        (PG_AGUARDANDO_CMS, 'Aguardando pagamento CMS'),
        (PG_PAGO_CMS, 'Pago CMS'),
        (PG_PAGO_CMS_EMPRESA, 'Pago CMS Empresa'),
        (PEND_AGUARDANDO, 'Pendência em aberto'),
        (PEND_CORRIGIDO, 'Pendência corrigida'),
        (CAN_ENCERRADO, 'Encerrado'),
        (CAN_CLIENTE, 'Cancelado pelo cliente'),
        (CAN_CORRETOR, 'Cancelado pelo corretor'),
        (CAN_BANCO, 'Cancelado pelo banco'),
        (CAN_REEMBOLSO, 'Estorno'),
    )


# Sub-status em Pagamento onde o vendedor pode enviar comprovante (arquivo + título, sem valor).
SUB_STATUS_ENVIO_COMPROVANTE_PAGAMENTO_VENDEDOR = frozenset({
    SubStatusOperacional.PG_AGUARDANDO_CLIENTE,
    SubStatusOperacional.PG_PAGO_CLIENTE,
    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
})


def contrato_permite_envio_comprovante_pagamento_vendedor(ce) -> bool:
    """True quando o contrato permite anexo de comprovante pelo vendedor (sem valor monetário)."""
    if ce is None:
        return False
    return (
        getattr(ce, 'etapa_operacional', None) == EtapaOperacional.PAGAMENTO
        and getattr(ce, 'sub_status_operacional', None) in SUB_STATUS_ENVIO_COMPROVANTE_PAGAMENTO_VENDEDOR
    )


# Upload de comprovante pelo vendedor (PDF ou imagem, alinhado ao accept do CRM TC).
COMPROVANTE_VENDEDOR_EXTENSOES_PERMITIDAS = frozenset({'.pdf', '.jpg', '.jpeg', '.png', '.webp'})
COMPROVANTE_VENDEDOR_MAX_BYTES = 10 * 1024 * 1024


def validar_arquivo_comprovante_vendedor(uploaded_file):
    """Retorna (ok, mensagem_erro)."""
    if not uploaded_file:
        return False, 'Arquivo obrigatório.'
    nome = getattr(uploaded_file, 'name', '') or ''
    ext = os.path.splitext(nome)[1].lower()
    if ext not in COMPROVANTE_VENDEDOR_EXTENSOES_PERMITIDAS:
        return False, 'Formato não permitido. Use PDF ou imagem (JPG, PNG ou WEBP).'
    tamanho = getattr(uploaded_file, 'size', None)
    if tamanho is not None and tamanho > COMPROVANTE_VENDEDOR_MAX_BYTES:
        return False, 'Arquivo excede o tamanho máximo de 10 MB.'
    return True, ''


# Tags financeiras de referência (nexos — exibição / relatório)
class TagFinanceiraContrato:
    PAGO_CLIENTE = 'PAGO_CLIENTE'
    PAGO_TC = 'PAGO_TC'
    AGUARDANDO_PAGAMENTO_EMPRESA = 'AGUARDANDO_PAGAMENTO_EMPRESA'
    PAGO_CMS = 'PAGO_CMS'
    CHOICES = (
        (PAGO_CLIENTE, 'Pago cliente'),
        (PAGO_TC, 'Pago TC'),
        (AGUARDANDO_PAGAMENTO_EMPRESA, 'Aguardando pagamento empresa (CMS)'),
        (PAGO_CMS, 'Pago CMS / empresa'),
    )


# Fase legada (ContratoExecucao) — mantida para compatibilidade com filtros antigos; sincronizada a partir de etapa+sub
class FaseContratoExecucao:
    DIGITACAO_AGUARDANDO = 'DIGITACAO_AGUARDANDO'
    AGUARDANDO_FORMALIZACAO = 'AGUARDANDO_FORMALIZACAO'
    EM_ANALISE = 'EM_ANALISE'
    AGUARDANDO_ANUENCIA = 'AGUARDANDO_ANUENCIA'
    AGUARDANDO_PAGAMENTO_CLIENTE = 'AGUARDANDO_PAGAMENTO_CLIENTE'
    CLIENTE_PAGO = 'CLIENTE_PAGO'
    AGUARDANDO_PAGAMENTO_TC = 'AGUARDANDO_PAGAMENTO_TC'
    CANCELADO = 'CANCELADO'
    CHOICES = (
        (DIGITACAO_AGUARDANDO, 'Digitando — aguardando'),
        (AGUARDANDO_FORMALIZACAO, 'Aguardando formalização'),
        (EM_ANALISE, 'Em análise'),
        (AGUARDANDO_ANUENCIA, 'Aguardando anuência'),
        (AGUARDANDO_PAGAMENTO_CLIENTE, 'Aguardando pagamento cliente'),
        (CLIENTE_PAGO, 'Cliente pago'),
        (AGUARDANDO_PAGAMENTO_TC, 'Aguardando pagamento TC'),
        (CANCELADO, 'Cancelado'),
    )


# Solicitação de digitação (após vendedor marcar propostas + PDF)
class EstadoSolicitacaoDigitacao:
    PENDENTE_OPERACIONAL = 'PENDENTE_OPERACIONAL'
    EM_DIGITACAO = 'EM_DIGITACAO'
    PENDENTE_CORRECAO = 'PENDENTE_CORRECAO'
    CANCELADA = 'CANCELADA'
    CONTRATO_GERADO = 'CONTRATO_GERADO'
    CHOICES = (
        (PENDENTE_OPERACIONAL, 'Pendente operacional'),
        (EM_DIGITACAO, 'Em digitação'),
        (PENDENTE_CORRECAO, 'Pendente correção (vendedor)'),
        (CANCELADA, 'Cancelada (sem contrato)'),
        (CONTRATO_GERADO, 'Contrato gerado'),
    )


# Sub-status comercial em Propostas (carteira — nexos)
class SubStatusPropostaComercial:
    ACEITE = 'ACEITE'
    VERIFICANDO = 'VERIFICANDO'
    VERIFICADO = 'VERIFICADO'
    CHOICES = (
        (ACEITE, 'Aceite'),
        (VERIFICANDO, 'Verificando'),
        (VERIFICADO, 'Verificado'),
    )
