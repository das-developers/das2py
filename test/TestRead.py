import sys
import das3

perr = sys.stderr.write

# Testing low level and high level das2 python data read APIs

def main(argv):

	if len(argv) > 1:
		sUrl = " ".join(argv[1:])

	# Try file read, with packet definition, but no data packets
	sFile = 'test/test_read_empty.d2s'

	# Low level
	(dStream, lDs) = das3._das3.read_file(sFile)
	print(dStream['info'])
	for ds in lDs: 
		print(ds['info'])
	print("")

	# High level
	(dStream, lDs) = das3.read_file(sFile)

	# A bad read must raise.  These readers once printed the error and
	# returned None, which surfaced later as an unrelated TypeError.
	for sBad in ('test/no_such_file.d3t', __file__):
		try:
			das3.read_file(sBad)
		except das3._das3.Error:
			continue
		perr("ERROR: das3.read_file('%s') did not raise\n"%sBad)
		return 13

	return 0

	for ds in lDs:
		print(ds)
	print("")
	

	lDs = das3.ds_strip_empty(lDs)
	if len(lDs) > 0:
		perr("ERROR: Expected empty dataset list\n")
		return 13


	# Try server read

	sUrl = 'https://jupiter.physics.uiowa.edu/das/server?server=dataset&'+\
	       'dataset=Galileo/PWS/Survey_Electric&start_time=2001-001&' +\
			 'end_time=2001-002'
			 
	# First low level...
	(dStream, lDs) = das3._das3.read_server(sUrl, 3.0)
	print(dStream['info'])
	for ds in lDs: print(ds['info'])
	print("")
	
	# Now high level			 
	(dStream, lDs) = das3.read_http(sUrl)
	for ds in lDs: print(ds)

	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv))
