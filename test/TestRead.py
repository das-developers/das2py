import sys
import das2

perr = sys.stderr.write

# Testing low level and high level das2 python data read APIs

def main(argv):

	if len(argv) > 1:
		sUrl = " ".join(argv[1:])

	# Try file read, with packet definition, but no data packets
	sFile = 'test/test_read_empty.d2s'

	# Low level
	lDs = das2._das2.read_file(sFile)
	for ds in lDs: print(ds['info'])
	print("")

	# High level
	lDs = das2.read_file(sFile)

	for ds in lDs: print(ds)
	print("")

	lDs = das2.ds_strip_empty(lDs)
	if len(lDs) > 0:
		perr("ERROR: Expected empty dataset list\n")
		return 13


	# Try server read

	sUrl = 'https://jupiter.physics.uiowa.edu/das/server?server=dataset&'+\
	       'dataset=Galileo/PWS/Survey_Electric&start_time=2001-001&' +\
			 'end_time=2001-002'
			 
	# First low level...
	lDs = das2._das2.read_server(sUrl, 3.0)
	for ds in lDs: print(ds['info'])
	print("")
	
	# Now high level			 
	lDs = das2.read_http(sUrl)
	for ds in lDs: print(ds)

	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv))
