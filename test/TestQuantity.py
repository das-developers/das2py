"""Quantity arithmetic with plain numbers on both sides, on both interpreters.

The 2.7 operator names differ from the 3.x ones for division, which is how
1.0 / quantity came to raise TypeError on 2.7 while 3.x was fine.
"""

from __future__ import print_function
import sys
import unittest
import das3


class TestQuantity(unittest.TestCase):

	def test_div_by_number(self):
		q = das3.Quantity(4.0, 's') / 2.0
		self.assertEqual(q.value, 2.0)
		self.assertEqual(q.unit, 's')

	def test_number_div_quantity(self):
		# the case that raised on 2.7
		q = 1.0 / das3.Quantity(4.0, 's')
		self.assertEqual(q.value, 0.25)
		self.assertEqual(q.unit, 'Hz')

	def test_quantity_div_quantity(self):
		q = das3.Quantity(6.0, 'V') / das3.Quantity(2.0, 's')
		self.assertEqual(q.value, 3.0)
		self.assertEqual(q.unit, 'V s**-1')

	def test_mul_both_sides(self):
		self.assertEqual((2.0 * das3.Quantity(3.0, 'km')).value, 6.0)
		self.assertEqual((das3.Quantity(3.0, 'km') * 2.0).value, 6.0)

	def test_int_times_quantity_is_not_tuple_repeat(self):
		# Quantity is a namedtuple; without __rmul__, 2 * q is (3.0, 'km', 3.0, 'km')
		q = 2 * das3.Quantity(3.0, 'km')
		self.assertTrue(isinstance(q, das3.Quantity))
		self.assertEqual(q.value, 6.0)
		self.assertEqual(q.unit, 'km')

	def test_to_value(self):
		# AstroPy's spelling, kept on purpose
		self.assertEqual(das3.Quantity(1500.0, 'Hz').to_value('kHz'), 1.5)


if __name__ == '__main__':
	unittest.main()
