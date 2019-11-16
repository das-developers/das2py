# No she-bang here because we want the test target to pick the python version

import sys
import das2


#src = das2.get_source('site:/uiowa/juno/wav/survey/das2')
src = das2.get_source('site:/uiowa/cassini/rpws/survey_keyparam/das2')
lDs = src.httpGet({'start_time':'2016-10-02T11:00', 'end_time':'2016-10-02T12:00'})

for i in range(len(lDs)):
	print("Dataset 1:")
	print(lDs[i].info)
	
lDs = src.httpGet({'start_time':'2016-10-02T11:00', 'end_time':'2016-10-02T12:00'})

sys.exit(117)

src = das2.get_source('site:/uiowa/cassini/rpws/survey_keyparam/das2')

lDs = src.get(time=('2010-001','2010-002'), magnetic_specdens=1)


## For data items we want to be able to change units and to enable or
## disable various entries
#
lDs = src.get(time=('2014-08-31', '2014-09-01', 43.2), amp={'units':'DN'})



#
#src.get(time=('2014-08-31', '2014-09-01', 43.2), amp=False)
#
#src.get(time=('2014-08-31', '2014-09-01'), Bx="", By=" ")
#

   





















