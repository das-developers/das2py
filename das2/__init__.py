"""Compatibility alias: ``import das2`` is ``import das3``.

The package was renamed for the das3 stream format; das3 does not imply
Python 3, this shim runs on 2.7 as well.  Every name under das2, including
submodules such as das2.dastime and das2.pycdf.const, resolves to the very
same module object as its das3 counterpart, so there is never a second copy
of a class to trip an isinstance() check.

The pip distribution is still das2py.  A PendingDeprecationWarning is issued
once per process.  Python hides that category everywhere by default, so old
scripts run without a word on either interpreter; to find them, run with

    python -W error::PendingDeprecationWarning old_script.py
"""

# Python 2 tries 'import das3' inside this package as the relative
# 'das2.das3' first, which the finder below would alias to 'das3.das3'.
from __future__ import absolute_import

import sys
import warnings


class _Alias(object):
	"""Meta path finder that answers for das2 and das2.* with das3 modules.

	Both import protocols are implemented in one class.  Python 2 calls
	find_module()/load_module() (PEP 302); 3.4 and later call find_spec()
	and the create/exec pair (PEP 451), and 3.12 removed the old pair
	entirely.  Each interpreter only ever calls the half it knows.

	Imports are local to each method on purpose.  This module replaces
	itself in sys.modules below, and Python 2 then sets every global of
	the discarded module to None, so a method that reached for a module
	level 'importlib' would find None the next time it ran.
	"""

	@staticmethod
	def _target(sName):
		if sName == 'das2' or sName.startswith('das2.'):
			return 'das3' + sName[4:]
		return None

	# Python 2 -------------------------------------------------------------
	def find_module(self, sName, path=None):
		return self if self._target(sName) else None

	def load_module(self, sName):
		import sys, importlib
		mod = importlib.import_module(self._target(sName))
		sys.modules[sName] = mod
		return mod

	# Python 3.4+ ----------------------------------------------------------
	def find_spec(self, sName, path, target=None):
		# Answer for foreign names before importing anything: the import
		# machinery asks every finder about 'importlib.util' too, and a
		# finder that imports first recurses into itself.
		if not self._target(sName):
			return None
		import importlib.util
		return importlib.util.spec_from_loader(sName, self)

	def create_module(self, spec):
		import importlib
		return importlib.import_module(self._target(spec.name))

	def exec_module(self, module):
		pass   # the das3 module already ran; nothing to execute


if not any(isinstance(f, _Alias) for f in sys.meta_path):
	sys.meta_path.insert(0, _Alias())

warnings.warn(
	"'import das2' is deprecated; the package is 'das3' (pip: das2py)",
	PendingDeprecationWarning, stacklevel=2
)

# Replace this shim with the real package in sys.modules, so attribute
# access on the das2 name reaches das3 without a second copy of anything.
import das3
sys.modules[__name__] = das3
