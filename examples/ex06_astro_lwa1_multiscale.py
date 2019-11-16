# das2 module example 6:
#   Plotting terrestrial radio-astronomy observations of Jupiter from the 
#   Long Wave Array, installation 1 (LWA-1).  
#
#   This example demonstrates:
#
#     1) Selecting data variable output
#     2) Selecting different coordinate resolutions
#
# das2 server download speeds and data volumes at various time resolutions

import sys
import das2

# Temporary:  This data source requires authentication, so set it.
n = das2.auth_load()

sId = 'site:/uiowa/earth/lwa-1/stokes_fullres/das2'
src = das2.get_source(sId)
print(src.info())

sys.exit(117)

dQuery = {
   'time':('2015-02-21T05:11', '2015-02-21T05:12', 0.03),
   'frequency':{'center':30}, 'psd':{'stokes':'V/I'}
}

lDs = src.get(dQuery)

# get data for the low tuning as well

dQuery['reader']['high'] = False
lDs = src.get(dQuery)


# Das2 server specific query
dQuery = {
   'start_time':'2015-02-21T05:11',
   'end_time':  '2015-02-21T05:12',
   'resolution': '0.03',
   'param':'High Q'
}

lDs = src.http_get(dQuery)

