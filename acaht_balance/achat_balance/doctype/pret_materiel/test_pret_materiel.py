from unittest import TestCase

from acaht_balance.achat_balance.calculations import calculate_loan_line


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
