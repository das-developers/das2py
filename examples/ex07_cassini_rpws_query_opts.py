# das2 module example 7
#   Plotting filtered versus unfiltered Cassini RPWS survey data using
#   data source options

import numpy
import das2
import sys

import matplotlib.pyplot as pyplot
import matplotlib.colors as colors
import matplotlib.ticker as ticker

# The Cassini RPWS Survey data source is one of the most complicated das2 data
# sources at U. Iowa.  Data consist of multiple frequency sets from multiple
# recivers all attempting to cover the maximum parameter space within a limited
# telemetry alotment and on-board computing power.  
#
# Example 3 demonstrated collapsing what are essentially scatter data onto
# a single plot.  This example (7) focuses on using extra options to control
# the bands output by the data source.  das 2.2 servers pack all extra
# datasource options into a single GET parameter, while das 2.3 servers provide
# detailed parameter information.  As das 2.3 servers are not yet available
# this example will use the 2.2 protocol.

src = das2.Source("site:/uiowa/cassini/rpws/survey/das2")

