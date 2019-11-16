# The MIT License
#
# Copyright 2019 Chris Piker
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import os.path
import sys
import _das2

def auth_set(sBaseUrl, sRealm, sHash, tGetParam=(None,None)):
	"""Set an authentication hash to be sent to remote servers when certain
	conditions are met.
	
	To prevent password strings from being handed out willy-nilly, the request
	for authentication must come from a particular URL, for a particular 
	security realm, and for particular HTTP GET parameters, otherwise the
	authentication hash is not transmitted.
	
	:param sBaseUrl: The full URL path to match for the request.  For das2.2
	        servers it's recommended that the full server path be used, for
			  example: 'https://zeus.physics.uiowa.edu/das/server'
	
	:param sRealm: The security realm string provided to server to match 
	        for this authentication hash.
	
	:param sHash: The hash to send.  Most servers, including das2 pyServer
           are looking for an HTTP Basic Authentication hash which built as
			  follows.  Make the string 'USERNAME:PASSWORD' where ':' is a 
			  literal colon and encode it using the base64 algorithm.  The 
			  standard_b64encode() function from the base64 module can be used
			  to perform this task
	
	:param tGetParam: Mostly used for das2.2 servers.  These servers identify
	        datasets by special get parameters.  To only sent the Authentication
			  string when also transmitting a particular HTTP GET key, include
			  that key and value in a 2-tuple here.  For example:  
			  ('dataset', 'Juno/WAV/Survey'). 
			  
	:rtype: None	
	"""
	
	if tGetParam != None and tGetParam[0] != None:
		if tGetParam[0] != 'dataset':
			#TODO: Removed this once the das2 C module is updated
			raise NotImplementedError("Handling for general dataset ID "+\
			                          "parameters is not yet implemented")
		if tGetParam[1] is None:
			raise ValueError("Dataset ID value (sValue) can't be None when "+\
			                 "a key is given")
		_das2.auth_set(sBaseUrl, sRealm, sHash, tGetParam[1])
	else:
		_das2.auth_set(sBaseUrl, sRealm, sHash)


def auth_load(sFile=None):
	"""Load authentication hashes from a semicolon delimited disk file.  
	
	Each line of the file should contain a single hash to load.  Lines are
	formated with pipe, '|',  delimiters.  The hash itself may contain
	pipes as all non-whitespace after the fourth pipe is taken as the hash
	value.
	
	
	    URL | Realm | Key | Param | Hash 
	
	To indicate that a hash may be used with any GET parameters leave Key and
	Param blank.  Two adjacent delimiters, or two delimiters containing only
	whitespace indicate a blank field.
	
	:param sFile: If none, then the location $HOME/.das2_auth is read on Linux
	       and MacOS.  A suitable default for Windows has not been selected.
	
	:rtype: The number of authentication hashes loaded.
	"""
	
	if sFile is None:
		import os
		sHome = os.getenv('HOME')
		if sHome is None:
			raise EnvironmentError("Can't find account home directory")
			
		sFile = "%s/.das2_auth"%sHome
	
	if not os.path.isfile(sFile):
		sys.stderr.write("Can't open %s\n"%sFile)
		return 0
		
	fIn = open(sFile, 'r')
	
	nLine = 0
	nLoaded = 0
	for sLine in fIn:
		nLine += 1
		sLine = sLine.strip()
		if len(sLine) == 0:
			continue
			
		lLine = sLine.split('|')
		
		if len(lLine) < 5:
			raise ValueError(
				"%s, line %d: Two few entries, expected 5 fields:"
				"' URL; Realm; Key; Param; Hash ', where Key and "
				"Param may be an empty string"%(sFile, nLine))
		
		if len(lLine) > 5:    # In case hash contains '|' charaters
			lLine[4] = '|'.join(lLine[4:])
	
		lLoad = [s.strip() for s in lLine]
		
		if (lLoad[2] != None) and (len(lLoad[2]) > 0):
			auth_set(lLoad[0], lLoad[1], lLoad[4], (lLoad[2], lLoad[3]))
		else:
			auth_set(lLoad[0], lLoad[1], lLoad[4])
			
		nLoaded += 1
			
	fIn.close()
	return nLoaded	
