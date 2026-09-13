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
import glob
import warnings

ROOTS = ('das3', 'das2', 'scripts')

# Test files that are part of make test; the rest of test/ holds generators
# and scratch that never run on 2.7
TEST_FILES = (
	'test/TestCatalog.py', 'test/TestDasTime.py', 'test/TestSortMinimal.py',
	'test/TestRead.py', 'test/TestComposite.py', 'test/TestAlias.py', 'test/TestPkt.py', 'test/TestProps.py', 'test/TestQuantity.py',
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

# Builtins of the interpreter this trap is NOT running on, plus names that
# only exist under a version guard
_lOtherInterp = ('unicode', 'long', 'xrange', 'cmp', 'basestring', 'raw_input')

def checkNames():
	"""Every bare name a package module reads resolves after import.  A
	name that only ever arrived through another module's star import stops
	resolving the day that module gains an __all__, and nothing else notices
	until a user hits the line.  Skipped when the package is not importable
	(this trap also runs before the extension is built)."""
	import ast, importlib
	try:
		import builtins
	except ImportError:
		import __builtin__ as builtins
	try:
		import das3
	except ImportError:
		print("(package not importable here, name check skipped)")
		return 0
	nBad = 0
	for sPath in sorted(glob.glob('das3/*.py')):
		sMod = 'das3' if sPath.endswith('__init__.py') else 'das3.' + os.path.basename(sPath)[:-3]
		mod = importlib.import_module(sMod)
		with open(sPath, 'rb') as f:
			tree = ast.parse(f.read(), sPath)
		lUsed = set(); lBound = set()
		for n in ast.walk(tree):
			if isinstance(n, ast.Name):
				(lUsed if isinstance(n.ctx, ast.Load) else lBound).add(n.id)
			elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
				lBound.add(n.name)
			if isinstance(n, (ast.FunctionDef, ast.Lambda)):
				# *args and **kwargs: a plain string on 2.7, an ast.arg on 3
				for v in (n.args.vararg, n.args.kwarg):
					if v is not None:
						lBound.add(v if isinstance(v, str) else v.arg)
			elif isinstance(n, ast.ExceptHandler) and n.name:
				lBound.add(n.name if isinstance(n.name, str) else n.name.id)
			elif isinstance(n, (ast.Import, ast.ImportFrom)):
				for a in n.names:
					lBound.add((a.asname or a.name).split('.')[0])
			elif hasattr(ast, 'arg') and isinstance(n, ast.arg):
				lBound.add(n.arg)
		for sName in sorted(lUsed):
			if sName in lBound or sName in _lOtherInterp: continue
			if hasattr(mod, sName) or hasattr(builtins, sName): continue
			nBad += 1
			print("FAIL %s: name %r is read but never defined or imported"%(sPath, sName))
	return nBad


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

	nBad += checkNames()

	if nBad:
		print("%d portability problems"%nBad)
		return 13
	print("Sources compile and carry no one-interpreter idioms (%s)"%sys.version.split()[0])
	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
