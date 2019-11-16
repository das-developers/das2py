# The MIT License
#
# Copyright 2019 Chris Piker
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


""" Define das2 utility types"""

class CatalogError(Exception):
	"""Raised when there is a problem with a definition in a das2 catalog"""
	def __init__(self, sUrl, sMsg):
		self.sUrl = sUrl
		self.sMsg = sMsg

	def __str__(self):
		return "%s (from %s)"%(self.sMsg, self.sUrl)

class SourceError(Exception):
	"""Raised when there is non-authentication problem gathing data from a server
	"""
	def __init__(self, sUrl, sMsg):
		self.sUrl = sUrl
		self.sMsg = sMsg

	def __str__(self):
		return "%s (from %s)"%(self.sMsg, self.sUrl)

class DatasetError(Exception):
	def __init__(self, sMsg):
		self.sMsg = sMsg

	def __str__(self):
		return self.sMsg
