from unittest import TestCase

from acaht_balance.achat_balance.calculations import calculate_loan_line, calculate_supplier_settlement


class TestLoanCalculations(TestCase):
	def test_calculates_remaining_and_deposit(self):
		result = calculate_loan_line(100, returned=70, lost=5, damaged=3, deposit_rate=2.5)
		self.assertEqual(str(result["remaining"]), "22.000")
		self.assertEqual(str(result["deposit_amount"]), "250.00")

	def test_rejects_over_return(self):
		with self.assertRaises(ValueError):
			calculate_loan_line(10, returned=8, lost=3)

	def test_rejects_non_positive_loan(self):
		with self.assertRaises(ValueError):
			calculate_loan_line(0)

	def test_deducts_material_from_supplier_debt(self):
		result = calculate_supplier_settlement(50000, 10 * 1000)
		self.assertEqual(str(result["net_payable"]), "40000.00")

	def test_negative_net_means_supplier_owes_company(self):
		result = calculate_supplier_settlement(5000, 10000)
		self.assertEqual(str(result["net_payable"]), "-5000.00")

	def test_paid_deposit_reduces_material_retention(self):
		result = calculate_supplier_settlement(150000, 10000, 4000)
		self.assertEqual(str(result["material_retention"]), "6000.00")
		self.assertEqual(str(result["net_payable"]), "144000.00")
