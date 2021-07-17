# 
# Fast discrete cosine transform algorithms (Python)
# 
# Copyright (c) 2020 Project Nayuki. (MIT License)
# https://www.nayuki.io/page/fast-discrete-cosine-transform-algorithms
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# - The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
# - The Software is provided "as is", without warranty of any kind, express or
#   implied, including but not limited to the warranties of merchantability,
#   fitness for a particular purpose and noninfringement. In no event shall the
#   authors or copyright holders be liable for any claim, damages or other
#   liability, whether in an action of contract, tort or otherwise, arising from,
#   out of or in connection with the Software or the use or other dealings in the
#   Software.
# 

import math, random, unittest
import fastdctlee, naivedct


class FastDctTest(unittest.TestCase):
	
	def test_fast_dct_lee_vs_naive(self):
		for i in range(1, 12):
			n = 2**i
			vector = FastDctTest.random_vector(n)
			expect = naivedct.transform(vector)
			actual = fastdctlee.transform(vector)
			self.assertListAlmostEqual(actual, expect)
			expect = naivedct.inverse_transform(vector)
			actual = fastdctlee.inverse_transform(vector)
			self.assertListAlmostEqual(actual, expect)
	
	def test_fast_dct_lee_invertibility(self):
		for i in range(1, 18):
			n = 2**i
			vector = FastDctTest.random_vector(n)
			temp = fastdctlee.transform(vector)
			temp = fastdctlee.inverse_transform(temp)
			temp = [(val * 2.0 / n) for val in temp]
			self.assertListAlmostEqual(vector, temp)
	
	def assertListAlmostEqual(self, actual, expect):
		self.assertEqual(len(actual), len(expect))
		for (x, y) in zip(actual, expect):
			self.assertAlmostEqual(x, y, delta=FastDctTest._EPSILON)
	
	
	@staticmethod
	def random_vector(n):
		return [random.uniform(-1.0, 1.0) for _ in range(n)]
	
	
	_EPSILON = 1e-9


if __name__ == "__main__":
	unittest.main()
