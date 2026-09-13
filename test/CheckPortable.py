"""Trap for interpreter-specific code in the common tree.

Compiles every package and script source with the interpreter running this
test, so a construct the other interpreter cannot parse (f-strings, keyword
only arguments, print with end=) fails here as soon as the py2 chain runs.
Then greps for the idioms that parse everywhere but only work on one side:
zero-argument super(), and open() with encoding= outside a try block.

Runs from the das2py root, with no das2 import, so it works before the
extension is built.
"""

from __future__ import print_function
import sys
import os
import re
import warnings

ROOTS = ('das3', 'das2', 'scripts')

# Test files that are part of make test; the rest of test/ holds generators
# and scratch that never run on 2.7
TEST_FILES = (
	'test/TestCatalog.py', 'test/TestDasTime.py', 'test/TestSortMinimal.py',
	'test/TestRead.py', 'test/TestComposite.py', 'test/TestAlias.py', 'test/TestPkt.py',
)

ZERO_ARG_SUPER = re.compile(r'\bsuper\(\s*\)')
OPEN_ENCODING  = re.compile(r'\bopen\([^)]*\bencoding\s*=')

def sources():
	for sRoot in ROOTS:
		for (sDir, lDirs, lFiles) in os.walk(sRoot):
			for sFile in lFiles:
				sPath = os.path.join(sDir, sFile)
				if sFile.endswith('.py'):
					yield sPath
				elif sDir == 'scripts':
					with open(sPath, 'rb') as f:
						if f.read(2) == b'#!':
							yield sPath
	for sPath in TEST_FILES:
		yield sPath

def main(argv):
	nBad = 0
	for sPath in sources():
		with open(sPath, 'rb') as f:
			bSrc = f.read()

		# The builtin, not py_compile: nothing to write, and the SyntaxError
		# carries the line number for the report.  Bytes in, since 2.7 will
		# not take a coding cookie inside a unicode string.  SyntaxWarning
		# is promoted so an invalid escape like '\m' fails here on 3.12
		# instead of becoming a SyntaxError in a later interpreter.
		try:
			with warnings.catch_warnings():
				warnings.simplefilter('error', SyntaxWarning)
				compile(bSrc, sPath, 'exec')
		except SyntaxError as e:
			nBad += 1
			print("FAIL %s:%s: does not compile on %s: %s"%(
				sPath, e.lineno, sys.version.split()[0], e.msg))
			continue

		lLines = bSrc.decode('utf-8').split('\n')
		for (i, sLine) in enumerate(lLines):
			if ZERO_ARG_SUPER.search(sLine):
				nBad += 1
				print("FAIL %s:%d: zero-argument super() is python 3 only"%(sPath, i+1))
			if OPEN_ENCODING.search(sLine):
				sBefore = ' '.join(lLines[max(0, i-2):i])
				if 'try:' not in sBefore:
					nBad += 1
					print("FAIL %s:%d: open(encoding=) needs a try/except fallback on python 2"%(
						sPath, i+1))

	if nBad:
		print("%d portability problems"%nBad)
		return 13
	print("Sources compile and carry no one-interpreter idioms (%s)"%sys.version.split()[0])
	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
