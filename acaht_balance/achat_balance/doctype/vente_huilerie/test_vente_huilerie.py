from unittest import TestCase

from acaht_balance.achat_balance.calculations import (
	allocate_customer_payment, calculate_customer_payment, calculate_sale_total,
)


class TestVenteHuilerieCalculations(TestCase):
	def test_calculates_sale_total(self):
		self.assertEqual(str(calculate_sale_total([(10, 1500), (4, 2500)])), "25000.00")

	def test_calculates_partial_customer_payment(self):
		result = calculate_customer_payment(25000, 10000)
		self.assertEqual(str(result["remaining"]), "15000.00")

	def test_rejects_payment_above_invoice_balance(self):
		with self.assertRaises(ValueError):
			calculate_customer_payment(25000, 26000)

	def test_allocates_payment_to_oldest_invoices(self):
		allocations = allocate_customer_payment([10000, 15000, 5000], 18000)
		self.assertEqual([str(value) for value in allocations], ["10000.00", "8000.00", "0.00"])

	def test_rejects_global_overpayment(self):
		with self.assertRaises(ValueError):
			allocate_customer_payment([10000, 15000], 26000)
