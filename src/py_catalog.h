/* Copyright (C) 2018-2019 Chris Piker
 *
 * This file is part of das2py, the Core Das2 C Library.
 * 
 * Das2py is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License version 2.1 as published
 * by the Free Software Foundation.
 *
 * Das2py is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
 * more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * version 2.1 along with das2py; if not, see <http://www.gnu.org/licenses/>. 
 */

#ifndef _WIN32
#include <strings.h>
#endif

#include <Python.h>

#include <das2/http.h>
#include <das2/node.h>
#include <das2/log.h>

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#endif

/* This block is just here to make IDE code assistance not throw up lots of 
 * errors since it has to be able to understand how to parse this file on 
 * it's own. */
#ifndef HAS_DAS2_PYEXCEPT
static PyObject* g_pPyD2Error;
static void* pyd2_setException(PyObject* pExcept);
static void* pyd2_setExceptFromLog(PyObject* pExcept);
static PyObject* g_pPyD2QueryErr;
static PyObject* g_pPyD2AuthErr;
static DasCredMngr* g_pMgr = NULL;
#endif

/* ************************************************************************* */
/* converting JSON data to python objects                                    */
PyObject* DasJdo_toPyObj(const DasJdo* pJdo){
	
	PyObject* pPy = NULL;
	PyObject* pPySub = NULL;
	const char* sStr = NULL;
	const das_json_dict_el* pDel = NULL;
	const das_json_ary_el* pAel = NULL;
	const das_json_str* pS = NULL;
	const das_json_num* pN = NULL;
	double rNum = 0.0;
	Py_ssize_t u = 0;
	
	/* Note: PyDict_SetItem and PyList_SetItem handle reference counts 
	 * differently.  Dicts increment the ref count when you hand them an 
	 * item.  So if you don't want to own the item you have to decrement the
	 * count.  Lists just assume that you wanted them to own the item so they
	 * don't increment the count, but they do assume they can decrement it at
	 * will.  So... call Py_DECREF for dicts, but not for lists.  */
	
	switch(pJdo->type){
	case das_json_type_dict:
		pPy = PyDict_New();
		if(pPy == NULL) 
			return NULL;
		
		for(pDel = DasJdo_dictFirst(pJdo); pDel != NULL; pDel = pDel->next){
			sStr = ((das_json_str*)pDel->name)->string;
			if(sStr != NULL){
				pPySub = DasJdo_toPyObj( pDel->value);
				if(pPySub == NULL){ 
					Py_DECREF(pPy); return NULL; 
				}
				if(PyDict_SetItemString(pPy, sStr, pPySub) != 0){
					Py_DECREF(pPySub); Py_DECREF(pPy); return NULL; 
				}
			}
		}
		return pPy;
		
	case das_json_type_ary:
		pPy = PyList_New( ((das_json_ary*)(pJdo->value))->length );
		if(pPy == NULL) 
			return NULL;
		
		u = 0;
		for(pAel = DasJdo_aryFirst(pJdo); pAel != NULL; pAel = pAel->next){
			pPySub = DasJdo_toPyObj(pAel->value);
			if((pPySub == NULL)||(PyList_SetItem(pPy, u, pPySub) != 0)){
				Py_DECREF(pPy); return NULL;
			}
			++u;
		}
		return pPy;
		
	case das_json_type_str:
		pS = (das_json_str*)pJdo->value;
		pPy = PyString_FromString(pS->string);
		return pPy;
		
	case das_json_type_num:
		/* Return an integer if you can */
		pN = (das_json_num*)pJdo->value;
		if(!das_str2double(pN->number, &rNum)){
			daslog_error_v("Couldn't convert %s to a number", pN->number);
			return NULL;
		}
		if( rNum == (long int) rNum)
			return PyInt_FromLong((long int)rNum);  // Convert as integer
		else
			return PyFloat_FromDouble(rNum);        // Convert as double
		
		
		
	case das_json_type_true:
		return PyBool_FromLong(1);
		
	case das_json_type_false:
		return PyBool_FromLong(0);
		
	case das_json_type_null:
		Py_RETURN_NONE;
	}
	return pPy;
}

/* ************************************************************************* */
/* Reading catalog data */

static DasNode* g_pRootCat = NULL;

static char pyd2help_get_node[] = 
"Get JSON data from a das2 Catalog Node by URL or URI.\n"
"\n"
"Arguments\n"
"   path_uri (string) - The URI of the node to load.  By default the federated\n"
"         catalog system is used to provide the URL to the catalog node file.\n"
"\n"
"   agent (string, optional) - If present (and not None) then the supplied text\n"
"         will be the User Agent string supplied to any remote HTTP servers that\n"
"         are contacted.\n"
"\n"
"   url (string, optional) - If present (and not None) then the node is loaded\n"
"         directly from the URL provided, potentially skipping the global\n"
"         catalog, this is useful for testing stand alone catalog files\n";

static PyObject* pyd2_get_node(PyObject* self, PyObject* args)
{
	
	const char* sUri = NULL;
	const char* sAgent = NULL;
	const char* sLocation = NULL;
	DasNode* pNode = NULL;
	PyObject* pPyObj = NULL;
	
	if(!PyArg_ParseTuple(args, "z|zz:get_node", &sUri, &sAgent, &sLocation))
		return NULL;
	
	/* g_pMgr note: module initialization handles the lone cred manager */
	if(g_pRootCat == NULL){
		g_pRootCat = new_RootNode(NULL, g_pMgr, sAgent);
		if(g_pRootCat == NULL) return NULL;
	}
	
	if(sUri == NULL){
		pNode = g_pRootCat;
	}
	else{
		if(sLocation != NULL)
			pNode = new_RootNode_url(sLocation, sUri, g_pMgr, sAgent);
		else
			pNode = DasNode_subNode(g_pRootCat, sUri, g_pMgr, sAgent);
	}
	
	if(pNode == NULL) return pyd2_setExceptFromLog(g_pPyD2Error);
		
	/* Convert node data to python objects */
	if(!DasNode_isJson(pNode)){
		PyErr_SetString(PyExc_NotImplementedError, 
			"Handling non-JSON catalogs is not yet implemented"
		);
		return NULL;
	}
		
	pPyObj = DasJdo_toPyObj((DasJdo*)pNode->pDom);
	if(pPyObj == NULL){
		return pyd2_setExceptFromLog(g_pPyD2Error);
	}
	
	/* Save the URL used to get the item, this is very handy for informational 
	 * messages */
	PyObject* pTmp = PyString_FromString(pNode->sURL);
	
	if(PyDict_SetItemString(pPyObj, "_url", pTmp) != 0){
		Py_DECREF(pTmp); Py_DECREF(pPyObj); return NULL; 
	}
	
	pTmp = PyString_FromString(pNode->sPath);
	if(PyDict_SetItemString(pPyObj, "_path", pTmp) != 0){
		Py_DECREF(pTmp); Py_DECREF(pPyObj); return NULL; 
	}
	
	
	if(pNode && (sLocation != NULL)) del_RootNode(pNode);
	return pPyObj;
}


