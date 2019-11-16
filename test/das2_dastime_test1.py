import sys
import os
import os.path

def main(argv):

	perr = sys.stderr.write

	if len(argv) < 2:
		perr("BUILD_DIRectory missing")
		return 4
		
	if not os.path.isdir(argv[1]):
		perr("Directory %s doesn't exist"%argv[1])

	sys.path.insert(0, "%s/%s"%(os.getcwd(), argv[1]))
	sys.path.insert(0, ".")
	
	import das2 as D
	
	dt = D.DasTime("1971-001")
	print("A parsed time")
	print(str(dt)[:-3])
	print("")
	
	dt.adjust(0,0,364,23,59,59.999999)
	
	print("Adding 364 days, 23 hours, 59 minutes, and 59.999999 seconds")
	print(str(dt))
	print("")
	
	print("Blindly printing to millisecond resolution (error)")
	print("%04d-%03dT%02d:%02d:%06.3f"%(dt.year(), dt.doy(), dt.hour(), 
	                                   dt.minute(), dt.sec()))
	print("")
	
	print("You can use the round_doy() function to help")
	print(dt.round_doy(dt.MILLISEC))
	print("")
	
	print("Or the round() function too")
	print(dt.round(dt.MILLISEC))
	print("")
	
	return 0
	
	
if __name__ == "__main__":
	sys.exit(main(sys.argv))
