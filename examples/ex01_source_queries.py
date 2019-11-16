# das2py example 01:  Data queries using catalog Source nodes
#
# The lowest level nodes in a das2 catalog are usually Source nodes which
# describe where and how to get data.  Without source nodes the catalog
# wouldn't be very useful.  The most common source node type is HttpStreamSrc,
# which can describe many HTTP GET based data service including das2 servers
# and HAPI servers.  A future Source derived class will provide access to
# static file collections.
#
# There are currently three types of data querys supported by das2py and the
# das2 catalog system, each of which is useful for a different purpose.
#
#  0.  Get example data using Source.example()
#
#      All data sources are required to provide at least one default set of
#      data for testing and evaluation purposes.  Named examples may be
#      requeseted if desired.  Other than the example name (which is optional)
#      no arguments are required.
#
#  1.  Protocol specific queries using Source.protoQuery()
#
#      Using protoQuery() directly means that application code is tied to a
#      specific GET API and will break if the server definition changes (for
#      example due to upgrades).  Even with these low level queries, automatic
#      failover to redundant servers is still supported.
#
#  2.  Source public API queries using Source.query()
#
#      These use the more generic use the public interface API of the source.
#      The Source node contains information to translate public API queries
#      into the specific protocol strings that must be issued to the server.
#      As new server versions are developed the underlying protocol may change,
#      but these query parameters can remain fixed.
#
# The code below provides examples of all three working query types.
#
#   For the curious a fourth query type that will handle contacting multiple
#   heterogenous data sources using permanent IDs such as DOIs is prototyped
#   in the file: future/exNN_collection_queries.py .

import das2
import sys


sId = 'site:/uiowa/cassini/rpws/hires_midfreq_waveform/das2'

# 0. Getting example data.  All valid das2 catalog Source definitions are
#    required to provide at least one example dateset.

src = das2.get_source(sId)
for name, summary in src.examples(): print(name, "|", summary)
lDatasets = src.get()  # Gets the first example if no arguments are provide


# 1. Protocol specific query (discouraged, but sometimes necessary).  If the
#    data are moved to a different server with a different API, this code will
#    break.

src = das2.get_source(sId)
print( src.protoInfo() )

dQuery = {
   'start_time':'2008-223T09:06', 'end_time':'2008-223T09:13',
   'params':'--80khz'
}
lDatasets = src.protoGet(dQuery, verbose=True)
print(lDatasets[0])

# 2. Public interface query.  This interface exists to make it easier to
#    associate data navigation operations with the query parameters.  This
#    is the recommended interface for most uses.

src = das2.get_source(sId)
print(src.info())

dQuery = { 'time':('2008-223T09:06', '2008-223T09:13'), 
           'frequency':{'band':'80 kHz'}  }
lDatasets = src.get(dQuery)

# Print dataset info. Actually using the datasets returned via these queries
# is the subject of subsequent examples

for ds in lDatasets:
   print(ds)
   print("")

