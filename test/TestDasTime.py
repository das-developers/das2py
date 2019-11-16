import das2
import unittest

class TestDasTime(unittest.TestCase):
	
	def test_floor(self):
		dt1 = das2.DasTime('2014-01-01T12:57:34.445')
		dt2 = das2.DasTime('2014-01-01T12:57')
		dt1.floor(60)
		self.assertEqual(dt1, dt2)
		
		dt1 = das2.DasTime('2014-01-01T12:57:34.445')
		dt2 = das2.DasTime('2014-01-01T12:57:30')
		dt1.floor(25)
		self.assertEqual(dt1, dt2)

		
		dt1 = das2.DasTime('2014-01-01T12:57:34.445')
		dt2 = das2.DasTime('2014-01-01T12:50')
		dt1.floor(600)
		self.assertEqual(dt1, dt2)
		
		dt1 = das2.DasTime('2014-01-01T12:57:34.445')
		dt2 = das2.DasTime('2014-01-01T12:40')
		dt1.floor(1200)
		self.assertEqual(dt1, dt2)
		
		dt1 = das2.DasTime('2014-01-01T12:57:34.445')
		dt2 = das2.DasTime('2014-01-01T12:00')
		dt1.floor(3600)
		self.assertEqual(dt1, dt2)
		
		
	def test_ceil(self):
		dt1 = das2.DasTime('2014-01-01T12:07:34.445')
		dt2 = das2.DasTime('2014-01-01T12:08')
		dt1.ceil(60)
		self.assertEqual(dt1, dt2)

		dt1 = das2.DasTime('2014-01-01T12:07:34.445')
		dt2 = das2.DasTime('2014-01-01T12:10')
		dt1.ceil(600)
		self.assertEqual(dt1, dt2)
		
		dt1 = das2.DasTime('2014-01-01T12:07:34.445')
		dt2 = das2.DasTime('2014-01-01T12:20')
		dt1.ceil(1200)
		self.assertEqual(dt1, dt2)
		
		dt1 = das2.DasTime('2014-01-01T12:07:34.445')
		dt2 = das2.DasTime('2014-01-01T13:00')
		dt1.ceil(3600)
		self.assertEqual(dt1, dt2)


if __name__ == '__main__':
	unittest.main()
