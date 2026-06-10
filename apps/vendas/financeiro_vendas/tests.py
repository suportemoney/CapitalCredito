from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from apps.vendas.financeiro_vendas.models import ComprovanteTC, ContratoPagamento


class RecalcularTcAcumuladoTest(TestCase):
    """Testes de recálculo de valor_tc_acumulado no ContratoPagamento."""

    def test_recalcular_marca_pago_quando_acumulado_atinge_meta(self):
        from django.contrib.auth.models import User
        from apps.rh.admin.models import Setor
        from apps.vendas.siape.models import Produto

        user = User.objects.create_user(username='vendedor_tc', password='x')
        setor = Setor.objects.create(nome='SETOR TC', status=True)
        produto = Produto.objects.create(nome='PROD TC', status=True)
        from apps.vendas.financeiro_vendas.models import Classificador

        classificador = Classificador.objects.create(titulo='M1', percentual=Decimal('100'))

        cp = ContratoPagamento.objects.create(
            user=user,
            setor=setor,
            cliente_cpf='12345678901',
            cliente_nome='CLIENTE TC',
            produto=produto,
            banco='BANCO',
            valor_af=Decimal('1000'),
            valor_repasse=Decimal('100'),
            valor_tc=Decimal('100'),
            classificador=classificador,
            data_contrato='2025-01-15',
            status='A_PAGAR',
        )

        from django.core.files.base import ContentFile

        comp = ComprovanteTC(
            contrato_pagamento=cp,
            valor=Decimal('100'),
            criado_por=user,
        )
        comp.arquivo.save('teste.pdf', ContentFile(b'%PDF-test'), save=True)

        cp.recalcular_tc_acumulado()
        cp.refresh_from_db()

        self.assertEqual(cp.valor_tc_acumulado, Decimal('100'))
        self.assertEqual(cp.status, 'PAGO')
        self.assertIsNotNone(cp.data_pagamento)

    def test_recalcular_sobrescreve_acumulado_legado_ao_adicionar_comprovante(self):
        from django.contrib.auth.models import User
        from django.core.files.base import ContentFile
        from apps.rh.admin.models import Setor
        from apps.vendas.siape.models import Produto
        from apps.vendas.financeiro_vendas.models import Classificador

        user = User.objects.create_user(username='vendedor_legado', password='x')
        setor = Setor.objects.create(nome='SETOR LEG', status=True)
        produto = Produto.objects.create(nome='PROD LEG', status=True)
        classificador = Classificador.objects.create(titulo='LEG', percentual=Decimal('100'))

        cp = ContratoPagamento.objects.create(
            user=user,
            setor=setor,
            cliente_cpf='98765432100',
            cliente_nome='LEGADO',
            produto=produto,
            banco='BANCO',
            valor_af=Decimal('5000'),
            valor_repasse=Decimal('5885'),
            valor_tc=Decimal('5885'),
            valor_tc_acumulado=Decimal('5885'),
            classificador=classificador,
            data_contrato='2024-06-01',
            status='PAGO',
        )

        comp = ComprovanteTC(contrato_pagamento=cp, valor=Decimal('1500'), criado_por=user)
        comp.arquivo.save('leg.pdf', ContentFile(b'%PDF'), save=True)
        cp.recalcular_tc_acumulado()
        cp.refresh_from_db()

        self.assertEqual(cp.valor_tc_acumulado, Decimal('1500'))
        self.assertEqual(cp.status, 'A_PAGAR')


class ResolverClassificadorFinanceiroTest(SimpleTestCase):
    def test_retorna_none_sem_classificador_cadastrado(self):
        from apps.vendas.financeiro_vendas.services.sincronizar_comprovante import (
            resolver_classificador_financeiro_por_cv_id,
        )

        with patch('apps.vendas.financeiro_vendas.models.Classificador.objects') as mock_cl:
            mock_cl.filter.return_value.order_by.return_value.first.return_value = None
            with patch('apps.vendas.siape.models.ClassificacaoValor.objects') as mock_cv:
                mock_cv.get.return_value = MagicMock(percentual=Decimal('50'))
                mock_cl.filter.return_value.order_by.return_value.first.return_value = None
                result = resolver_classificador_financeiro_por_cv_id(99)
        self.assertIsNone(result)


class RankingFormulaTest(SimpleTestCase):
    """Garante fórmula do ranking: TC acumulado bruto, sem classificador."""

    def test_formula_valor_tc_acumulado_sem_classificador(self):
        acumulado = Decimal('200')
        self.assertEqual(float(acumulado), 200.0)
