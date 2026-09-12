from unittest import TestCase

from acaht_balance.achat_balance.calculations import calculate_customer_payment, calculate_sale_total


class TestVenteHuilerieCalculations(TestCase):
	def test_calculates_sale_total(self):
		self.assertEqual(str(calculate_sale_total([(10, 1500), (4, 2500)])), "25000.00")

	def test_calculates_partial_customer_payment(self):
		result = calculate_customer_payment(25000, 10000)
		self.assertEqual(str(result["remaining"]), "15000.00")

	def test_rejects_payment_above_invoice_balance(self):
		with self.assertRaises(ValueError):
			calculate_customer_payment(25000, 26000)
