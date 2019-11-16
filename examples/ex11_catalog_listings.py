# das2py example 11:
#    Reading catalogs and observing two stage node initialization

import das2

# ########################################################################### #
# Helper: print info on each catalog node
def prnCat(node):
   # Print what it is and its Universal Resource Identifier
   print("'%s'  name: '%s', type: %s"%(
      node.path, node.name, node.__class__.__name__)
   )

   # Looping over sub items internally triggers a call to the __iter__ method
   # which will load the full node definition if needed.
   for sSub in node:
      sub_node = node[sSub]
      print("  |- '%s'  name: '%s', type: %s"%(
            sSub, sub_node.name, sub_node.__class__.__name__)
      )

   print()

# ########################################################################### #
# Browsing directory nodes
top_node = das2.get_node(None)
prnCat(top_node)

# Lets walk down the node tree to the Galileo Ephemeris data Collection.
# Detailed node definitions are only downloaded as needed.  This way GUI
# Tree controls don't have to load the entire catalog at once.
das_node = top_node['tag:das2.org,2012:']
prnCat(das_node)

site_node = das_node['site']
prnCat(site_node)

uiowa_node = site_node['uiowa']
prnCat(uiowa_node)

cas_node = uiowa_node['cassini']
prnCat(cas_node)

rpws_node = cas_node['rpws']
prnCat(rpws_node)

survey_node = rpws_node['survey']
prnCat(survey_node)

# Alternate method, let's jump down to leaf node using dictionary style access
waves_node = top_node['tag:das2.org,2012:']['site']['uiowa']['juno']['wav']['survey']
prnCat(waves_node)

# And the simplest method, getting a node using a path URI.
#
# In this case we skip loading the upper level nodes since we know what we want
# to read.  Since the majority of the nodes used in daily processing are likely
# to be under the das head node, path URIs that don't start with one of the
# root paths are assumed to be a relative path under: 'tag:das2.org,2012:'

ephem_col = das2.get_node('site:/uiowa/galileo/ephemeris/jovicentric')


# ########################################################################### #
# Two stage loading and the props member

# das2 Node objects use lazy initialization.  Catalog nodes contains references
# to sub-nodes.  Sub-nodes can be accessed using standard python dictionary
# methods.  When first obtaining a reference to a python sub-node object it
# looks to application code as if the sub-node has already been read from it's
# catalog file.  In fact this is not the case.  If it were, loading the root
# node would cause the entire global catalog to be pulled into memory, a
# situation to be avoided.  Until a Node function is called that needs the full
# definition, the Node is defined only by the few elements given in its parent
# catalog listing.  The only items that are always defined are:
#
#   Node.__class__.__name__ - The python class name for the node.
#   Node.path  - The absolute path name of this node, typically begins with
#                'tag:das2.org,2012:'
#   Node.name  - The common label to use for this node in GUI controls and
#                listings
#   Node.props - A dictionary of any properties for this node, which initially
#                is a very small set, grows quite a bit when the full node is
#                loaded.
#   Node.urls  - The set of URLs from which this node may be loaded if required.
#
# Using lazy initialization allows GUI tree controls (for example) to only load
# the portions of the catalog that are needed without requiring management of
# two separate python objects for each node.
#
# If for some reason you need to force a full node definition in memory use the
# function:
#
#   Node.load()

# To view the full set of properties for a node, use the props member
# dictionary.  In the code below a node is obtained from from the Catalog
# rpws_node above.  Since the parent doesn't carry a full child definition
# only a stub node is present at first

hfr_wfrm = rpws_node['hires_midfreq_waveform']

print("Stub node %s from %s:"%(hfr_wfrm.__class__.__name__, rpws_node.url))
for key in hfr_wfrm.props:
   print("   %s: %s" %(key, hfr_wfrm.props[key]))
print()

# Explicitly load the full node.  This isn't required unless we're dealing with
# the Node.props member directly as the various catalog API functions will
# trigger a full load as needed.
hfr_wfrm.load()

# Print the node properties again (notice the .url member of the child node)
print("Full node %s from %s:"%(hfr_wfrm.__class__.__name__, hfr_wfrm.url))
for key in hfr_wfrm.props:
   print("   %s: %s" %(key, hfr_wfrm.props[key]))
print()
