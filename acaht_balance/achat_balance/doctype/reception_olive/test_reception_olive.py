from unittest import TestCase

from acaht_balance.achat_balance.calculations import calculate_packaging_tare, calculate_reception


class TestReceptionCalculations(TestCase):
	def test_calculates_weight_amount_and_balance(self):
		result = calculate_reception(1000, 200, 20, 5, 1.5, 100, 250)
		self.assertEqual(str(result["net_weight"]), "780.000")
		self.assertEqual(str(result["payable_weight"]), "741.000")
		self.assertEqual(str(result["amount"]), "1111.50")
		self.assertEqual(str(result["new_balance"]), "961.50")

	def test_rejects_incoherent_weights(self):
		with self.assertRaises(ValueError):
			calculate_reception(100, 120)

	def test_rejects_invalid_waste(self):
		with self.assertRaises(ValueError):
			calculate_reception(100, 20, waste_percent=101)

	def test_calculates_packaging_tare(self):
		self.assertEqual(str(calculate_packaging_tare([(10, 1.5), (4, 2.25)])), "24.000")

	def test_rejects_packaging_without_weight(self):
		with self.assertRaises(ValueError):
			calculate_packaging_tare([(10, 0)])
