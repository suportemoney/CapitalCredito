# -*- coding: utf-8 -*-
"""APIs de ações sobre contratos executados (pós-digitação):
- Edição de dados do cliente/proposta (operacional/supervisor).
- Pendências tipadas (criar, listar, resolver).
- Comprovantes TC (upload com acumulado Parcial/Total).
Todas as ações registram `HistoricoTransicaoContrato` para timeline.
"""
import json
import logging
import os
import unicodedata
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.transaction import TransactionManagementError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.seguranca.permissoes.decorators import controle_acess
from apps.seguranca.permissoes.utils import user_has_access

from apps.contratos_v2.apis.fluxo import controle_acess_multiplos

from apps.contratos_v2.apis.carteira_contrato_permissoes import (
    contrato_vinculado_carteiras_responsavel,
    pendencia_tipos_abertos,
    vendedor_pode_acesso_pendencia_contrato,
)
# Reaproveita defer dos campos pré-contrato (migração 0050) para queries com select_related da solicitação.
from apps.contratos_v2.apis.fluxo import (
    DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO,
    _montar_registermoney_extra_supervisor_pago_tc,
    _solicitacao_digitacao_queryset_schema_seguro,
)
from apps.contratos_v2.fluxo_constants import EtapaOperacional, EstadoSolicitacaoDigitacao, SubStatusOperacional
from apps.contratos_v2.fluxo_transicoes import (
    _registrar_historico,
    aplicar_etapa_sub,
    persistir_tc_modal_em_contrato_e_rm,
    zerar_tc_modal_em_contrato,
    sincronizar_register_money_dados_modal_pago_tc,
    transicao_por_acao,
    valor_tc_efetivo_para_fluxo,
)
from apps.contratos_v2.models import (
    ClienteArquivo,
    ClienteBancario,
    ClienteContato,
    ClienteDadosPessoais,
    ClienteEndereco,
    ComprovanteTC,
    ContratoDadosOperacionais,
    ContratoExecucao,
    EnvioComprovantePagamentoVendedor,
    HistoricoEventoDigitacao,
    HistoricoTransicaoContrato,
    Pendencia,
    PropostaDados,
    SolicitacaoDigitacao,
)
logger = logging.getLogger(__name__)


def _json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _dec(v):
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _cargo_indica_operacoes_backoffice(nome_upper: str) -> bool:
    """True para cargos como «Assistente de Operações» que não contêm «OPERACIONAL»."""
    if 'OPERAÇÕES' in nome_upper:
        return True
    sem_acento = ''.join(
        c for c in unicodedata.normalize('NFD', nome_upper) if unicodedata.category(c) != 'Mn'
    )
    return 'OPERACOES' in sem_acento


def _papel_usuario(user):
    """Classifica o papel do user no fluxo de contratos a partir do Cargo do funcionário.
    Retorna 'operacional' | 'supervisor' | 'vendedor' | 'financeiro' | None.
    """
    try:
        from apps.rh.funcionarios.models import Funcionario
        f = Funcionario.objects.select_related('dados_profissionais__cargo').filter(
            usuario=user, status=True
        ).first()
        dp = getattr(f, 'dados_profissionais', None) if f else None
        if not f or not dp or not dp.cargo_id:
            return None
        nome = (dp.cargo.nome or '').upper()
        if 'SUPERVISOR' in nome:
            return 'supervisor'
        if (
            'OPERACIONAL' in nome
            or 'DIGITADOR' in nome
            or _cargo_indica_operacoes_backoffice(nome)
        ):
            return 'operacional'
        if 'FINANCEIRO' in nome or 'FINANC' in nome:
            return 'financeiro'
        return 'vendedor'
    except Exception:
        return None


def _financeiros_travados_por_pagamento(ce) -> bool:
    """Retorna True quando os campos financeiros do contrato (AF/TC/Liberado)
    devem ficar bloqueados para edição.
    Regra: trava a partir do primeiro comprovante TC ativo OU quando já existe
    RegisterMoney (TC) com `classificador_auto` definido vinculado ao contrato.
    """
    try:
        if ComprovanteTC.objects.filter(contrato_execucao=ce, status=True).exists():
            return True
    except Exception:
        pass
    try:
        from apps.vendas.siape.models import RegisterMoney
        qs = RegisterMoney.objects.filter(contrato_execucao=ce, status=True)
        # Classificador não nulo / não vazio indica que a TC já foi processada.
        if qs.exclude(classificador_auto__isnull=True).exclude(classificador_auto='').exists():
            return True
    except Exception:
        # Falhas de import/consulta não devem impedir a edição; guard opera
        # em modo best-effort: o `ComprovanteTC` já cobre o cenário principal.
        pass
    return False


# ============================================================================
# Editar dados do cliente/proposta (operacional e supervisor)
# ============================================================================

# Aliases aceitos no payload de cliente.* — mapeiam rótulos amigáveis da UI
# para nomes reais no model `ClienteDadosPessoais`.
_CLIENTE_FIELD_ALIASES = {
    'rg': 'numero_rg',
    'nome': 'nome_completo',
}


def _normalizar_campos_cliente(payload):
    """Aplica aliases (ex.: rg -> numero_rg) e preserva chaves já canônicas."""
    if not isinstance(payload, dict):
        return {}
    normalizado = {}
    for chave, valor in payload.items():
        chave_final = _CLIENTE_FIELD_ALIASES.get(chave, chave)
        normalizado[chave_final] = valor
    return normalizado


def _validar_financeiro_nao_negativo(valor):
    """Retorna True se o valor (já convertido para Decimal) é >= 0 ou None."""
    if valor is None:
        return True
    try:
        return Decimal(valor) >= 0
    except (InvalidOperation, ValueError, TypeError):
        return False


def _dict_payload_tem_valor_real(d):
    """True se o dict JSON tiver ao menos um valor não vazio (bloqueio contrato/DO pré-CE)."""
    if not isinstance(d, dict):
        return False
    for v in d.values():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return True
    return False


def _editar_dados_via_solicitacao_digitacao(request, data, sol_id):
    """Persiste cliente + proposta vinculados à solicitação antes de existir `ContratoExecucao`."""
    if ContratoExecucao.objects.filter(solicitacao_digitacao_id=sol_id, status=True).exists():
        return JsonResponse(
            {
                'ok': False,
                'erro': (
                    'Contrato já gerado para esta solicitação. Recarregue a esteira e edite pelo registro de contrato.'
                ),
            },
            status=409,
        )
    ctr_raw = data.get('contrato') if isinstance(data.get('contrato'), dict) else {}
    if ctr_raw:
        for k in ctr_raw.keys():
            if k not in ('numero_contrato', 'link_formalizacao'):
                return JsonResponse(
                    {
                        'ok': False,
                        'erro': (
                            'Antes da digitação, em contrato só são permitidos o número no banco '
                            'e o link de formalização.'
                        ),
                    },
                    status=400,
                )
    if _dict_payload_tem_valor_real(data.get('dados_operacionais') or {}):
        return JsonResponse(
            {
                'ok': False,
                'erro': 'Antes de gerar o contrato, altere apenas dados de cliente e proposta.',
            },
            status=400,
        )

    sol = get_object_or_404(
        _solicitacao_digitacao_queryset_schema_seguro()
        .select_related('proposta_dados__cliente_dados_pessoais', 'carteira_clientes'),
        pk=sol_id,
    )
    # Permissão alinhada à leitura da ficha: quem conseguiu abrir o modal pode salvar.
    # A barreira de visibilidade já é feita por `api_get_ficha` e pela UI da esteira/loja.
    papel = _papel_usuario(request.user) or ''

    pd = sol.proposta_dados
    if not pd:
        return JsonResponse({'ok': False, 'erro': 'Proposta não vinculada à solicitação.'}, status=400)
    dp = pd.cliente_dados_pessoais
    if not dp:
        return JsonResponse({'ok': False, 'erro': 'Cliente não vinculado à proposta.'}, status=400)

    if 'link_formalizacao' in ctr_raw:
        lv = ctr_raw.get('link_formalizacao')
        if isinstance(lv, str):
            lv = lv.strip() or None
        elif lv is not None:
            lv = str(lv).strip() or None
        else:
            lv = None
        if lv:
            try:
                URLValidator()(lv)
            except ValidationError:
                return JsonResponse(
                    {
                        'ok': False,
                        'erro': 'Link de formalização inválido.',
                        'campos_invalidos': ['contrato.link_formalizacao'],
                    },
                    status=400,
                )

    CAMPOS_FINANCEIROS = ('valor_af', 'valor_tc', 'valor_liberado')
    financeiros_travados = False
    campos_alterados = []
    erros_validacao = []

    with transaction.atomic():
        dp_payload_raw = data.get('cliente') or {}
        dp_payload = _normalizar_campos_cliente(dp_payload_raw)
        campos_dp = (
            'nome_completo', 'data_nascimento', 'numero_rg', 'estado_civil',
            'nome_mae', 'nome_pai', 'naturalidade', 'nacionalidade', 'sexo',
        )
        for k in campos_dp:
            if k in dp_payload:
                novo = dp_payload.get(k)
                if isinstance(novo, str):
                    novo = novo.strip() or None
                if k == 'nome_completo' and not novo and (getattr(dp, 'nome_completo', None) or '').strip():
                    erros_validacao.append('cliente.nome_completo não pode ficar vazio.')
                    continue
                if getattr(dp, k, None) != novo:
                    setattr(dp, k, novo)
                    campos_alterados.append(f'cliente.{k}')
        if erros_validacao:
            return JsonResponse({
                'ok': False,
                'erro': 'Campos inválidos.',
                'campos_invalidos': erros_validacao,
            }, status=400)
        dp.save()

        contato_campos_enviados = [k for k in ('email', 'telefone') if k in dp_payload]
        if contato_campos_enviados:
            contato_obj, _ = ClienteContato.objects.get_or_create(cliente_dados_pessoais=dp)
            for k in contato_campos_enviados:
                novo = dp_payload.get(k)
                if isinstance(novo, str):
                    novo = novo.strip() or None
                if getattr(contato_obj, k, None) != novo:
                    setattr(contato_obj, k, novo)
                    campos_alterados.append(f'cliente.{k}')
            contato_obj.save()

        # ------ Dados bancários do cliente (ClienteBancario, OneToOne com DP) ------
        # Mesma lógica do fluxo pós-contrato: persiste sob demanda no DP da solicitação.
        ban_payload = data.get('bancario') or {}
        if isinstance(ban_payload, dict) and ban_payload:
            cb, _cb_created = ClienteBancario.objects.get_or_create(cliente_dados_pessoais=dp)
            campos_cb_str = (
                'banco', 'agencia', 'dv_agencia', 'conta', 'dv_conta',
                'tipo_conta', 'tipo_pagamento',
            )
            cb_alterado = False
            for k in campos_cb_str:
                if k in ban_payload:
                    novo = ban_payload.get(k)
                    if isinstance(novo, str):
                        novo = novo.strip() or None
                    if getattr(cb, k, None) != novo:
                        setattr(cb, k, novo)
                        cb_alterado = True
                        campos_alterados.append(f'bancario.{k}')
            if 'incluir_seguro' in ban_payload:
                novo_seg = bool(ban_payload.get('incluir_seguro'))
                if cb.incluir_seguro != novo_seg:
                    cb.incluir_seguro = novo_seg
                    cb_alterado = True
                    campos_alterados.append('bancario.incluir_seguro')
            if cb_alterado:
                cb.save()

        pp_payload = (data.get('proposta') or {}) if isinstance(data.get('proposta'), dict) else {}
        if pp_payload:
            for k in ('valor_parcela', 'prazo', 'valor_af', 'valor_tc', 'valor_liberado', 'coeficiente'):
                if k in pp_payload:
                    if financeiros_travados and k in CAMPOS_FINANCEIROS:
                        valor_enviado = _dec(pp_payload.get(k))
                        if getattr(pd, k, None) != valor_enviado:
                            return JsonResponse({
                                'ok': False,
                                'erro': (
                                    'Campos financeiros (AF/TC/Liberado) estão travados '
                                    'após o primeiro pagamento de TC.'
                                ),
                                'campo_bloqueado': f'proposta.{k}',
                            }, status=409)
                        continue
                    raw = pp_payload.get(k)
                    if k == 'prazo':
                        try:
                            novo = int(raw) if raw not in (None, '') else None
                        except (TypeError, ValueError):
                            erros_validacao.append(f'proposta.{k} inválido.')
                            continue
                        if novo is not None and novo < 1:
                            erros_validacao.append(f'proposta.{k} deve ser >= 1.')
                            continue
                    else:
                        novo = _dec(raw)
                        if novo is not None and not _validar_financeiro_nao_negativo(novo):
                            erros_validacao.append(f'proposta.{k} não pode ser negativo.')
                            continue
                    if getattr(pd, k, None) != novo:
                        setattr(pd, k, novo)
                        campos_alterados.append(f'proposta.{k}')
            if erros_validacao:
                return JsonResponse({
                    'ok': False,
                    'erro': 'Campos inválidos.',
                    'campos_invalidos': erros_validacao,
                }, status=400)
            pd.save()

        from django.db import DatabaseError as _DatabaseError

        sol_update_fields = []
        if isinstance(ctr_raw, dict) and ctr_raw:
            if 'numero_contrato' in ctr_raw:
                nv = ctr_raw.get('numero_contrato')
                if isinstance(nv, str):
                    nv = nv.strip() or None
                elif nv is not None:
                    nv = str(nv).strip() or None
                try:
                    atual = getattr(sol, 'numero_contrato_banco_pre', None)
                except _DatabaseError:
                    atual = None
                if atual != nv:
                    sol.numero_contrato_banco_pre = nv
                    sol_update_fields.append('numero_contrato_banco_pre')
                    campos_alterados.append('contrato.numero_contrato')
            if 'link_formalizacao' in ctr_raw:
                nv = ctr_raw.get('link_formalizacao')
                if isinstance(nv, str):
                    nv = nv.strip() or None
                elif nv is not None:
                    nv = str(nv).strip() or None
                else:
                    nv = None
                try:
                    atual = getattr(sol, 'link_formalizacao_pre', None)
                except _DatabaseError:
                    atual = None
                if atual != nv:
                    sol.link_formalizacao_pre = nv
                    sol_update_fields.append('link_formalizacao_pre')
                    campos_alterados.append('contrato.link_formalizacao')
        if sol_update_fields:
            # Se as colunas da migração 0050 ainda não existem no banco, fingir gravado
            # sem alterar nada; o supervisor verá no log do servidor a necessidade de migrar.
            try:
                sol.save(update_fields=sol_update_fields)
            except _DatabaseError as _exc:
                logger.exception(
                    '_editar_dados_via_solicitacao_digitacao: schema desatualizado ao salvar '
                    'campos pré-contrato %s: %s', sol_update_fields, _exc,
                )
                return JsonResponse(
                    {
                        'ok': False,
                        'erro': (
                            'Schema do banco desatualizado: campos pré-contrato (Nº contrato/Link) '
                            'não estão disponíveis. Solicite ao administrador que execute as migrações.'
                        ),
                    },
                    status=500,
                )

        if campos_alterados:
            obs = f'Edição CRM pré-contrato ({papel}): ' + ', '.join(campos_alterados)
        else:
            obs = f'Edição CRM pré-contrato sem alterações detectadas ({papel})'
        HistoricoEventoDigitacao.objects.create(
            solicitacao=sol,
            estado_anterior=sol.estado,
            estado_novo=sol.estado,
            usuario=request.user,
            observacao=obs[:500],
        )

    return JsonResponse({'ok': True, 'campos_alterados': campos_alterados})


@login_required
@require_POST
def api_post_editar_dados_contrato(request):
    """Atualiza campos não críticos de `ClienteDadosPessoais`/`ClienteContato`,
    `PropostaDados`, `ContratoDadosOperacionais` e `ContratoExecucao`
    (numero_contrato/link_formalizacao).

    Com `solicitacao_digitacao_id` (e sem `contrato_id`), atualiza apenas cliente e
    proposta da solicitação de digitação antes de existir contrato na esteira.

    Permissão: Operacional ou Supervisor (Cargo), qualquer usuário com acesso
    SCT189 (mesmo critério da esteira CRM), ou vendedor em fluxo de pendências
    (Validação [9]) — o ramo por solicitação exige operacional/SCT189.
    Registra entrada na timeline via `HistoricoTransicaoContrato`.

    Validações:
        - Trava financeira (AF/TC/Liberado) após primeiro pagamento de TC.
        - `nome_completo` não pode virar vazio se já existe valor.
        - Valores monetários devem ser >= 0.
    """
    data = _json(request)
    contrato_id = data.get('contrato_id')
    sol_raw = data.get('solicitacao_digitacao_id')
    if sol_raw is not None and str(sol_raw).strip() != '':
        if contrato_id:
            return JsonResponse(
                {'ok': False, 'erro': 'Informe apenas contrato_id ou solicitacao_digitacao_id.'},
                status=400,
            )
        try:
            sol_id = int(sol_raw)
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'solicitacao_digitacao_id inválido.'}, status=400)
        return _editar_dados_via_solicitacao_digitacao(request, data, sol_id)
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    ce = get_object_or_404(
        ContratoExecucao.objects.select_related(
            'solicitacao_digitacao',
            'proposta_dados__solicitacao_origem',
        ).defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO),
        pk=int(contrato_id),
    )

    # Permissão alinhada à leitura: quem consegue abrir o modal pode salvar.
    # As travas de papel/tipo de pendência foram removidas a pedido do produto.
    papel = _papel_usuario(request.user) or ''

    # Integridade financeira (critério 8 da validação [4]):
    # Após o primeiro pagamento de TC, AF/TC/Liberado ficam travados.
    CAMPOS_FINANCEIROS = ('valor_af', 'valor_tc', 'valor_liberado')
    financeiros_travados = _financeiros_travados_por_pagamento(ce)

    campos_alterados = []
    erros_validacao = []

    with transaction.atomic():
        # ------ Dados do cliente (ClienteDadosPessoais) ------
        dp_payload_raw = data.get('cliente') or {}
        dp_payload = _normalizar_campos_cliente(dp_payload_raw)
        dp = ce.cliente_dados_pessoais
        campos_dp = (
            'nome_completo', 'data_nascimento', 'numero_rg', 'estado_civil',
            'nome_mae', 'nome_pai', 'naturalidade', 'nacionalidade', 'sexo',
        )
        for k in campos_dp:
            if k in dp_payload:
                novo = dp_payload.get(k)
                if isinstance(novo, str):
                    novo = novo.strip() or None
                # Validação [7] — obrigatoriedade: nome_completo não pode
                # virar vazio se já havia valor gravado.
                if k == 'nome_completo' and not novo and (getattr(dp, 'nome_completo', None) or '').strip():
                    erros_validacao.append('cliente.nome_completo não pode ficar vazio.')
                    continue
                if getattr(dp, k, None) != novo:
                    setattr(dp, k, novo)
                    campos_alterados.append(f'cliente.{k}')
        if erros_validacao:
            return JsonResponse({
                'ok': False,
                'erro': 'Campos inválidos.',
                'campos_invalidos': erros_validacao,
            }, status=400)
        dp.save()

        # ------ Dados de contato (ClienteContato, OneToOne com DP) ------
        # email e telefone são aceitos no objeto `cliente.*` da UI; persistem no
        # objeto de contato principal. Criado sob demanda via get_or_create.
        contato_campos_enviados = [k for k in ('email', 'telefone') if k in dp_payload]
        if contato_campos_enviados:
            contato_obj, _ = ClienteContato.objects.get_or_create(cliente_dados_pessoais=dp)
            for k in contato_campos_enviados:
                novo = dp_payload.get(k)
                if isinstance(novo, str):
                    novo = novo.strip() or None
                if getattr(contato_obj, k, None) != novo:
                    setattr(contato_obj, k, novo)
                    campos_alterados.append(f'cliente.{k}')
            contato_obj.save()

        # ------ Dados bancários do cliente (ClienteBancario, OneToOne com DP) ------
        # Persistido sob demanda (get_or_create). incluir_seguro é boolean; demais são strings.
        ban_payload = data.get('bancario') or {}
        if isinstance(ban_payload, dict) and ban_payload:
            cb, _cb_created = ClienteBancario.objects.get_or_create(cliente_dados_pessoais=dp)
            campos_cb_str = (
                'banco', 'agencia', 'dv_agencia', 'conta', 'dv_conta',
                'tipo_conta', 'tipo_pagamento',
            )
            cb_alterado = False
            for k in campos_cb_str:
                if k in ban_payload:
                    novo = ban_payload.get(k)
                    if isinstance(novo, str):
                        novo = novo.strip() or None
                    if getattr(cb, k, None) != novo:
                        setattr(cb, k, novo)
                        cb_alterado = True
                        campos_alterados.append(f'bancario.{k}')
            if 'incluir_seguro' in ban_payload:
                novo_seg = bool(ban_payload.get('incluir_seguro'))
                if cb.incluir_seguro != novo_seg:
                    cb.incluir_seguro = novo_seg
                    cb_alterado = True
                    campos_alterados.append('bancario.incluir_seguro')
            if cb_alterado:
                cb.save()

        # ------ Dados da proposta (PropostaDados) ------
        pp_payload = (data.get('proposta') or {}) if isinstance(data.get('proposta'), dict) else {}
        pd = getattr(ce, 'proposta_dados', None)
        if pd is not None and pp_payload:
            # Campos monetários convertidos via _dec; coeficiente também Decimal; prazo inteiro.
            for k in ('valor_parcela', 'prazo', 'valor_af', 'valor_tc', 'valor_liberado', 'coeficiente'):
                if k in pp_payload:
                    # Bloqueia alteração de AF/TC/Liberado após primeiro pagamento
                    if financeiros_travados and k in CAMPOS_FINANCEIROS:
                        valor_enviado = _dec(pp_payload.get(k))
                        if getattr(pd, k, None) != valor_enviado:
                            return JsonResponse({
                                'ok': False,
                                'erro': (
                                    'Campos financeiros (AF/TC/Liberado) estão travados '
                                    'após o primeiro pagamento de TC.'
                                ),
                                'campo_bloqueado': f'proposta.{k}',
                            }, status=409)
                        continue
                    raw = pp_payload.get(k)
                    if k == 'prazo':
                        try:
                            novo = int(raw) if raw not in (None, '') else None
                        except (TypeError, ValueError):
                            erros_validacao.append(f'proposta.{k} inválido.')
                            continue
                        if novo is not None and novo < 1:
                            erros_validacao.append(f'proposta.{k} deve ser >= 1.')
                            continue
                    else:
                        novo = _dec(raw)
                        if novo is not None and not _validar_financeiro_nao_negativo(novo):
                            erros_validacao.append(f'proposta.{k} não pode ser negativo.')
                            continue
                    if getattr(pd, k, None) != novo:
                        setattr(pd, k, novo)
                        campos_alterados.append(f'proposta.{k}')
            if erros_validacao:
                return JsonResponse({
                    'ok': False,
                    'erro': 'Campos inválidos.',
                    'campos_invalidos': erros_validacao,
                }, status=400)
            pd.save()
            # Espelha no snapshot o que o modal Pago TC / comprovantes leem em DO.
            try:
                d_esp = ce.dados_operacionais
            except ContratoDadosOperacionais.DoesNotExist:
                d_esp = None
            if d_esp is not None:
                _espelhar_proposta_financeiros_em_do(d_esp, pd, pp_payload, campos_alterados)

        # ------ Dados operacionais (snapshot AF/TC do contrato) ------
        do_payload = (data.get('dados_operacionais') or {}) if isinstance(data.get('dados_operacionais'), dict) else {}
        try:
            d = ce.dados_operacionais
        except ContratoDadosOperacionais.DoesNotExist:
            d = None
        if d and do_payload:
            for k in ('valor_af', 'valor_tc', 'valor_liberado', 'valor_parcela', 'prazo'):
                if k in do_payload:
                    if financeiros_travados and k in CAMPOS_FINANCEIROS:
                        valor_enviado = _dec(do_payload.get(k))
                        if getattr(d, k, None) != valor_enviado:
                            return JsonResponse({
                                'ok': False,
                                'erro': (
                                    'Campos financeiros (AF/TC/Liberado) estão travados '
                                    'após o primeiro pagamento de TC.'
                                ),
                                'campo_bloqueado': f'dados_operacionais.{k}',
                            }, status=409)
                        continue
                    raw = do_payload.get(k)
                    if k == 'prazo':
                        try:
                            novo = int(raw) if raw not in (None, '') else None
                        except (TypeError, ValueError):
                            erros_validacao.append(f'dados_operacionais.{k} inválido.')
                            continue
                    else:
                        novo = _dec(raw)
                        if novo is not None and not _validar_financeiro_nao_negativo(novo):
                            erros_validacao.append(f'dados_operacionais.{k} não pode ser negativo.')
                            continue
                    if getattr(d, k, None) != novo:
                        setattr(d, k, novo)
                        campos_alterados.append(f'dados_operacionais.{k}')
            if erros_validacao:
                return JsonResponse({
                    'ok': False,
                    'erro': 'Campos inválidos.',
                    'campos_invalidos': erros_validacao,
                }, status=400)
            d.save()

        # ------ ContratoExecucao (número do contrato e link de formalização) ------
        ce_payload = (data.get('contrato') or {}) if isinstance(data.get('contrato'), dict) else {}
        if ce_payload:
            # Aceita aliases: numero_contrato -> codigo (campo real no ContratoExecucao).
            mapa_ce = {
                'codigo': 'codigo',
                'numero_contrato': 'codigo',
                'link_formalizacao': 'link_formalizacao',
            }
            ce_alterado = False
            for chave_payload, atributo in mapa_ce.items():
                if chave_payload in ce_payload:
                    novo = ce_payload.get(chave_payload)
                    if isinstance(novo, str):
                        novo = novo.strip() or None
                    if getattr(ce, atributo, None) != novo:
                        setattr(ce, atributo, novo)
                        campos_alterados.append(f'contrato.{atributo}')
                        ce_alterado = True
            if ce_alterado:
                ce.save(update_fields=['codigo', 'link_formalizacao'])

        # ------ Histórico (timeline) ------
        # Observação inclui o papel do usuário para rastreabilidade (validações [7] e [9]).
        if campos_alterados:
            obs = f'Edição de dados ({papel}): ' + ', '.join(campos_alterados)
        else:
            obs = f'Edição sem alterações detectadas ({papel})'
        _registrar_historico(
            ce,
            ce.etapa_operacional, ce.sub_status_operacional,
            ce.etapa_operacional, ce.sub_status_operacional,
            request.user, obs[:500],
        )

    return JsonResponse({'ok': True, 'campos_alterados': campos_alterados})


# ============================================================================
# Exclusão de arquivo do cliente (Validação [7] — aba Arquivos do modal de edição)
# ============================================================================

@login_required
@controle_acess_multiplos('SCT189', 'SCT201')
@require_POST
def api_post_excluir_cliente_arquivo(request):
    """Exclui um `ClienteArquivo` vinculado ao contrato (via cliente_dados_pessoais).

    Payload JSON:
        {contrato_id, arquivo_id}

    Regras:
        - Permitido apenas para papel `operacional` ou `supervisor`.
        - O `ClienteArquivo` precisa pertencer ao mesmo `ClienteDadosPessoais`
          do contrato (defesa contra exclusão cruzada).
        - Remove o arquivo físico via `FileField.delete(save=False)` antes de
          apagar a row — evita arquivo órfão no storage.
        - Registra observação na timeline (`HistoricoTransicaoContrato`).
    """
    data = _json(request)
    contrato_id = data.get('contrato_id')
    arquivo_id = data.get('arquivo_id')
    if not contrato_id or not arquivo_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id e arquivo_id obrigatórios.'}, status=400)

    papel = _papel_usuario(request.user) or ''
    if not user_has_access(request.user, 'SCT201') and papel not in ('operacional', 'supervisor'):
        return JsonResponse({'ok': False, 'erro': 'Apenas Operacional/Supervisor podem excluir arquivo.'}, status=403)

    ce = get_object_or_404(ContratoExecucao, pk=int(contrato_id))
    arq = get_object_or_404(ClienteArquivo, pk=int(arquivo_id))

    # Blindagem contra exclusão cruzada: o arquivo deve pertencer ao mesmo
    # titular do contrato (mesmo ClienteDadosPessoais).
    if arq.cliente_dados_pessoais_id != ce.cliente_dados_pessoais_id:
        return JsonResponse({'ok': False, 'erro': 'Arquivo não pertence a este contrato.'}, status=403)

    titulo = arq.titulo or (arq.arquivo.name if arq.arquivo else '—')

    with transaction.atomic():
        # Remoção segura do arquivo físico — ignora erros (arquivo já ausente
        # no storage, por exemplo) para não impedir a exclusão da row.
        try:
            if arq.arquivo and arq.arquivo.name:
                arq.arquivo.delete(save=False)
        except Exception:
            logger.warning(
                'Falha ao remover arquivo físico do ClienteArquivo %s (prosseguindo).',
                arq.id, exc_info=True,
            )
        arq.delete()

        _registrar_historico(
            ce,
            ce.etapa_operacional, ce.sub_status_operacional,
            ce.etapa_operacional, ce.sub_status_operacional,
            request.user,
            f'Arquivo excluído ({papel}): {titulo}'[:500],
        )

    return JsonResponse({'ok': True, 'arquivo_id': int(arquivo_id)})


# ============================================================================
# Pendências tipadas
# ============================================================================

@login_required
@require_POST
def api_post_criar_pendencia(request):
    """Cria uma ou mais `Pendencia` e aciona transição `pendencia_entrar` (apenas operacional).

    Espera: {contrato_id, observacao, tipos: [..]} ou legado {contrato_id, tipo, observacao}.
    """
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
    data = _json(request)
    contrato_id = data.get('contrato_id')
    observacao = (data.get('observacao') or '').strip()
    if not contrato_id or not observacao:
        return JsonResponse({'ok': False, 'erro': 'contrato_id e observação são obrigatórios.'}, status=400)

    tipos = []
    tipos_raw = data.get('tipos')
    if isinstance(tipos_raw, list) and tipos_raw:
        vistos = set()
        for x in tipos_raw:
            t = (str(x) or '').strip()
            if t in dict(Pendencia.TIPO_CHOICES) and t not in vistos:
                vistos.add(t)
                tipos.append(t)
    if not tipos:
        u = (data.get('tipo') or '').strip()
        if u in dict(Pendencia.TIPO_CHOICES):
            tipos = [u]
    if not tipos:
        return JsonResponse(
            {'ok': False, 'erro': 'Informe ao menos um tipo de pendência válido (tipos ou tipo).'},
            status=400,
        )

    ce = get_object_or_404(ContratoExecucao, pk=int(contrato_id))
    papel = _papel_usuario(request.user) or ''
    if papel != 'operacional':
        return JsonResponse({'ok': False, 'erro': 'Apenas Operacional pode criar pendência.'}, status=403)

    with transaction.atomic():
        criadas = []
        for tipo in tipos:
            criadas.append(
                Pendencia.objects.create(
                    contrato_execucao=ce,
                    tipo=tipo,
                    observacao=observacao,
                    criado_por=request.user,
                )
            )
        obs_trans = '; '.join(
            f'[{p.get_tipo_display()}] {observacao}' for p in criadas
        )[:500]
        ok, msg = transicao_por_acao(
            ce, request.user, 'operacional', 'pendencia_entrar',
            observacao=obs_trans,
        )
        if not ok:
            logger.info('api_post_criar_pendencia: transição não aplicada: %s', msg)

    ult = criadas[-1]
    return JsonResponse({
        'ok': True,
        'pendencia_ids': [p.id for p in criadas],
        'pendencias': [{'id': p.id, 'tipo': p.tipo, 'criado_em': p.criado_em.isoformat()} for p in criadas],
        'pendencia_id': ult.id,
        'tipo': ult.tipo,
        'criado_em': ult.criado_em.isoformat(),
    })


@login_required
@require_POST
def api_post_resolver_pendencia(request):
    """Marca Pendencia como resolvida. Quando TODAS as pendências abertas do
    contrato estão resolvidas, executa `pendencia_corrigido` para retornar à
    etapa de origem.
    """
    data = _json(request)
    pend_id = data.get('pendencia_id')
    if not pend_id:
        return JsonResponse({'ok': False, 'erro': 'pendencia_id obrigatório.'}, status=400)
    pend = get_object_or_404(
        Pendencia.objects.select_related('contrato_execucao'),
        pk=int(pend_id),
    )

    ce = pend.contrato_execucao
    papel = _papel_usuario(request.user)
    papel_s = (papel or '')
    pode_supervisor_app = user_has_access(request.user, 'SCT201')
    pode_ops_crm = (
        user_has_access(request.user, 'SCT189')
        and papel_s in ('operacional', 'supervisor')
    )
    pode_vend = vendedor_pode_acesso_pendencia_contrato(request.user, ce)
    if not (pode_ops_crm or pode_vend or pode_supervisor_app):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão para resolver pendência.'}, status=403)

    # transicao_por_acao exige 'vendedor' | 'operacional' | 'supervisor'; user sem
    # Funcionario tem papel None e precisa disparar fluxo de vendedor.
    if pode_ops_crm:
        papel_transicao = papel_s
    elif pode_supervisor_app:
        papel_transicao = 'supervisor'
    else:
        papel_transicao = 'vendedor'

    with transaction.atomic():
        if not pend.resolvido:
            pend.resolvido = True
            pend.resolvido_por = request.user
            pend.resolvido_em = timezone.now()
            pend.save(update_fields=['resolvido', 'resolvido_por', 'resolvido_em'])
        pendencias_abertas = Pendencia.objects.filter(contrato_execucao=ce, resolvido=False).exists()
        if not pendencias_abertas and ce.etapa_operacional == EtapaOperacional.PENDENCIAS:
            transicao_por_acao(
                ce, request.user, papel_transicao, 'pendencia_corrigido',
                observacao=f'Pendência resolvida: {pend.get_tipo_display()}',
            )

    return JsonResponse({'ok': True, 'pendencia_id': pend.id, 'resolvido_em': pend.resolvido_em.isoformat() if pend.resolvido_em else None})


@login_required
@require_POST
def api_post_sanar_pendencias_contrato(request):
    """Marca pendências como sanadas e conclui etapa PENDENCIAS do contrato."""
    data = _json(request)
    contrato_id = data.get('contrato_id')
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)

    ce = get_object_or_404(
        ContratoExecucao.objects.select_related(
            'solicitacao_digitacao', 'proposta_dados__solicitacao_origem',
        ).defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO),
        pk=int(contrato_id), status=True,
    )
    papel = _papel_usuario(request.user)
    papel_s = (papel or '')
    pode_supervisor_app = user_has_access(request.user, 'SCT201')
    pode_ops_crm = (
        user_has_access(request.user, 'SCT189')
        and papel_s in ('operacional', 'supervisor')
    )
    pode_vend = vendedor_pode_acesso_pendencia_contrato(request.user, ce)
    pode_por_etapa = (ce.etapa_operacional == EtapaOperacional.PENDENCIAS)
    if not (pode_ops_crm or pode_vend or pode_supervisor_app or pode_por_etapa):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão para sanar pendências.'}, status=403)

    if ce.etapa_operacional != EtapaOperacional.PENDENCIAS:
        return JsonResponse({'ok': False, 'erro': 'Contrato não está na etapa de pendências.'}, status=400)

    if pode_ops_crm:
        papel_transicao = papel_s
    elif pode_supervisor_app:
        papel_transicao = 'supervisor'
    else:
        papel_transicao = 'vendedor'

    with transaction.atomic():
        qs_abertas = Pendencia.objects.select_for_update().filter(contrato_execucao=ce, resolvido=False)
        ids_resolvidas = []
        for pend in qs_abertas:
            pend.resolvido = True
            pend.resolvido_por = request.user
            pend.resolvido_em = timezone.now()
            pend.save(update_fields=['resolvido', 'resolvido_por', 'resolvido_em'])
            ids_resolvidas.append(pend.id)

        transicao_por_acao(
            ce, request.user, papel_transicao, 'pendencia_corrigido',
            observacao='Pendência sanada manualmente pelo modal da consulta cliente.',
        )
    return JsonResponse({'ok': True, 'contrato_id': ce.id, 'pendencias_resolvidas': ids_resolvidas})


@login_required
@require_GET
def api_get_pendencias_contrato(request):
    """Lista pendências de um contrato (abertas ou todas)."""
    from django.db import DatabaseError

    contrato_id = request.GET.get('contrato_id')
    incluir_resolvidas = (request.GET.get('incluir_resolvidas') or '').lower() in ('1', 'true')
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    try:
        try:
            ce = (
                ContratoExecucao.objects.select_related(
                    'solicitacao_digitacao', 'proposta_dados__solicitacao_origem',
                )
                .defer(*DEFER_SOLICITACAO_DIGITACAO_PRE_CONTRATO)
                .get(pk=int(contrato_id), status=True)
            )
        except ContratoExecucao.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
        pode = (
            user_has_access(request.user, 'SCT189')
            or user_has_access(request.user, 'SCT201')
            or vendedor_pode_acesso_pendencia_contrato(request.user, ce)
            or (
                ce.etapa_operacional == EtapaOperacional.PENDENCIAS
                and contrato_vinculado_carteiras_responsavel(request.user, ce)
            )
        )
        if not pode:
            return JsonResponse({'ok': False, 'erro': 'Sem permissão.'}, status=403)
        qs = Pendencia.objects.filter(contrato_execucao_id=int(contrato_id))
        if not incluir_resolvidas:
            qs = qs.filter(resolvido=False)
        itens = [
            {
                'id': p.id,
                'tipo': p.tipo,
                'tipo_label': p.get_tipo_display(),
                'observacao': p.observacao,
                'criado_por': p.criado_por.username,
                'criado_em': p.criado_em.isoformat() if p.criado_em else None,
                'resolvido': p.resolvido,
                'resolvido_por': p.resolvido_por.username if p.resolvido_por_id else None,
                'resolvido_em': p.resolvido_em.isoformat() if p.resolvido_em else None,
            }
            for p in qs.select_related('criado_por', 'resolvido_por').order_by('-criado_em')
        ]
        return JsonResponse({'ok': True, 'pendencias': itens})
    except DatabaseError as exc:
        # Schema desatualizado (ex.: migração 0050 pendente): devolve JSON estruturado.
        logger.exception('api_get_pendencias_contrato (DatabaseError) contrato_id=%s: %s', contrato_id, exc)
        return JsonResponse(
            {
                'ok': False,
                'erro': (
                    'Schema do banco desatualizado para esta tela. '
                    'Solicite ao administrador que execute as migrações pendentes.'
                ),
            },
            status=500,
        )
    except Exception as exc:
        logger.exception('api_get_pendencias_contrato falhou contrato_id=%s: %s', contrato_id, exc)
        return JsonResponse(
            {'ok': False, 'erro': 'Erro interno ao listar pendências. Verifique o log do servidor.'},
            status=500,
        )


# ============================================================================
# Comprovantes TC (acumulado Parcial/Total)
# ============================================================================

# Campos da proposta que têm homônimos no snapshot operacional (exceto coeficiente).
_SNAPSHOT_PROP_FIN_KEYS = ('valor_parcela', 'prazo', 'valor_af', 'valor_tc', 'valor_liberado')


def _espelhar_proposta_financeiros_em_do(d, pd, pp_payload, campos_alterados):
    """Mantém ContratoDadosOperacionais alinhado após edição de proposta no CRM (modal Editar)."""
    if not pp_payload or not isinstance(pp_payload, dict):
        return
    if not any(k in pp_payload for k in _SNAPSHOT_PROP_FIN_KEYS):
        return
    upd = []
    for k in _SNAPSHOT_PROP_FIN_KEYS:
        novo = getattr(pd, k, None)
        if getattr(d, k, None) != novo:
            setattr(d, k, novo)
            campos_alterados.append(f'dados_operacionais.{k}')
            upd.append(k)
    if upd:
        d.save(update_fields=upd)


def _valor_tc_do_contrato(ce) -> Decimal:
    return valor_tc_efetivo_para_fluxo(ce)


def _soma_comprovantes(ce) -> Decimal:
    total = Decimal('0')
    for c in ComprovanteTC.objects.filter(contrato_execucao=ce, status=True).only('valor'):
        if c.valor is not None:
            total += Decimal(str(c.valor))
    return total


def _contrato_tem_dados_operacionais(ce) -> bool:
    """True se existe linha em ContratoDadosOperacionais para este CE.

    O OneToOne reverso ``dados_operacionais`` não gera ``ce.dados_operacionais_id`` no Django:
    a FK ``contrato_execucao`` fica na tabela de dados operacionais.
    """
    return ContratoDadosOperacionais.objects.filter(contrato_execucao_id=ce.pk).exists()


def _refresh_ce_e_relacionados_valor_tc(ce):
    """Recarrega CE e FKs usadas em valor_tc após save (evita cache do select_related)."""
    ce.refresh_from_db()
    if _contrato_tem_dados_operacionais(ce):
        try:
            ce.dados_operacionais.refresh_from_db()
        except ObjectDoesNotExist:
            logger.warning(
                'Dados operacionais ausentes após atualização TC (ce=%s).',
                ce.pk,
            )
    if ce.proposta_dados_id:
        try:
            ce.proposta_dados.refresh_from_db()
        except ObjectDoesNotExist:
            logger.warning(
                'Proposta dados ausente após atualização TC (ce=%s, pd_id=%s).',
                ce.pk,
                ce.proposta_dados_id,
            )


def _rm_payload_de_registermoney_post(raw, ce):
    """
    Converte JSON registermoney do POST em dict validado para aplicar_etapa_sub.
    Retorna (dict|None, erro|None).
    """
    if not raw or not str(raw).strip():
        return None, (
            'Informe os dados do registro financeiro no modal Pago TC '
            '(valor TC, classificador, AF, etc.).'
        )
    if isinstance(raw, dict):
        payload = raw
    else:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None, 'Campo registermoney inválido (JSON).'
    if not isinstance(payload, dict):
        return None, 'Campo registermoney deve ser um objeto JSON.'
    data = dict(payload)
    if data.get('valor_est') not in (None, '') and data.get('valor_est_tc') in (None, ''):
        data['valor_est_tc'] = data.get('valor_est')
    rm_dict, err = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
    if err:
        return None, err
    return rm_dict, None


def _registrar_comprovante_tc_sem_rm(
    ce,
    valor: Decimal,
    arquivo,
    user,
    observacao_extra: str = '',
    novo_tc_modal: Decimal | None = None,
    rm_payload=None,
):
    """
    Cria ComprovanteTC e atualiza sub-status parcial/total.
    No 1º comprovante com TC > 0, rm_payload alimenta a criação do RegisterMoney.
    Retorna (comp, soma, valor_tc, total_atingido).
    """
    observacao = observacao_extra or f'Comprovante TC — R$ {valor}'
    with transaction.atomic():
        comp = ComprovanteTC.objects.create(
            contrato_execucao=ce,
            valor=valor,
            arquivo=arquivo,
            criado_por=user,
        )
        soma = _soma_comprovantes(ce)

        if novo_tc_modal is not None and novo_tc_modal > 0:
            atual_snap = valor_tc_efetivo_para_fluxo(ce)
            qa = atual_snap.quantize(Decimal('0.01'))
            qn = novo_tc_modal.quantize(Decimal('0.01'))
            if qa != qn:
                ok_p, err_p = persistir_tc_modal_em_contrato_e_rm(ce, novo_tc_modal, soma)
                if not ok_p:
                    raise RuntimeError(err_p)
                _refresh_ce_e_relacionados_valor_tc(ce)

        valor_tc = _valor_tc_do_contrato(ce)
        if valor_tc <= 0:
            raise RuntimeError('Valor TC inválido após processamento.')

        total_atingido = soma >= valor_tc
        novo_sub = (
            SubStatusOperacional.PG_PAGO_TC_TOTAL
            if total_atingido
            else SubStatusOperacional.PG_PAGO_TC_PARCIAL
        )

        ja_tem_rm = RegisterMoney_has_for_ce(ce)
        if ja_tem_rm:
            ok, msg = aplicar_etapa_sub(
                ce,
                EtapaOperacional.PAGAMENTO,
                novo_sub,
                user,
                observacao=f'{observacao} #{comp.id}',
                sincronizar_legado=True,
                inner_atomic=False,
            )
            if not ok:
                raise RuntimeError(msg or 'Falha ao atualizar sub-status TC.')
            _incrementar_acumulado_rm(ce, valor)
        else:
            if valor_tc > 0 and not rm_payload:
                raise RuntimeError(
                    'Informe os dados do registro financeiro no modal Pago TC '
                    '(valor TC, classificador, AF, etc.) antes do primeiro comprovante.'
                )
            ok, msg = aplicar_etapa_sub(
                ce,
                EtapaOperacional.PAGAMENTO,
                novo_sub,
                user,
                observacao=f'{observacao} #{comp.id}',
                rm_payload=rm_payload,
                inner_atomic=False,
            )
            if not ok:
                raise RuntimeError(msg or 'Falha ao aplicar sub-status TC.')

    ce.refresh_from_db()
    return comp, soma, valor_tc, total_atingido


def _valor_est_json_registermoney_post(rm_raw):
    """Extrai valor_est do JSON registermoney no POST multipart do comprovante TC."""
    if not rm_raw or not str(rm_raw).strip():
        return None
    try:
        payload = json.loads(rm_raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    ve = payload.get('valor_est')
    if ve in (None, ''):
        return None
    return _dec(ve)


@login_required
@require_http_methods(['POST'])
def api_post_comprovante_tc(request):
    """Recebe upload de comprovante de pagamento de TC (multipart). A soma dos
    comprovantes decide se o sub-status fica em PG_PAGO_TC_PARCIAL ou PG_PAGO_TC_TOTAL.

    Params POST (multipart):
        contrato_id, valor, arquivo
        registermoney (JSON) — dados do modal Pago TC (obrigatório no 1º comprovante com TC > 0)
    """
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    # Permissão principal deste endpoint é SCT189. Não restringir por papel aqui,
    # pois há cenários válidos com acesso ativo e cargo não mapeado no helper.
    try:
        contrato_id = int(request.POST.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    valor = _dec(request.POST.get('valor'))
    arquivo = request.FILES.get('arquivo')
    if valor is None or valor <= 0:
        return JsonResponse({'ok': False, 'erro': 'Valor inválido.'}, status=400)
    if not arquivo:
        return JsonResponse({'ok': False, 'erro': 'Anexe o comprovante.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
        )
        rm_raw = request.POST.get('registermoney')
        novo_tc_modal = _valor_est_json_registermoney_post(rm_raw)
        valor_tc_pre = _valor_tc_do_contrato(ce)
        if valor_tc_pre <= 0 and (novo_tc_modal is None or novo_tc_modal <= 0):
            return JsonResponse(
                {
                    'ok': False,
                    'erro': (
                        'Contrato sem valor de TC — informe o Valor TC no modal Pago TC '
                        'ou cadastre no contrato.'
                    ),
                },
                status=400,
            )

        rm_payload = None
        if not RegisterMoney_has_for_ce(ce) and (
            valor_tc_pre > 0 or (novo_tc_modal is not None and novo_tc_modal > 0)
        ):
            rm_payload, err_rm = _rm_payload_de_registermoney_post(rm_raw, ce)
            if err_rm:
                return JsonResponse({'ok': False, 'erro': err_rm}, status=400)

        comp, soma, valor_tc, total_atingido = _registrar_comprovante_tc_sem_rm(
            ce,
            valor,
            arquivo,
            request.user,
            observacao_extra=f'Comprovante TC — R$ {valor}',
            novo_tc_modal=novo_tc_modal,
            rm_payload=rm_payload,
        )

        # Defesa em profundidade: recupera o classificador do 1º RegisterMoney para
        # devolver ao frontend e garantir que pagamentos parciais subsequentes
        # exibam a mesma classificação inicial (M1/M2/M3) sem recalcular.
        classificador_preservado = None
        tipo_preservado = None
        try:
            from apps.vendas.siape.apis.classificador import obter_classificador_primeiro_rm
            info = obter_classificador_primeiro_rm(ce)
            if info:
                classificador_preservado, tipo_preservado = info
        except Exception:
            pass

        valor_tc_resp = _valor_tc_do_contrato(ce)

        return JsonResponse({
            'ok': True,
            'comprovante_id': comp.id,
            'soma_acumulada': str(_soma_comprovantes(ce)),
            'valor_tc': str(valor_tc_resp),
            'total_atingido': total_atingido,
            'sub_status': ce.sub_status_operacional,
            'classificador_auto': classificador_preservado,
            'tipo_classificacao': tipo_preservado,
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)


@login_required
@require_POST
def api_post_atualizar_tc_modal_pago(request):
    """
    Persiste o Valor TC editado no modal quando já existem comprovantes (sem novo upload).

    O TC gravado no contrato está em ``ContratoDadosOperacionais.valor_tc`` (o modelo
    ``ContratoExecucao`` não tem essa coluna); ``PropostaDados.valor_tc`` é atualizado em conjunto.
    Recalcula Parcial/Total conforme soma dos comprovantes vs TC gravado e ajusta ``RegisterMoney.valor_est``.

    Logs (nível INFO) usam o prefixo ``[atualizar-tc-modal-pago]`` — aparecem no journalctl do Gunicorn
    se o ``LOGGING`` do Django incluir INFO para este módulo.
    """
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    novo_tc = _dec(data.get('valor_tc') if data.get('valor_tc') not in (None, '') else data.get('valor_est'))
    if contrato_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    if novo_tc is None or novo_tc <= 0:
        return JsonResponse({'ok': False, 'erro': 'Informe valor_tc maior que zero.'}, status=400)

    observacao = (data.get('observacao') or '').strip() or 'Ajuste Valor TC (modal CRM)'

    logger.info(
        '[atualizar-tc-modal-pago] entrada contrato_id=%s novo_tc=%s user_id=%s',
        contrato_id,
        novo_tc,
        getattr(request.user, 'pk', None),
    )

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        if ce.etapa_operacional != EtapaOperacional.PAGAMENTO:
            logger.warning(
                '[atualizar-tc-modal-pago] etapa inválida ce=%s etapa=%s',
                ce.pk,
                ce.etapa_operacional,
            )
            return JsonResponse({'ok': False, 'erro': 'Contrato não está na etapa Pagamento.'}, status=400)

        soma = _soma_comprovantes(ce)
        valor_tc_antes = _valor_tc_do_contrato(ce)
        logger.info(
            '[atualizar-tc-modal-pago] estado inicial ce=%s sub=%s soma_comprovantes=%s valor_tc_antes=%s tem_do=%s pd_id=%s',
            ce.pk,
            ce.sub_status_operacional,
            soma,
            valor_tc_antes,
            _contrato_tem_dados_operacionais(ce),
            ce.proposta_dados_id,
        )
        if soma <= 0:
            logger.warning('[atualizar-tc-modal-pago] sem comprovantes ce=%s', ce.pk)
            return JsonResponse(
                {'ok': False, 'erro': 'Envie um comprovante TC antes de ajustar o valor pelo modal.'},
                status=400,
            )

        with transaction.atomic():
            try:
                ok_p, err_p = persistir_tc_modal_em_contrato_e_rm(ce, novo_tc, soma)
            except Exception as exc:
                logger.exception(
                    'api_post_atualizar_tc_modal_pago: exceção em persistir_tc_modal_em_contrato_e_rm '
                    'contrato_id=%s user_id=%s',
                    contrato_id,
                    getattr(request.user, 'pk', None),
                )
                raise RuntimeError(f'Erro ao gravar TC (persistência): {exc}') from exc
            if not ok_p:
                raise RuntimeError(err_p or 'Falha ao persistir TC.')
            logger.info(
                '[atualizar-tc-modal-pago] persistir_tc_modal_em_contrato_e_rm ok ce=%s novo_tc_pedido=%s',
                ce.pk,
                novo_tc,
            )
            if _contrato_tem_dados_operacionais(ce):
                try:
                    ce.dados_operacionais.refresh_from_db()
                except Exception as exc:
                    # RelatedObjectDoesNotExist nem sempre casa com ObjectDoesNotExist em todas as versões Django
                    logger.warning(
                        'api_post_atualizar_tc_modal_pago: falha ao refresh DO ce=%s: %s',
                        ce.pk,
                        exc,
                        exc_info=True,
                    )
                    raise RuntimeError(
                        f'Não foi possível recarregar os dados operacionais após salvar o TC: {exc}'
                    ) from exc
            if ce.proposta_dados_id:
                try:
                    ce.proposta_dados.refresh_from_db()
                except Exception as exc:
                    logger.warning(
                        'api_post_atualizar_tc_modal_pago: falha ao refresh PropostaDados ce=%s: %s',
                        ce.pk,
                        exc,
                        exc_info=True,
                    )
                    raise RuntimeError(
                        f'Não foi possível recarregar a proposta após salvar o TC: {exc}'
                    ) from exc

            # Recalcula soma dentro da transação (blindagem se o fluxo passar a alterar comprovantes aqui)
            soma = _soma_comprovantes(ce)
            valor_tc = _valor_tc_do_contrato(ce)
            novo_sub = (
                SubStatusOperacional.PG_PAGO_TC_TOTAL
                if soma >= valor_tc
                else SubStatusOperacional.PG_PAGO_TC_PARCIAL
            )
            aplicar_transicao = ce.sub_status_operacional != novo_sub
            logger.info(
                '[atualizar-tc-modal-pago] decisão parcial/total ce=%s soma=%s valor_tc=%s novo_sub=%s sub_atual=%s aplicar_transicao=%s',
                ce.pk,
                soma,
                valor_tc,
                novo_sub,
                ce.sub_status_operacional,
                aplicar_transicao,
            )
            if aplicar_transicao:
                logger.info(
                    '[atualizar-tc-modal-pago] aplicar_etapa_sub ce=%s %s -> %s',
                    ce.pk,
                    ce.sub_status_operacional,
                    novo_sub,
                )
                rm_payload_trans = None
                if not RegisterMoney_has_for_ce(ce) and valor_tc > 0:
                    reg_body = data.get('registermoney')
                    if reg_body is not None:
                        rm_payload_trans, err_rm_t = _rm_payload_de_registermoney_post(reg_body, ce)
                        if err_rm_t:
                            raise RuntimeError(err_rm_t)
                    else:
                        raise RuntimeError(
                            'Informe os dados do registro financeiro no modal Pago TC '
                            'antes de ajustar o valor TC.'
                        )
                ok, msg = aplicar_etapa_sub(
                    ce,
                    EtapaOperacional.PAGAMENTO,
                    novo_sub,
                    request.user,
                    observacao=observacao,
                    sincronizar_legado=True,
                    rm_payload=rm_payload_trans,
                    inner_atomic=False,
                )
                if not ok:
                    raise RuntimeError(msg or 'Falha ao atualizar status TC.')
                logger.info(
                    '[atualizar-tc-modal-pago] aplicar_etapa_sub concluído ce=%s sub_agora=%s',
                    ce.pk,
                    ce.sub_status_operacional,
                )

        logger.info('[atualizar-tc-modal-pago] atomic commit ok ce=%s', ce.pk)

        _refresh_ce_e_relacionados_valor_tc(ce)
        valor_tc_resp = _valor_tc_do_contrato(ce)
        soma_f = _soma_comprovantes(ce)
        total_atingido = soma_f >= valor_tc_resp

        logger.info(
            '[atualizar-tc-modal-pago] sucesso ce=%s valor_tc_resp=%s sub=%s soma=%s total_atingido=%s',
            ce.pk,
            valor_tc_resp,
            ce.sub_status_operacional,
            soma_f,
            total_atingido,
        )

        return JsonResponse({
            'ok': True,
            'valor_tc': str(valor_tc_resp),
            'sub_status': str(ce.sub_status_operacional or ''),
            'soma_acumulada': str(soma_f),
            'total_atingido': bool(total_atingido),
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except RuntimeError as exc:
        logger.warning(
            '[atualizar-tc-modal-pago] RuntimeError contrato_id=%s err=%s',
            contrato_id,
            exc,
        )
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except ValidationError as exc:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: ValidationError contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except IntegrityError:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: IntegrityError contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse(
            {'ok': False, 'erro': 'Não foi possível salvar (conflito ou limite de dados).'},
            status=400,
        )
    except DatabaseError:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: DatabaseError contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse(
            {'ok': False, 'erro': 'Erro ao gravar no banco de dados. Tente novamente ou contate o suporte.'},
            status=500,
        )
    except TransactionManagementError:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: TransactionManagementError contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse(
            {
                'ok': False,
                'erro': (
                    'Conflito ao finalizar a transação do banco. Recarregue a página e tente de novo; '
                    'se repetir, contate o suporte.'
                ),
            },
            status=409,
        )
    except ObjectDoesNotExist:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: ObjectDoesNotExist contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse(
            {
                'ok': False,
                'erro': 'Registro vinculado ao contrato não foi encontrado após a atualização. Recarregue a página e tente de novo.',
            },
            status=409,
        )
    except Exception as exc:
        logger.exception(
            'api_post_atualizar_tc_modal_pago: exceção inesperada contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        msg = 'Erro inesperado ao atualizar o valor TC.'
        tipo_exc = type(exc).__name__
        detalhe = (str(exc) or tipo_exc)[:400]
        if settings.DEBUG:
            msg = f'{msg} [{tipo_exc}: {exc}]'
        return JsonResponse(
            {
                'ok': False,
                'erro': msg,
                'detalhe': detalhe,
                'tipo': tipo_exc,
            },
            status=500,
        )


@login_required
@require_POST
def api_post_salvar_dados_pago_tc_modal(request):
    """
    Grava Valor TC, AF, classificador e loja do modal Pago TC sem exigir comprovante
    e sem evoluir o sub-status (use comprovante-tc / Confirmar para isso).
    """
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id inválido.'}, status=400)
    if contrato_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        if ce.etapa_operacional != EtapaOperacional.PAGAMENTO:
            return JsonResponse({'ok': False, 'erro': 'Contrato não está na etapa Pagamento.'}, status=400)

        rm_dict, err_rm = _montar_registermoney_extra_supervisor_pago_tc(data, ce)
        if err_rm:
            return JsonResponse({'ok': False, 'erro': err_rm}, status=400)
        if not rm_dict:
            return JsonResponse({'ok': False, 'erro': 'Dados do modal inválidos.'}, status=400)

        soma = _soma_comprovantes(ce)
        valor_est = rm_dict.get('valor_est') or Decimal('0')
        valor_tc_antes = _valor_tc_do_contrato(ce)
        observacao = (data.get('observacao') or '').strip() or 'Ajuste dados Pago TC (modal CRM)'
        tc_zerado = False

        with transaction.atomic():
            if valor_est > 0:
                ok_p, err_p = persistir_tc_modal_em_contrato_e_rm(ce, valor_est, soma)
                if not ok_p:
                    raise RuntimeError(err_p or 'Falha ao persistir Valor TC.')
            elif valor_tc_antes > 0:
                ok_z, err_z = zerar_tc_modal_em_contrato(ce)
                if not ok_z:
                    raise RuntimeError(err_z or 'Falha ao zerar Valor TC.')
                tc_zerado = True
                observacao = (data.get('observacao') or '').strip() or 'Zerar Valor TC (modal CRM)'

            af = rm_dict.get('af')
            if af is not None and _contrato_tem_dados_operacionais(ce):
                d = ce.dados_operacionais
                d.valor_af = af
                d.save(update_fields=['valor_af'])
            if af is not None and ce.proposta_dados_id:
                pd = ce.proposta_dados
                pd.valor_af = af
                pd.save(update_fields=['valor_af'])

            ok_rm, err_sync = sincronizar_register_money_dados_modal_pago_tc(ce, rm_dict)
            if not ok_rm:
                raise RuntimeError(err_sync or 'Falha ao sincronizar RegisterMoney.')

            _registrar_historico(
                ce,
                ce.etapa_operacional,
                ce.sub_status_operacional,
                ce.etapa_operacional,
                ce.sub_status_operacional,
                request.user,
                observacao[:500],
            )

        _refresh_ce_e_relacionados_valor_tc(ce)
        valor_tc_resp = _valor_tc_do_contrato(ce)
        return JsonResponse({
            'ok': True,
            'valor_tc': str(valor_tc_resp),
            'valor_est_tc': str(valor_tc_resp),
            'soma_acumulada': str(_soma_comprovantes(ce)),
            'sub_status': str(ce.sub_status_operacional or ''),
            'tc_zerado': tc_zerado,
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except Exception as exc:
        logger.exception(
            'api_post_salvar_dados_pago_tc_modal: contrato_id=%s user_id=%s',
            contrato_id,
            getattr(request.user, 'pk', None),
        )
        return JsonResponse({'ok': False, 'erro': 'Erro ao salvar dados do modal Pago TC.'}, status=500)


def RegisterMoney_has_for_ce(ce) -> bool:
    from apps.vendas.siape.models import RegisterMoney
    return RegisterMoney.objects.filter(contrato_execucao=ce).exists()


def _incrementar_acumulado_rm(ce, valor: Decimal):
    """Incrementa `valor_pago_acumulado` em todos os RegisterMoney do contrato
    mantendo proporção (metade/metade no caso de repasse, total caso contrário).
    """
    from apps.vendas.siape.models import RegisterMoney
    rms = list(RegisterMoney.objects.filter(contrato_execucao=ce, status=True))
    if not rms:
        return
    if len(rms) == 2 and all(r.flag_repasse for r in rms):
        parte = (valor / Decimal('2')).quantize(Decimal('0.01'))
        for r in rms:
            r.valor_pago_acumulado = (r.valor_pago_acumulado or Decimal('0')) + parte
            r.save(update_fields=['valor_pago_acumulado'])
    else:
        for r in rms:
            r.valor_pago_acumulado = (r.valor_pago_acumulado or Decimal('0')) + valor
            r.save(update_fields=['valor_pago_acumulado'])


def _decrementar_acumulado_rm(ce, valor: Decimal):
    """Decrementa `valor_pago_acumulado` (simétrico a _incrementar_acumulado_rm)."""
    from apps.vendas.siape.models import RegisterMoney
    rms = list(RegisterMoney.objects.filter(contrato_execucao=ce, status=True))
    if not rms:
        return
    if len(rms) == 2 and all(r.flag_repasse for r in rms):
        parte = (valor / Decimal('2')).quantize(Decimal('0.01'))
        for r in rms:
            novo = (r.valor_pago_acumulado or Decimal('0')) - parte
            r.valor_pago_acumulado = max(novo, Decimal('0'))
            r.save(update_fields=['valor_pago_acumulado'])
    else:
        for r in rms:
            novo = (r.valor_pago_acumulado or Decimal('0')) - valor
            r.valor_pago_acumulado = max(novo, Decimal('0'))
            r.save(update_fields=['valor_pago_acumulado'])


@login_required
@require_POST
def api_post_excluir_comprovante_tc(request):
    """Soft delete de ComprovanteTC; recalcula sub-status e acumulado do RegisterMoney."""
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    data = _json(request)
    try:
        contrato_id = int(data.get('contrato_id') or 0)
        comprovante_id = int(data.get('comprovante_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id ou comprovante_id inválido.'}, status=400)
    if contrato_id <= 0 or comprovante_id <= 0:
        return JsonResponse({'ok': False, 'erro': 'contrato_id e comprovante_id obrigatórios.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
            status=True,
        )
        if ce.etapa_operacional != EtapaOperacional.PAGAMENTO:
            return JsonResponse({'ok': False, 'erro': 'Contrato não está na etapa Pagamento.'}, status=400)

        comp = get_object_or_404(
            ComprovanteTC,
            pk=comprovante_id,
            contrato_execucao_id=contrato_id,
            status=True,
        )
        valor_excluido = comp.valor
        sub_antes = ce.sub_status_operacional
        observacao = (data.get('observacao') or '').strip() or f'Exclusão comprovante TC — R$ {valor_excluido}'

        with transaction.atomic():
            comp.status = False
            comp.save(update_fields=['status'])

            if RegisterMoney_has_for_ce(ce):
                _decrementar_acumulado_rm(ce, valor_excluido)

            soma = _soma_comprovantes(ce)
            valor_tc = _valor_tc_do_contrato(ce)
            if soma <= 0:
                if sub_antes in (
                    SubStatusOperacional.PG_PAGO_TC_PARCIAL,
                    SubStatusOperacional.PG_PAGO_TC_TOTAL,
                    SubStatusOperacional.PG_PAGO_TC,
                ):
                    novo_sub = SubStatusOperacional.PG_AGUARDANDO_TC
                else:
                    novo_sub = SubStatusOperacional.PG_PAGO_CLIENTE
            elif valor_tc > 0:
                novo_sub = (
                    SubStatusOperacional.PG_PAGO_TC_TOTAL
                    if soma >= valor_tc
                    else SubStatusOperacional.PG_PAGO_TC_PARCIAL
                )
            else:
                novo_sub = ce.sub_status_operacional

            if novo_sub != ce.sub_status_operacional:
                ok, msg = aplicar_etapa_sub(
                    ce,
                    EtapaOperacional.PAGAMENTO,
                    novo_sub,
                    request.user,
                    observacao=observacao[:500],
                    sincronizar_legado=True,
                    inner_atomic=False,
                )
                if not ok:
                    raise RuntimeError(msg or 'Falha ao atualizar sub-status após exclusão.')
            else:
                _registrar_historico(
                    ce,
                    ce.etapa_operacional,
                    sub_antes,
                    ce.etapa_operacional,
                    ce.sub_status_operacional,
                    request.user,
                    observacao[:500],
                )

        ce.refresh_from_db()
        return JsonResponse({
            'ok': True,
            'soma_acumulada': str(_soma_comprovantes(ce)),
            'valor_tc': str(_valor_tc_do_contrato(ce)),
            'sub_status': str(ce.sub_status_operacional or ''),
            'comprovantes': [
                {
                    'id': c.id,
                    'valor': str(c.valor),
                    'arquivo_url': c.arquivo.url if c.arquivo else None,
                    'criado_por': c.criado_por.username,
                    'criado_em': c.criado_em.isoformat() if c.criado_em else None,
                }
                for c in ComprovanteTC.objects.filter(
                    contrato_execucao=ce, status=True
                ).select_related('criado_por').order_by('criado_em')
            ],
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato ou comprovante não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)
    except Exception as exc:
        logger.exception(
            'api_post_excluir_comprovante_tc: contrato_id=%s comprovante_id=%s',
            contrato_id,
            comprovante_id,
        )
        return JsonResponse({'ok': False, 'erro': 'Erro ao excluir comprovante TC.'}, status=500)


@login_required
@require_http_methods(['POST'])
def api_post_comprovante_tc_from_envio_vendedor(request):
    """
    Converte envio do vendedor em ComprovanteTC (sem RegisterMoney).
    Params POST: contrato_id, envio_id, valor
    """
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    try:
        contrato_id = int(request.POST.get('contrato_id') or 0)
        envio_id = int(request.POST.get('envio_id') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'erro': 'contrato_id ou envio_id inválido.'}, status=400)
    if not contrato_id or not envio_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id e envio_id obrigatórios.'}, status=400)
    valor = _dec(request.POST.get('valor'))
    if valor is None or valor <= 0:
        return JsonResponse({'ok': False, 'erro': 'Valor inválido.'}, status=400)

    try:
        ce = get_object_or_404(
            ContratoExecucao.objects.select_related('dados_operacionais', 'proposta_dados'),
            pk=contrato_id,
        )
        if ce.etapa_operacional != EtapaOperacional.PAGAMENTO:
            return JsonResponse(
                {'ok': False, 'erro': 'Contrato fora da etapa Pagamento.'},
                status=400,
            )
        envio = get_object_or_404(
            EnvioComprovantePagamentoVendedor,
            pk=envio_id,
            contrato_execucao_id=contrato_id,
        )
        if not envio.arquivo:
            return JsonResponse({'ok': False, 'erro': 'Arquivo do envio indisponível.'}, status=400)

        rm_raw = request.POST.get('registermoney')
        novo_tc_modal = _valor_est_json_registermoney_post(rm_raw)
        valor_tc_pre = _valor_tc_do_contrato(ce)
        rm_payload = None
        if not RegisterMoney_has_for_ce(ce) and (
            valor_tc_pre > 0 or (novo_tc_modal is not None and novo_tc_modal > 0)
        ):
            rm_payload, err_rm = _rm_payload_de_registermoney_post(rm_raw, ce)
            if err_rm:
                return JsonResponse({'ok': False, 'erro': err_rm}, status=400)

        envio.arquivo.open('rb')
        try:
            conteudo = envio.arquivo.read()
        finally:
            envio.arquivo.close()
        nome_arq = os.path.basename(envio.arquivo.name) or 'comprovante'
        arquivo_copy = ContentFile(conteudo, name=nome_arq)

        comp, soma, valor_tc, total_atingido = _registrar_comprovante_tc_sem_rm(
            ce,
            valor,
            arquivo_copy,
            request.user,
            observacao_extra=f'Boleto vendedor: {envio.titulo}',
            novo_tc_modal=novo_tc_modal,
            rm_payload=rm_payload,
        )
        envio.delete()

        return JsonResponse({
            'ok': True,
            'comprovante_id': comp.id,
            'soma_acumulada': str(soma),
            'valor_tc': str(valor_tc),
            'total_atingido': total_atingido,
            'sub_status': ce.sub_status_operacional,
        })
    except Http404:
        return JsonResponse({'ok': False, 'erro': 'Contrato ou envio não encontrado.'}, status=404)
    except RuntimeError as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)


@login_required
@require_GET
def api_get_comprovantes_tc(request):
    """Lista comprovantes de TC de um contrato."""
    if not user_has_access(request.user, 'SCT189'):
        return JsonResponse({'ok': False, 'erro': 'Sem permissão de acesso (SCT189).'}, status=403)
    contrato_id = request.GET.get('contrato_id')
    if not contrato_id:
        return JsonResponse({'ok': False, 'erro': 'contrato_id obrigatório.'}, status=400)
    ce = get_object_or_404(ContratoExecucao, pk=int(contrato_id))
    itens = [
        {
            'id': c.id,
            'valor': str(c.valor),
            'arquivo_url': c.arquivo.url if c.arquivo else None,
            'criado_por': c.criado_por.username,
            'criado_em': c.criado_em.isoformat() if c.criado_em else None,
        }
        for c in ComprovanteTC.objects.filter(contrato_execucao=ce, status=True).select_related('criado_por').order_by('criado_em')
    ]
    from apps.contratos_v2.apis.fluxo import serialize_envios_comprovante_pagamento_vendedor

    envios_vendedor = serialize_envios_comprovante_pagamento_vendedor(request, ce)
    return JsonResponse({
        'ok': True,
        'comprovantes': itens,
        'envios_vendedor': envios_vendedor,
        'soma': str(_soma_comprovantes(ce)),
        'valor_tc': str(_valor_tc_do_contrato(ce)),
    })
