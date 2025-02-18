/* Copyright (C) 2017-2024 Chris Piker
 *
 * This file is part of das2py, the das2C python wrapper
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


#include <limits.h>
#include <Python.h>

#include <das2/io.h>
#include <das2/http.h>
#include <das2/builder.h>
#include <das2/units.h>
#include <das2/log.h>

#include <numpy/ndarrayobject.h>

/*
#include <numpy/npy2_compat.h>
*/

#if PY_MAJOR_VERSION >= 3
#define PyString_FromString PyUnicode_FromString
#define PyInt_FromLong      PyLong_FromLong
#endif

#ifdef _WIN32
#define PyLong_FromInt64 PyLong_FromLongLong
#else
#define PyLong_FromInt64 PyLong_FromLong
#endif

/* This block is just here to make IDE code assistance not throw up lots of
 * errors since it has to be able to understand how to parse this file on
 * it's own. */
#ifndef HAS_DAS2_PYEXCEPT
static PyObject* g_pPyD2Error;
static void* pyd2_setException(void);
static PyObject* g_pPyD2QueryErr;
static PyObject* g_pPyD2AuthErr;
#endif

/* ************************************************************************* */
/* Singleton Credentials manager */

static DasCredMngr* g_pMgr = NULL;

const char pyd2help_auth_set[] =
"Set an authentication hash to be sent to remote servers when certain conditions\n"
"are met.\n"
"\n"
"The request must come from a particular server, for a particular realm,\n"
"and for a particular dataset.  The authentication hash is not transmitted\n"
"unless the server asks for it and the request matches the given conditions.\n"
"\n"
"Args:\n"
"   base_url (str) : The full URL path to the das2 server, which is not\n"
"      typically the same as the host root, example:\n"
"      https://zeus.physics.uiowa.edu/das/server \n"
"\n"
"   realm (str) : The authentication realm.  This is provided in the dsdf\n"
"      files under the securityRealm keyword.\n"
"\n"
"   hash (str) : The hash to send.  Most servers, including das2 pyServer\n"
"      are looking for an HTTP Basic Authentication hash\n"
"\n"
"   dataset (str,optional) : The dataset, ex: 'Juno/WAV/Survey'  Use None\n"
"      to match any dataset in this Realm.  Some sites will\n"
"      not provide this information in which case None should\n"
"      be used to match request from those sites.\n"
"\n"
"HTTP Basic Auth Hash Generation\n"
"   Make the string 'USERNAME:PASSWORD' where ':' is a literal colon and encode\n"
"   it using the base64 algorithm.  The standard_b64encode() function from the\n"
"   python base64 module can be used to perform this task.\n";

static PyObject* pyd2_auth_set(PyObject* self, PyObject* args)
{
	const char* url;  /* full path to CGI */
	const char* realm;
	const char* hash;
	const char* dataset = NULL;

	if(!PyArg_ParseTuple(args, "sss|s:set_auth", &url, &realm, &hash, &dataset))
		return NULL;
	das_credential cred;

	das_cred_init(&cred, url, realm, dataset, hash);
	int nCreds = CredMngr_addCred(g_pMgr, &cred);

	return Py_BuildValue("i", nCreds);
}

/* Helper for NDarray creation */
static void _npdims_from_shape(DasAry* pAry, PyArray_Dims* pNpDims){
	ptrdiff_t shape[16] = {0};
	DasAry_shape(pAry, shape);

	pNpDims->len = pAry->nRank;
	for(int i = 0; i < pAry->nRank; ++i) pNpDims->ptr[i] = shape[i];
}

/* ************************************************************************ */
/* Make a new numpy datetime64 array, allocs ndarray memory                 */

PyObject* _DasCalAryToNumpyAry(DasAry* pAry)
{
	/* Access the das2 array and the numpy array as a flat index space makes
	 * looping faster as the for-loop to find the next multi-dimensional
	 * index is not required */
	size_t uLen;
	das_val_type vt = DasAry_valType(pAry);
	const void* pMem = DasAry_getIn(pAry, vt, DIM0, &uLen);

	/* Create a Numpy Array descriptor that says we're going to use nanoseconds
	 * since 1970-01-01 for the meaning of the stored int8_t values */
	PyArray_Descr* pDesc = NULL;
	PyObject* pType = PyString_FromString("M8[ns]");
	PyArray_DescrConverter(pType, &pDesc);
	Py_DECREF(pType);

	npy_intp npLen = (npy_intp)uLen;
	PyObject* pObj = PyArray_SimpleNewFromDescr(1, &npLen, pDesc);
	if(pObj == NULL){
		PyErr_Format(g_pPyD2Error, "Couldn't generate new datetime64 array ");
		return NULL;
	}
	if(!PyArray_Check(pObj)){
		PyErr_SetString(PyExc_TypeError, "Unexpected type in _DasCalAryToNumpyAry()");
		Py_DECREF(pObj);
		return NULL;
	}

	PyArrayObject* pNdAry = (PyArrayObject*)pObj;

	if(! PyArray_ISBEHAVED(pNdAry) || !(PyArray_IS_C_CONTIGUOUS(pNdAry))){
		PyErr_Format(g_pPyD2Error, "New NDArray is not contiguous, aligned, and "
				                     "in machine byte order");
		Py_DECREF(pNdAry);
		return NULL;
	}

	/* Type branch to keep inner loops small */
	const ubyte* pUByte;   const int8_t* pByte;
	const int16_t* pShort; const uint16_t* pUShort;
	const int32_t* pInt;   const uint32_t* pUInt;
	const int64_t* pLong;  const uint64_t* pULong;
	const float* pFloat;   const double* pDbl;
	const das_time* pDt;
	npy_intp nd_index0[16] = {'\0'};
	int64_t* pNdData = (int64_t*) PyArray_GetPtr((PyArrayObject*)pNdAry, nd_index0);

	size_t u = 0;
	das_time dt;
	das_units units = DasAry_units(pAry);
	switch(vt){
	case vtUByte:
		for(pUByte = (const ubyte*)pMem, u = 0; u < uLen; ++u, ++pUByte, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pUByte), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtByte:
		for(pByte = (const int8_t*)pMem, u = 0; u < uLen; ++u, ++pByte, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pByte), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtUShort:
		for(pUShort = (const uint16_t*)pMem, u = 0; u < uLen; ++u, ++pUShort, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pUShort), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtShort:
		for(pShort = (const int16_t*)pMem, u = 0; u < uLen; ++u, ++pShort, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pShort), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtUInt:
		for(pUInt = (const uint32_t*)pMem, u = 0; u < uLen; ++u, ++pUInt, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pUInt), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtInt:
		for(pInt = (const int32_t*)pMem, u = 0; u < uLen; ++u, ++pInt, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pInt), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtULong:
		for(pULong = (const uint64_t*)pMem, u = 0; u < uLen; ++u, ++pULong, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pULong), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtLong:
		for(pLong = (const int64_t*)pMem, u = 0; u < uLen; ++u, ++pLong, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pLong), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtFloat:
		for(pFloat = (const float*)pMem, u = 0; u < uLen; ++u, ++pFloat, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pFloat), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtDouble:
		for(pDbl = (const double*)pMem, u = 0; u < uLen; ++u, ++pDbl, ++pNdData) {
			Units_convertToDt(&dt, (double)(*pDbl), units);
			*pNdData = dt_nano_1970(&dt);
		}
		break;
	case vtTime:
		for(pDt = (const das_time*)pMem, u = 0; u < uLen; ++u, ++pDt, ++pNdData){
			*pNdData = dt_nano_1970((das_time*)pDt);
		}
		break;
	default:
		PyErr_Format(g_pPyD2Error, "Type vt = %d not supported in conversion "
				       "to datetime64", vt);
		Py_DECREF(pNdAry);
		return NULL;
	}

	/* Reshape the array (hopefully IN PLACE, don't know how to insure this) */
	npy_intp np_shape[16] = {0};
	PyArray_Dims np_dims = {np_shape, 0};
	_npdims_from_shape(pAry, &np_dims);
	PyObject* pFinal = PyArray_Newshape((PyArrayObject*)pNdAry, &np_dims, NPY_CORDER);
	Py_DECREF(pNdAry);

	return pFinal;
}

/* ************************************************************************ */
/* Make a new numpy timedelta64 array, allocs ndarray memory                */

PyObject* _DasTimeAryToNumpyAry(DasAry* pAry)
{
	/* Get the conversion factor to nanoseconds */
	das_units units = DasAry_units(pAry);
	double factor = Units_convertTo(UNIT_SECONDS, 1.0, units);
	if(factor == DAS_FILL_VALUE) return NULL;
	factor *= 1.0e+9;

	size_t uLen;
	das_val_type vt = DasAry_valType(pAry);
	const void* pMem = DasAry_getIn(pAry, vt, DIM0, &uLen);

	/* Create a Numpy Array descriptor that says we're going to use nanoseconds
	 * for the meaning of the stored int8_t values */
	PyArray_Descr* pDesc = NULL;
	PyObject* pType = PyString_FromString("m8[ns]");
	PyArray_DescrConverter(pType, &pDesc);
	Py_DECREF(pType);

	npy_intp npLen = (npy_intp)uLen;
	PyObject* pObj = PyArray_SimpleNewFromDescr(1, &npLen, pDesc);
	if(pObj == NULL){
		PyErr_Format(g_pPyD2Error, "Couldn't generate new timedelta64 array ");
		return NULL;
	}
	PyArrayObject* pNdAry = (PyArrayObject*)pObj;

	if(! PyArray_ISBEHAVED(pNdAry) || !(PyArray_IS_C_CONTIGUOUS(pNdAry))){
		PyErr_Format(g_pPyD2Error, "New NDArray is not contiguous, aligned, and "
				                     "in machine byte order");
		Py_DECREF(pNdAry);
		return NULL;
	}

	/* Type branch to keep inner loops small */
	const ubyte* pUByte; const int8_t* pByte; 
	const int16_t* pShort; const uint16_t* pUShort;
	const uint32_t* pUInt; const int32_t* pInt; 
	const uint64_t* pULong; const int64_t* pLong;  
	const float* pFloat; const double* pDbl;
	double dTmp = 0.0;
	float  fTmp = 0.0f;
	npy_intp nd_index0[16] = {'\0'};
	int64_t* pNdData = (int64_t*) PyArray_GetPtr((PyArrayObject*)pNdAry, nd_index0);

	size_t u = 0;
	switch(vt){
	case vtUByte:
		for(pUByte = (const ubyte*)pMem, u = 0; u < uLen; ++u, ++pUByte, ++pNdData) {
			*pNdData = (long int)((*pUByte)*factor);
		}
		break;
	case vtByte:
		for(pByte = (const int8_t*)pMem, u = 0; u < uLen; ++u, ++pByte, ++pNdData) {
			*pNdData = (long int)((*pByte)*factor);
		}
		break;
	case vtShort:
		for(pShort = (const int16_t*)pMem, u = 0; u < uLen; ++u, ++pShort, ++pNdData) {
			*pNdData = (long int)((*pShort)*factor);
		}
		break;
	case vtUShort:
		for(pUShort = (const uint16_t*)pMem, u = 0; u < uLen; ++u, ++pUShort, ++pNdData) {
			*pNdData = (long int)((*pUShort)*factor);
		}
		break;
	case vtUInt:
		for(pUInt = (const uint32_t*)pMem, u = 0; u < uLen; ++u, ++pUInt, ++pNdData) {
			*pNdData = (long int)((*pUInt)*factor);
		}
		break;
	case vtInt:
		for(pInt = (const int32_t*)pMem, u = 0; u < uLen; ++u, ++pInt, ++pNdData) {
			*pNdData = (long int)((*pInt)*factor);
		}
		break;
	case vtULong:
		for(pULong = (const uint64_t*)pMem, u = 0; u < uLen; ++u, ++pULong, ++pNdData) {
			*pNdData = (long int)((*pULong)*factor);
		}
		break;
	case vtLong:
		for(pLong = (const int64_t*)pMem, u = 0; u < uLen; ++u, ++pLong, ++pNdData) {
			*pNdData = (long int)((*pLong)*factor);
		}
		break;
	case vtFloat:
		/* Problem for time deltas!  The common fill value -1e31 is less than
		 * minimum possible long int!  We need to convert these fill values to
		 * something that is possible. */
		for(pFloat = (const float*)pMem, u = 0; u < uLen; ++u, ++pFloat, ++pNdData) {
			fTmp = (float) ((*pFloat) * factor);
			if((fTmp < LONG_MIN)||(fTmp > LONG_MAX))
				*pNdData = DAS_INT64_FILL;
			else
				*pNdData = (long int)(fTmp);
		}
		break;
	case vtDouble:
		/* See fill value problem above */
		for(pDbl = (const double*)pMem, u = 0; u < uLen; ++u, ++pDbl, ++pNdData) {
			dTmp = (*pDbl)*factor;
			if((dTmp < LONG_MIN)||(dTmp > LONG_MAX))
				*pNdData = DAS_INT64_FILL;
			else
				*pNdData = (long int)(dTmp);
		}
		break;
	default:
		PyErr_Format(g_pPyD2Error, "Type vt = %d not supported in conversion "
				       "to timedelta64", vt);
		Py_DECREF(pNdAry);
		return NULL;
	}

	/* Reshape the array (hopefully IN PLACE, don't know how to insure this) */
	npy_intp np_shape[16] = {0};
	PyArray_Dims np_dims = {np_shape, 0};
	_npdims_from_shape(pAry, &np_dims);
	PyObject* pFinal = PyArray_Newshape((PyArrayObject*)pNdAry, &np_dims, NPY_CORDER);
	Py_DECREF(pNdAry);

	return pFinal;
}

/* ************************************************************************ */
/* Allocs each string's memory and the ndarray memory (slow)                */

PyObject* _DasTextAryToNumpyAry(DasAry* pAry)
{
	das_val_type vt = DasAry_valType(pAry);

	/* Das2 vtText type is used for arrays of constant pointers to null
	 * terminated strings.  Since there's so many things that can go wrong
	 * with not owning your own memory, I don't use it much, but it does
	 * exist.  vtByte is much more common */

	if((vt != vtText)&&(vt != vtByte)){
		PyErr_Format(g_pPyD2Error, "Logic error in %s,%d", __FILE__, __LINE__);
		return NULL;
	}

	ptrdiff_t shape[16] = {0};
	int nRank = DasAry_shape(pAry, shape);
	int nAsRank = nRank;

	if(vt == vtByte) nAsRank = nRank - 1; /* For these arrays, last index is
													   * just the character count */

	/* Make sure we aren't ragged (except for the last dimension of vtByte
	 * arrays of coarse. */
	for(int d = 0; d < nAsRank; ++d){
		if(shape[d] == DASIDX_RAGGED){
			PyErr_Format(g_pPyD2Error, "Ragged array translation is not yet implemented");
			return NULL;
		}
	}

	int i;
	npy_intp np_shape[16] = {0};
	for(i = 0; i < nAsRank; ++i) np_shape[i] = shape[i];

	/* Create the array allocating space for the pointers */
	PyObject* pObj = PyArray_SimpleNew(nAsRank, np_shape, NPY_OBJECT);
	PyArrayObject* pNdAry = (PyArrayObject*)pObj;

	if(! PyArray_ISCONTIGUOUS(pNdAry) || ! PyArray_ISBEHAVED(pNdAry)){
		PyErr_Format(g_pPyD2Error, "New NDArray is not behaved");
		Py_DECREF(pNdAry);
		return NULL;
	}
	if(! PyDataType_REFCHK( PyArray_DESCR(pNdAry) ) ){
		PyErr_Format(g_pPyD2Error, "New NDArray is not handling reference "
				       "counting for us");
		Py_DECREF(pNdAry);
		return NULL;
	}

	/* We have to do formal multidimensional iteration instead of just getting
	 * the memory pointer and doing a flat iteration because the strings in
	 * vtByte could contain many nulls in a row. There's no guaruntee that each
	 * string has only a single null at the end. */
	npy_intp np_index[16] = {0};
	ptrdiff_t d2_index[16] = {0};

	const void* pItem = NULL;
	const char* sStr = NULL;
	PyObject** ppSet = NULL;
	PyObject* pStr = NULL;
	size_t uStrLen = 0;

	bool bNext = (DasAry_size(pAry) > 0);
	while(bNext){
		pItem = DasAry_getIn(pAry, vt, nAsRank, (ptrdiff_t*)d2_index, &uStrLen);

		if(vt == vtText) sStr = *( (const char**) pItem);
		else sStr = (const char*) pItem;

		ppSet = (PyObject**) PyArray_GetPtr(pNdAry, np_index);

		if((sStr != NULL)&&(sStr[0] != '\0')){
			pStr = PyString_FromString(sStr);
		}
		else{
			pStr = Py_None;
			Py_INCREF(Py_None);
		}
		*ppSet = pStr;

		/* Don't dec the reference here, the numpy object owns it */

		/* Next index please... */
		bNext = false;
		for(i = nAsRank - 1; i >= 0; --i){
			if(d2_index[i] < (shape[i] - 1)){
				d2_index[i] += 1;
				np_index[i] += 1;
				bNext = true;
				break;
			}
			else{
				d2_index[i] = 0;
				np_index[i] = 0;
			}
		}
	}
	return (PyObject*)pNdAry; /* Cast it back */
}

/* ************************************************************************ */
/* Convert a DasAry to NDarray with coping data (fast)                      */

static PyObject* _DasGenericAryToNumpyAry(DasAry* pAry)
{
	char sInfo[64] = {'\0'};        /* For error messages */
	DasAry_toStr(pAry, sInfo, 63);

	npy_intp pa_shape[16] = {0};
	PyArray_Dims np_dims = {pa_shape, 0};
	_npdims_from_shape(pAry, &np_dims);

	/* Assume check in higher level function for raggedness */
	int nType = 0;
	das_val_type et = DasAry_valType(pAry);
	switch(et){
	case vtUByte:  nType = NPY_UINT8; break;
	case vtByte:   nType = NPY_INT8; break;
	case vtUShort: nType = NPY_UINT16; break;
	case vtShort:  nType = NPY_INT16; break;
	case vtUInt:   nType = NPY_UINT32; break;
	case vtInt:    nType = NPY_INT32; break;
	case vtULong:  nType = NPY_UINT64; break;
	case vtLong:   nType = NPY_INT64; break;
	case vtFloat:  nType = NPY_FLOAT32; break;
	case vtDouble: nType = NPY_FLOAT64; break;
	default:
		/* Can't handle unknown types for now, could return these as just byte */
		/* blobs to python in the future, might be handy for telemetry */
		PyErr_Format(g_pPyD2Error, "Logic error in %s,%d", __FILE__, __LINE__);
		return NULL;
	}

	/* Make sure das2 arrays don't delete their data when free'ed */
	size_t uLen = 0;
	size_t uOffset = 0;
	ubyte* pMem = DasAry_disownElements(pAry, &uLen, &uOffset);
	PyObject* pNdAry = NULL;
	
	if(uLen != 0){
		if(pMem == NULL){
			PyErr_Format(g_pPyD2Error, "Array %s does not own it's elements",sInfo);
			return NULL;
		}
		if(uOffset > 0){
			PyErr_Format(g_pPyD2Error, "Array %s has head trim, update das2py",sInfo);
			free(pMem);  /* You owned it, so clean it up */
			return NULL;
		}

		pNdAry = PyArray_SimpleNewFromData(np_dims.len, np_dims.ptr, nType, pMem);

		/* Interface is incomplete if we have to do a cast like this just to
		 * give memory away.  Will be REALLY nice to stop supporting Centos 6
		 * and it's ancient libraries. */
		/* ((PyArrayObject*)pNdAry)->flags |= NPY_OWNDATA;  // for numpy < 1.7 */
		PyArray_ENABLEFLAGS((PyArrayObject*)pNdAry, NPY_ARRAY_OWNDATA);
	}
	else{
		pNdAry = PyArray_SimpleNew(np_dims.len, np_dims.ptr, nType);
	}

	return pNdAry;
}

/* ************************************************************************ */
/* Converting any* DasAry to ndarray without a data copy if possible        */

/* Note that DasAry is more flexible in one respect in that all it's
 * dimensions can be ragged.  Since ndarrays allow for masks we can get around
 * numpy's limitation by making a cubic array and giving it a mask.  For now
 * I'm just not supporting ragged arrays (except of vtByte arrays that store
 * strings) since das 2.2 streams don't have them anyway.
 *
 * * TODO: Handling mask creation for ragged arrays
 *
 * Basic conversion is handled as follows:
 *
 *  1. If the units of the array are epoch times (no matter the data type),
 *     generate an array of numpy datetime64 objects with units ns (nanoseconds).
 *
 *  2. If the units of the array are convertible to seconds (no mater the
 *     data type), output an array of numpy timedelta64 objects.
 *
 *  3. If the type of the array is vtText (no matter the units), or if the type
 *     is vtByte and the flag D2ARY_AS_STRING is set, output a python string
 *     object array
 *
 *  4. Otherwise output a generic C-aligned basic type array
 */
static PyObject* _DasAryToNumpyAry(DasAry* pAry)
{
	das_units units = DasAry_units(pAry);
	das_val_type vt = DasAry_valType(pAry);

	if((vt == vtTime) || Units_haveCalRep(units))
		return _DasCalAryToNumpyAry(pAry);

	if(Units_canConvert(units, UNIT_SECONDS))
		return _DasTimeAryToNumpyAry(pAry);

	unsigned int uFlags = DasAry_getUsage(pAry);
	if((vt == vtText) || ( (uFlags&D2ARY_AS_STRING) == D2ARY_AS_STRING) )
		return _DasTextAryToNumpyAry(pAry);

	return _DasGenericAryToNumpyAry(pAry);
}

/* ************************************************************************* */
/* Create python fill values from array fill values                          */
/* Note that the canonical DAS_FILL_VALUE only works for floating point      */
/* types.  If array is to be converted to a timedelta64 or datetime64 we     */
/* need to substitute fill values than are in range                          */

static PyObject* _DasAryFillToObj(DasAry* pAry)
{
	das_val_type vt = DasAry_valType(pAry);
	das_units    units = DasAry_units(pAry);
	const void* vpFill = DasAry_getFill(pAry);

	int64_t nFill = 0;
	double  rFill = 0.0;

	switch(vt){
	case vtUByte:  nFill = *((ubyte*)vpFill);    break;
	case vtByte:   nFill = *((int8_t*)vpFill);   break;
	case vtUShort: nFill = *((uint16_t*)vpFill); break;
	case vtShort:  nFill = *((int16_t*)vpFill);  break;
	case vtUInt:   nFill = *((uint32_t*)vpFill); break;
	case vtInt:    nFill = *((int32_t*)vpFill);  break;
	case vtULong:  nFill = *((uint64_t*)vpFill); break;
	case vtLong:   nFill = *((int64_t*)vpFill);  break;
	case vtFloat:  rFill = *((float*)vpFill);    break;
	case vtDouble: rFill = *((double*)vpFill);   break;
	case vtTime:  /* TODO: Handle fill value for das_time objects */
	case vtText:
		Py_INCREF(Py_None);
		return Py_None;
		break;
	default:
		/* Can't handle unknown types for now.  Would need a size call back */
		PyErr_Format(g_pPyD2Error, "Code logic error will setting fill value for "
				       "array %s", pAry->sId);
		return NULL;
	}
	
	/* This compliments code in _DasTimeAryToNumpyAry above.
	 * That function sets any values outside of LONG_MIN, LONG_MAX to 
	 * DAS_INT64_FILL, which is almost always what you want.
	 * 
	 * The fill value itself is scaled to nanoseconds as needed.
	 */
	double factor = 1.0;
	if(Units_haveCalRep(units) || Units_canConvert(units, UNIT_SECONDS)){
		
		/* Get the conversion factor to nanoseconds */
		if(Units_canConvert(units, UNIT_SECONDS)){
			factor = Units_convertTo(UNIT_SECONDS, 1.0, units);
			if(factor == DAS_FILL_VALUE){
				Py_INCREF(Py_None);
				return Py_None;
			}
			factor *= 1.0e+9;
		}
		/* TODO: Handle FILL for calendar time objects */
		
		if((vt == vtDouble)||(vt == vtFloat)){
			if((rFill*factor < LONG_MIN)||(rFill*factor > LONG_MAX))
				return PyLong_FromInt64(DAS_INT64_FILL);
			else
				return PyLong_FromInt64((int64_t)(rFill*factor));
		}	
		else{
			if((nFill*factor < LONG_MIN)||(nFill*factor > LONG_MAX)){
				return PyLong_FromInt64(DAS_INT64_FILL);
			}
			else
				return PyLong_FromInt64((int64_t)(nFill*factor));
		}
	}
	else{
		if((vt == vtDouble)||(vt == vtFloat))
			return PyFloat_FromDouble(rFill);
		else
			return PyLong_FromInt64(nFill);
	}
}

/* ************************************************************************* */
/* Create a dictionary of frames, or return Py_None  */

static PyObject* _frameDictionary(DasStream* pStream)
{
	int8_t uFrames = DasStream_getNumFrames(pStream);
	if(uFrames == 0)
		return Py_None;  /* caller takes ownership, I don't */

	PyObject* pFrames = PyDict_New();

	char sBuf[256] = {'\0'};
	for(int8_t u = 0; u < uFrames; ++u){
		const DasFrame* pFrame = DasStream_getFrame(pStream, u);
		DasFrame_info(pFrame, sBuf, 255);
		PyObject* pInfo = PyString_FromString( sBuf );
		PyDict_SetItemString(pFrames, DasFrame_getName(pFrame), pInfo);
	}
	return pFrames;
}

/* ************************************************************************* */
/* Convert DasDesc to Python dictionary of the form  name : (type, value)    */

static PyObject* _props2PyDict(DasDesc* pDesc)
{
	const char* sUnits = NULL;
	PyObject* pDict = PyDict_New();
	PyObject* pTup;

	size_t uProps = DasDesc_length(pDesc);
	for(size_t u = 0; u < uProps; ++u){

		const DasProp* pProp = DasDesc_getPropByIdx(pDesc, u);
		if(pProp == NULL) continue;  /* Unlikely, but possible */

		if((pProp->units == NULL)||(pProp->units[0] == '\0'))
			sUnits = "";
		else
			sUnits = pProp->units;
		char cSep = DasProp_sep(pProp);
		const char* sSep = "";
		if(cSep != '\0') sSep = &cSep;

		int nMultiplicity = 1;
		if(DasProp_isRange(pProp)) nMultiplicity = 2;
		else if(DasProp_isSet(pProp)) nMultiplicity = 3;

		pTup = Py_BuildValue("ssssi", 
			DasProp_typeStr3(pProp), DasProp_value(pProp), sUnits, sSep,
			nMultiplicity
		);
		
		if(pTup == NULL){
			Py_DECREF(pDict); return NULL;
		}
		if(PyDict_SetItemString(pDict, DasProp_name(pProp), pTup) != 0){
			Py_DECREF(pTup); Py_DECREF(pDict); return NULL;
		}
	}
	return pDict;
}

/* Here's what we are going to output from each of the builder calls.
 * Right now it can only handle mapping square arrays.  Currently there
 * is no wrapper around DasVar, so no fancy operations are possible.
 *
 * All the structure keys start with '_'.  It is assumed that higher level
 * pure python code will handle reworking these raw dictionaries into something
 * slightly easier to access.
 *
 * Maybe like this:
 *
 *   time_at_index = d.coords['time']['center'][1, 27]
 *   freq_at_index = d.coords['freq']['center'][1, 27]
 *   ampl_at_index = d.coords['ampl']['center'][1, 27]
 *
 * To do this the variable class will need to be reimplemented on the python
 * side of the fence, but that should be easier and more useful than making a
 * C-wrapper around DasVar and keeping all data in our own arrays, even though
 * they can handle arbitrarily ragged items.
 *
 * d = {
 *   '_version': 	DasStream.version
 *   '_props':    DasStream.properties
 *   'frames':   {
 *       DasFrame.id: { 
 *         '_id':         DasFrame.id   (int)   
 *         'expression':  DasFrame_info (string)
 *         '_props':      DasFrame.properties (Dictionary)
 *       }
 *    }
 * }
 *
 * l =
 * [                        (list of dictionaries, 1 dict / dataset )
 *   {
 *    '_props':   DasDs.properties (Dictionary)
 *		'_rank':    DasDs.nRank,     (int)
 *		'_id':      DasDs.sId,       (string)
 *		'_group':   DasDs.sGroupId,  (string)
 *    'shape':    DasDs.shape,     (int tuple)
 *
 *		'_coords':  {         (Dictionary of coordinate dimensions)
 *       DasDim.sId: {
 *         '_id':        DasDim.sId
 *         '_props':      DasDim.properties (Dictionary)
 *         '_offset':    (None or some other dimension's name)
 *         '_type':      'COORD_DIM'
 *
 *          DasDim.aRole[i] : {
 *            '_role'     : DasDim.aRole[i]
 *            '_units'    : DasVar.units
 *            '_idxmap'   : [ List of Ds.nRank ints ]
 *            '_isVec'    : True if last index is to be treated as geometric vector
 *            'expression': [ concrete definition of variable, including arrays ]
 *           }
 *           ... (next variable)
 *        }
 *        ... (next dimension)
 *     }
 *
 *    '_data':  {         (Dictionary of coordinate dimensions)
 *       DasDim.sId: {
 *         '_props':      DasDim.properties (Dictionary)
 *         '_id':         DasDim.sId
 *         '_offset':     (None or some other dimension's name)
 *         '_type':       'DATA_DIM'
 *
 *         DasDim.aRole[i] : {
 *            '_role'  :  DasDim.aRole[i]
 *            '_units' : DasVar.units
 *            'expression' : [ concrete definition of variable includes arrays ]
 *            '_isVec' : True for geometric vectors
 *            'array'  : sArray (key in array dictionary below)
 *         }
 *         ... (next variable)
 *      }
 *      ... (next dimension)
 *    }
 *
 *	   'arrays': {
 *			sName : ndarray,
 *			sName : ndarray,
 *			sName : ndarray
 *		}
 *
 *		'fill' {
 *			sName : pyObj;
 *			sName : pyObj;
 *			sName : pyObj;
 *		}
 *  }
 *  ...
 * ]
 *
 *
 *  Higher level python code in the das2 module can take care of putting
 *  this dictionary into a dataset object
 */

static bool _addVars(int nDsRank, DasDim* pDim, PyObject* pDimDict)
{
	DasVar* pVar = NULL;
	PyObject* pVarDict = NULL;
	PyObject* pStr = NULL;
	/* PyObject* pIdxMap = NULL; */
	/*	PyObject* pInt = NULL;*/
	char sBuf[4096] = {'\0'};
	
	size_t v=0;
	/* size_t i=0; */
	for(v = 0; v < pDim->uVars; ++v){
		pVar = pDim->aVars[v];
		pVarDict = PyDict_New();

		pStr = PyString_FromString(pDim->aRoles[v]);
		PyDict_SetItemString(pVarDict, "role", pStr);
		Py_DECREF(pStr);

		/* the cal representation units all get converted to ns1970, in the
		 * _DasCalAryToNumpyAry function above.  Make the variable units match
		 * what the array units are going to be soon.  
		 * 
		 * Note: Array Variables do not check on the units of their arrays after
		 *       creation, so we are manually pre-updating the Variables to have
		 *       the correct units. 
		 * 
		 * Since the dataset toStr() and dimension toStr() both call down to the
		 * variables toStr() lets set the units now.
		 */
		if((pVar->vt == vtTime) || Units_haveCalRep(pVar->units))
			pVar->units = Units_fromStr("ns1970");
		
		/* all units convertable to seconds get converted to nano seconds in the
		 * _DasTimeAryToNumpyAry function above */
		if(Units_canConvert(pVar->units, UNIT_SECONDS))
			pVar->units = Units_fromStr("ns");
		
		
		pStr = PyString_FromString(pVar->units);	
		PyDict_SetItemString(pVarDict, "units", pStr);
		Py_DECREF(pStr);
		
		/* Save the expression that makes the variable */
		pStr = PyString_FromString(DasVar_toStr(pVar, sBuf, 4095));
		PyDict_SetItemString(pVarDict, "expression", pStr);
		Py_DECREF(pStr);

		/* Save the value type */
		const char* sValType = das_vt_toStr(DasVar_valType(pVar));
		pStr = PyString_FromString(sValType);
		PyDict_SetItemString(pVarDict, "valtype", pStr);
		Py_DECREF(pStr);

		const char* sFrameName = DasVar_getFrameName(pVar);
		if(sFrameName != NULL){
			pStr = PyString_FromString(sFrameName);
			PyDict_SetItemString(pVarDict, "frame", pStr);
			Py_DECREF(pStr);
		}
		else{
			PyDict_SetItemString(pVarDict, "frame", Py_None);
		}
		

		/* Could save each sub-variable, don't know about this yet */
		/* pIdxMap = PyList_New(nDsRank);
		for(i = 0; i < nDsRank; ++i){
			pInt = PyInt_FromLong(pVar->idxmap[i]);
			PyList_SetItem(pIdxMap, i, pInt);
		}
		PyDict_SetItemString(pVarDict, "_idxmap", pIdxMap);
		Py_DECREF(pIdxMap);
		 */

		PyDict_SetItemString(pDimDict, pDim->aRoles[v], pVarDict);
	}

	return true;
}


/* Takes in a DasStream object returns a 2-tuple of stream header plus datasets */
static PyObject* _Stream2Tuple(DasStream* pStream)
{
	DasDesc* pDesc = NULL;
	DasDs* pDs = NULL;
	DasDim* pDim = NULL;

	PyObject* pDsList = PyList_New( DasStream_getNPktDesc(pStream) );
	PyObject* pHdrDict = PyDict_New();

	/* Iteration variables used here */
	size_t d = 0; /* Dataset index */
	size_t a = 0; /* Array index */
	size_t m = 0; /* Dimension index */

	ptrdiff_t shape[DASIDX_MAX] = {0};
	int nRank, i = 0;
	DasAry* pDasAry = NULL;

	char sInfo[4096] = {'\0'};
	/* char sInfo[32768] = {'\0'}; */

	/* Before going through all the setup, see if the Das Arrays can even be
	 * converted to ndarrays with this extension.  Once code has been written
	 * to generate ragged ndarrays, remove this check */
	int nPktId = 0;
	while((pDesc = DasStream_nextDesc(pStream, &nPktId)) != NULL){
		
		if(DasDesc_type(pDesc) != DATASET){
			PyErr_Format(g_pPyD2Error,
				"Error in das2C, invalid descriptor type returned by DasDsBldr: %d",
				DasDesc_type(pDesc)
			);
		}
		pDs = (DasDs*)pDesc;

		for(a = 0; a < pDs->uArrays; ++a){
			pDasAry = pDs->lArrays[a];

			/* Make sure the das array does not contain a user defined type */
			if(DasAry_valType(pDasAry) == vtUnknown){
				PyErr_Format(g_pPyD2Error,
					"Array %s from Dataset %s contains a generic type. "
					"Generic types are not supported by the python extension.",
					DasAry_toStr(pDasAry, sInfo, 63), pDs->sId
				);
			}

			DasAry_shape(pDasAry, shape);
			for(i = 1; i < pDasAry->nRank; ++i){

				if(shape[i] == DASIDX_RAGGED){

					/* Special exception if array is vtByte, has the flag
					 * D2ARY_AS_STRING and raggedness is only in the last dimension
					 * because I can turn these into cubic string object arrays */

					if((i == (pDasAry->nRank - 1)) &&
					   (DasAry_valType(pDasAry) == vtByte) &&
						((pDasAry->uFlags & D2ARY_AS_STRING)==D2ARY_AS_STRING) )
						continue;

					PyErr_Format(g_pPyD2Error,
						"Array %s from dataset %s is ragged.  Conversion "
						"of ragged DasArrays to NumPy ndarrays has not been "
						"implemented.", DasAry_toStr(pDasAry, sInfo, 63), pDs->sId
					);
					return NULL;
				}
			}
		}
		++d; // Increment the dataset index
	}
	memset(sInfo, 0, 64);

	PyObject* pFrames = NULL;
	PyObject* pDsDict = NULL;
	PyObject* pProps = NULL;
	PyObject* pStr = NULL;
	PyObject* pInt = NULL;
	PyObject* pCoordDict = NULL;
	PyObject* pDataDict = NULL;
	PyObject* pDict = NULL;
	PyObject* pDimDict = NULL;
	PyObject* pdArys = NULL;
	PyObject* pdFill = NULL;
	PyObject* pList = NULL;
	PyObject* pAry = NULL;
	PyObject* pObj = NULL;


	/* Handle the stream header conversion */
	pProps = _props2PyDict((DasDesc*)pStream);
	PyDict_SetItemString(pHdrDict, "props", pProps);
	pFrames = _frameDictionary(pStream);
	PyDict_SetItemString(pHdrDict, "frames", pFrames);
	DasStream_info(pStream, sInfo, 4095);
	pStr = PyString_FromString(sInfo);
	PyDict_SetItemString(pHdrDict, "info", pStr);
	Py_DECREF(pStr);

	/* Note: PyDict_SetItem and PyList_SetItem handle reference counts
	 * differently.  Dicts increment the ref count when you hand them an
	 * item.  So if you don't want to own the item you have to decrement the
	 * count.  Lists just assume that you wanted them to own the item so they
	 * don't increment the count, but they do assume they can decrement it at
	 * will.  So... call Py_DECREF for dicts, but not for lists.  */

	nPktId = 0;
	d = 0;
	while((pDesc = DasStream_nextDesc(pStream, &nPktId)) != NULL){

		if(DasDesc_type(pDesc) != DATASET){
			PyErr_Format(g_pPyD2Error,
				"Error in das2C, invalid descriptor type returned by DasDsBldr: %d",
				DasDesc_type(pDesc)
			);
		}
		pDs = (DasDs*)pDesc;

		/* Convert the properties */
		pProps = _props2PyDict((DasDesc*)pDs);
		if(pProps == NULL) return NULL;

		pDsDict = PyDict_New();
		PyDict_SetItemString(pDsDict, "props", pProps);
		Py_DECREF(pProps);

		pInt = PyInt_FromLong(pDs->nRank);
		PyDict_SetItemString(pDsDict, "rank", pInt);
		Py_DECREF(pInt);

		pStr = PyString_FromString(pDs->sId);
		PyDict_SetItemString(pDsDict, "id", pStr);
		Py_DECREF(pStr);

		pStr = PyString_FromString(pDs->sGroupId);
		PyDict_SetItemString(pDsDict, "group", pStr);
		Py_DECREF(pStr);

		/* Don't save the info string yet.  Converting to numpy datetime64 
		 * may alter the DasVar units... */
		
		nRank = DasDs_shape(pDs, shape);
		pList = PyList_New(nRank);
		for(i = 0; i < nRank; ++i){
			pInt = PyLong_FromInt64(shape[i]);
			PyList_SetItem(pList, i, pInt);
		}
		PyDict_SetItemString(pDsDict, "shape", pList);
		Py_DECREF(pList);

		/* Coordinate & Data dictionaries, we always have these even if they
		 * are empty, so just attach them now and dec my refs */
		pCoordDict = PyDict_New();
		PyDict_SetItemString(pDsDict, "coords", pCoordDict);
		Py_DECREF(pCoordDict);

		pDataDict = PyDict_New();
		PyDict_SetItemString(pDsDict, "data", pDataDict);
		Py_DECREF(pDataDict);

		for(m = 0; m < pDs->uDims; ++m){
			pDim = pDs->lDims[m];

			/* Create and add the dimension dictionary to the right category */
			pDimDict = PyDict_New();
			pDict = pDim->dtype == DASDIM_COORD ? pCoordDict : pDataDict;
			PyDict_SetItemString(pDict, pDim->sId, pDimDict);
			Py_DECREF(pDimDict);

			/* Fill in information for this dimension */
			pStr = PyString_FromString(
				pDim->dtype == DASDIM_COORD ? "COORD_DIM" : "DATA_DIM"
			);
			PyDict_SetItemString(pDimDict, "type", pStr);
			Py_DECREF(pStr);

			pProps = _props2PyDict((DasDesc*)pDim);
			if(pProps == NULL){ Py_DECREF(pDsDict); return NULL; }
			
			PyDict_SetItemString(pDimDict, "props", pProps);
			Py_DECREF(pProps);

			if( ! _addVars(pDs->nRank, pDim, pDimDict)){
				Py_DECREF(pDsDict); return NULL;
			}
		}

		/* Arrays and their fill values */
		pdArys = PyDict_New();
		pdFill = PyDict_New();
		for(a = 0; a < pDs->uArrays; ++a){
			pAry = _DasAryToNumpyAry(pDs->lArrays[a]);
			if(pAry == NULL){
				Py_DECREF(pdFill); Py_DECREF(pdArys); Py_DECREF(pDsDict);
				Py_DECREF(pDsList);
				return NULL;
			}
			PyDict_SetItemString(pdArys, pDs->lArrays[a]->sId, pAry);
			Py_DECREF(pAry);

			pObj = _DasAryFillToObj(pDs->lArrays[a]);
			if(pObj == NULL){
				Py_DECREF(pdFill); Py_DECREF(pdArys); Py_DECREF(pDsDict);
				Py_DECREF(pDsList);
				return NULL;
			}
			PyDict_SetItemString(pdFill, pDs->lArrays[a]->sId, pObj);
			Py_DECREF(pObj);
		}
		PyDict_SetItemString(pDsDict, "arrays", pdArys);
		PyDict_SetItemString(pDsDict, "fill",  pdFill);
		Py_DECREF(pdArys);
		Py_DECREF(pdFill);
		
		/* okay, now it's safe to save the dataset info string, AFTER any unit
		 * conversions that may have taken place */
		char* pInfo = DasDs_toStr(pDs, sInfo, 4095);
		if(pInfo == NULL){
			char* pTmp = (char*) calloc(65536, sizeof(char));
			pInfo = DasDs_toStr(pDs, pTmp, 65535);
			if(pInfo == NULL){
				free(pTmp);
				PyErr_Format(g_pPyD2Error,
					"Dataset description is > 64 KB, update py_builder.h if you want to "
					"handle datasets with this many variables."
				);
				return NULL;
			}
			pStr = PyString_FromString(sInfo);
			free(pTmp);
		}
		else{
			pStr = PyString_FromString(sInfo);
		}
		PyDict_SetItemString(pDsDict, "info", pStr);
		Py_DECREF(pStr);

		/* Attach correlated dataset converted to python objects */
		PyList_SetItem(pDsList, d, pDsDict);

		++d; 
	}

	return Py_BuildValue("(OO)", pHdrDict, pDsList);
}

/* ************************************************************************* */
const char pyd2help_read_file[] =
"Reads a Das2 stream from a disk file and returns a stream header and a list\n"
"of DasDs (das dataset) objects containing the data in the stream\n"
"\n"
"Thread Note:  This function releases the global interpreter lock during stream\n"
"              reading\n"
"\n"
"Args:\n"
"   sFile (str) : The filename to read\n"
"\n"
"Return:\n"
"   A two-tuple consisting of a stream header dictionary and a list of correlated\n"
"   datasets.  The stream header is a dictionary with the following keys:\n"
"\n"
"     * 'props' - A list of dictionaries providing metadata about the overall stream\n"
"     * 'frames' - A list of dictionaries providing vector frame definitions, if any.\n"
"\n"
"Each correlated dataset is a dictionary with the with the following keys and items:\n"
"\n"
"   * 'rank' - The number of array dimensions in each dataset\n"
"   * 'id'   - A string containing an identifier token usable as a variable name\n"
"   * 'group' - A string containing the join group for this Correlated dataset\n"
"   * 'shape' - An array containing the maximum index value in each dimension\n"
"   * 'coords' - A list of coordinate dictionaries (defined below)\n"
"   * 'datasets' - A list of datasets correlated in the given coordinates (see below)\n"
"   * 'arrays' - A dictionary of all the backing ndarrays for the dataset (see below)\n"
"   * 'props' - A list of dictionaries providing metadata about the dataset\n"
"   * 'info' - An information string about the dataset"
"\n"
"  Each item in 'coords' or 'data' is a dimension object that has the following keys\n"
"\n"
"   * 'type' - One of COORD_DIM or DATA_DIM\n"
"   * 'props' - A string containing the units of the coordinate\n"
"\n"
"  and one or more of the following optional keys:\n"
"\n"
"   * 'center' - A variable definition for data center values\n"
"   * 'reference' - A variable definition for data reference point (ususally start) values\n"
"   * 'offset' - A variable definition for data offset value, to be added to reference\n"
"\n"
"  Other variable definitions may follow for min, max, stddev etc. values in a dimension\n"
"\n";

static PyObject* pyd2_read_file(PyObject* self, PyObject* args)
{
	const char* sFile;
	int nRet = DAS_OKAY;

	if(!PyArg_ParseTuple(args, "s:read_file", &sFile))
		return NULL;

	DasIO* pIn = new_DasIO_file("das2py", sFile, "r");
	if(pIn == NULL) return pyd2_setException(g_pPyD2Error);

	DasDsBldr* pBldr = new_DasDsBldr();
	if(pBldr == NULL) return pyd2_setException(g_pPyD2Error);
	DasIO_addProcessor(pIn, (StreamHandler*)pBldr);

	/* Release the GIL while doing I/O */
	Py_BEGIN_ALLOW_THREADS
	nRet = DasIO_readAll(pIn);
	Py_END_ALLOW_THREADS

	if(nRet != DAS_OKAY){
		del_DasIO(pIn);
		del_DasDsBldr(pBldr);
		return pyd2_setException(g_pPyD2Error);
	}

	/* Build python list of dataset objects here */
	DasStream* pStream = DasDsBldr_getStream(pBldr);
	DasDsBldr_release(pBldr); /* Free the correlated datasets from builder mem */
	PyObject* pRet = (pStream != NULL) ? _Stream2Tuple(pStream) : NULL;
	del_DasStream(pStream);  /* arrays don't own re-used data and may be freed */
	del_DasIO(pIn);

	return pRet;
}

/* ************************************************************************* */
static const char pyd2help_read_server[] =
"read_server(sUrl, sAgent=None)\n"
"\n"
"Reads a Das2 stream from a remote HTTP/HTTPS server.\n"
"\n"
"Note:\n"
"   This function releases the global interpreter lock during data download\n"
"\n"
"Args:\n"
"   sUrl (str) : The URL to read, can be an extensive GET string\n"
"   rConSec (float, optional) : How long to wait on the connection to the\n"
"      remote server in seconds.  A value of <= 0.0 means wait as long as\n"
"      the operating system allows."
"   sAgent (str,optional) : The user agent string you'd like to use\n"
"\n"
"Returns:\n"
"   This function has the same return as :ref:`read_file`.\n"
"\n"
;

/* Read in das2 stream from a server */
static PyObject* pyd2_read_server(PyObject* self, PyObject* args)
{
	const char* sInitialUrl = "https://planet.physics.uiowa.edu/das/das2Server"
	       "?server=dataset&dataset=Galileo/PWS/Survey_Electric"
	       "&start_time=2001-001&end_time=2001-002";
	const char* sUserAgent = NULL;
	float rConSec = DASHTTP_TO_MIN * DASHTTP_TO_MULTI;
	if(!PyArg_ParseTuple(args, "s|fs:read_server", &sInitialUrl, &rConSec,
			               &sUserAgent))
		return NULL;

	bool bOkay = false;
	DasHttpResp res;
	PyObject* pExcept = g_pPyD2Error;
	PyObject* pRet = NULL;

	/* Release the GIL while the connection processes */
	Py_BEGIN_ALLOW_THREADS
	bOkay = das_http_getBody(sInitialUrl, sUserAgent, g_pMgr, &res, rConSec);
	Py_END_ALLOW_THREADS

	if(!bOkay){
		if((res.nCode == 401)||(res.nCode == 403)) pExcept = g_pPyD2AuthErr;
		if((res.nCode == 400)||(res.nCode == 404)) pExcept = g_pPyD2QueryErr;
		if(pExcept == NULL) pExcept = g_pPyD2Error;

		pRet = PyErr_Format(pExcept, "%d, Could not get body for URL, reason: %s",
		                    res.nCode, res.sError);
		DasHttpResp_clear(&res);
		return pRet;
	}
	char sUrl[512] = {'\0'};
	das_url_toStr(&(res.url), sUrl, 511);
	if(strcmp(sUrl, sInitialUrl) != 0)
		daslog_info_v("Redirected to %s", sUrl);

	DasIO* pIn;

	if(DasHttpResp_useSsl(&res))
		pIn = new_DasIO_ssl("das2py", res.pSsl, "r");
	else
		pIn = new_DasIO_socket("das2py", res.nSockFd, "r");

	DasIO_model(pIn, -1);  /* Allow all stream versions */

	DasDsBldr* pBldr = new_DasDsBldr();
	DasIO_addProcessor(pIn, (StreamHandler*)pBldr);

	int nRet = DAS_OKAY;

	/* Release the GIL while processing the message body */
	Py_BEGIN_ALLOW_THREADS
	nRet = DasIO_readAll(pIn);
	Py_END_ALLOW_THREADS

	if(nRet != DAS_OKAY){
		/* Bounce das2 error message to python's error facility */
		del_DasIO(pIn);
		del_DasDsBldr(pBldr);

		pRet = pyd2_setException(g_pPyD2Error);
		DasHttpResp_clear(&res);
		return pRet;
	}

	/* Build python list of dataset objects here */
	DasStream* pStream = DasDsBldr_getStream(pBldr);
	DasDsBldr_release(pBldr); /* Free the correlated datasets from builder mem */
	pRet = (pStream != NULL) ? _Stream2Tuple(pStream) : NULL;
	del_DasStream(pStream);  /* arrays don't own re-used data and may be freed */
	DasHttpResp_clear(&res);
	del_DasIO(pIn);

	return pRet;
}


/* ************************************************************************* */
const char pyd2help_read_cmd[] =
"read_cmd(sCmd)\n"
"\n"
"Reads a Das2 stream from an external program and returns a list of dictionaries\n"
"that describe dataset and hold the NumPy arrays containing the data.\n"
"\n"
"Note:\n"
"   This function releases the global interpreter lock during data download\n"
"\n"
"Args:\n"
"   sCmd (str) : The reader command line to run.  Standard output from the\n"
"      command is expected to be a das2 stream."
"\n"
"Returns:\n"
"   This function has the same return as :ref:`read_file`.\n"
"\n"
;

static PyObject* pyd2_read_cmd(PyObject* self, PyObject* args)
{

	const char* sCmd;

	if(!PyArg_ParseTuple(args, "s:read_cmd", &sCmd))
		return NULL;

	DasIO* pIn = new_DasIO_cmd("das2py", sCmd);
	if(pIn == NULL )	return pyd2_setException(g_pPyD2Error);
	
	DasDsBldr* pBldr = new_DasDsBldr();
	if(pBldr == NULL){
		del_DasIO(pIn);
		return pyd2_setException(g_pPyD2Error);
	}
	
	DasIO_addProcessor(pIn, (StreamHandler*)pBldr);

	int nRet = DAS_OKAY;

	/* Release the GIL while processing the command output */
	Py_BEGIN_ALLOW_THREADS
	nRet = DasIO_readAll(pIn);
	Py_END_ALLOW_THREADS

	if(nRet != DAS_OKAY){
		del_DasIO(pIn);
		del_DasDsBldr(pBldr);
		return pyd2_setException(g_pPyD2Error);  /* Bounce das2 err msg to python */
	}

	/* Build python list of dataset objects here */
	DasStream* pStream = DasDsBldr_getStream(pBldr);
	DasDsBldr_release(pBldr); /* Free the correlated datasets from builder mem */
	PyObject* pRet = (pStream != NULL) ? _Stream2Tuple(pStream) : NULL;
	del_DasStream(pStream);  /* arrays don't own re-used data and may be freed */
	del_DasIO(pIn);

	return pRet;
}
