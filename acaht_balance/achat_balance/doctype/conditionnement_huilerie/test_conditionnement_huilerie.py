from unittest import TestCase

from acaht_balance.achat_balance.calculations import calculate_packaging


class TestPackagingCalculations(TestCase):
	def test_calculates_packaged_quantity_and_loss(self):
		result = calculate_packaging(100, [(100, 0.75), (40, 0.5)])
		self.assertEqual(str(result["packaged_quantity"]), "95.000")
		self.assertEqual(str(result["loss_quantity"]), "5.000")

	def test_rejects_quantity_above_source(self):
		with self.assertRaises(ValueError):
			calculate_packaging(10, [(11, 1)])

	def test_rejects_empty_or_negative_values(self):
		with self.assertRaises(ValueError):
			calculate_packaging(10, [(0, 1)])
