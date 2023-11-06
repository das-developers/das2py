# No she-bang here because we want the test target to pick the python version

import sys
import das2
import json

pout = sys.stdout.write

# Some sample nodes:
#
#

def test_load(sUri, sLocation):

	try:
		dNode = das2._das2.get_node(sUri, None, sLocation)
		
	except das2._das2.Error as e:
		sMsg = str(e)
		i = sMsg.find("\n")
		if i != 1:
			sMsg = sMsg[:i]
		pout(" [FAILED]\n")
		print(sMsg)
		return False

	s = json.dumps(dNode, ensure_ascii=False, indent=2, sort_keys=True)
	pout(" (type is: %s) "%dNode['type'])
	pout(" [PASSED]\n")	
	return True


def main(argv):
	
	pout("Testing: DasCatalog functions\n")
	
	sSite = "tag:das2.org,2012:das/site/uiowa"
		
	# Get a standalone item give it what ever name we want
	sLoc = 'https://das2.org/catalog/das/site/uiowa/cassini/ephemeris/dione/das2.json'
	pout("   Test 1: Load direct URL %s"%sLoc)
	sId = "magnetospheric/dione/cassini/ephemeris"
	
	if not test_load(sId, sLoc): return 13
	
	# Get something from the root volume
	sId = "tag:das2.org,2012:site:/uiowa/juno/wav/survey"
	pout("   Test 2: Load path URI: %s"%sId)
	
	if not test_load(sId, None): return 13
	
	
	pout("\nAll Catalog Tests passed\n\n")
	return 0
	
	
	
if __name__ == '__main__':
	sys.exit(main(sys.argv))
