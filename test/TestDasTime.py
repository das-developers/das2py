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

	def test_tt2000(self):
		# Can't use dastime with tt2000 conversions due to the implicit call to 
		# tnorm.  Have to do something about that...

		# Convert a leap second time to a floating point time
		rTime = das2.to_epoch('TT2000', 2016, 12, 31, 23, 59, 60.0)
		self.assertEqual(rTime, 5.36500868184e+17)

		# Add a billion nanoseconds to it and see what we get
		rTime2 = das2.to_epoch('TT2000', 2017)
		self.assertEqual( rTime+1e9, rTime2)

		# Decode a leap second time
		t = das2.from_epoch(rTime, 'TT2000')
		self.assertEqual(t, (2016, 12, 31, 366, 23, 59, 60.0));

		dt1 = das2.DasTime('2016-12-31T23:59:59.0')
		dt2 = das2.DasTime('2017-01-01T00:00:00.0')

		r1 = dt1.epoch('TT2000')
		r2 = dt2.epoch('TT2000')
		self.assertEqual(r2 - r1, 2e9) # 2 seconds, not 1

	def test_convertable(self):
		# Test the the is convertable function
		self.assertEqual(True, das2.convertible('us2000','t1970'))

		# tt2000 aren't real units, TT2000 are, but it's a common mistake,
		# check to see that convertible throws
		try:
			das2.convertible('us2000','tt2000')
			self.assertEqual(True, False)
		except ValueError:
			pass
		self.assertEqual(True, das2.convertible('us2000','TT2000'))
		self.assertEqual(False, das2.convertible('doggy','us2000'))

if __name__ == '__main__':
	unittest.main()
