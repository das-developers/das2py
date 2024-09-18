/* Copyright (C) 2015-2017 Edward West
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
 * version 2.1 along with Das2py; if not, see <http://www.gnu.org/licenses/>. 
 */

/* Will be included directly as a *.c file, no need to declare as posix source
   or to include Python.h or numpy/arrayobject */



#include <stdbool.h>
#include <Python.h>
#include <numpy/arrayobject.h>
/* Can't do this until we drop support for centos 6 */
/* #define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION */


#include <das2/util.h>
#include <das2/time.h>
#include <das2/dft.h>

/* Python 2 doesn't have the Py_TYPE function but Python 3 does */
/* Make code analzer happy, add this a second time */
#ifndef Py_TYPE
#define Py_TYPE(ob) (((PyObject*)(ob))->ob_type)
#endif


/*****************************************************************************/
/* Dft type definition */

/* THIS CODE USES AND OLD VERSION OF NUMPY ON PURPOSE!  We still need to 
 * support CentOS 6 and it's ancient 1.4 version of numpy.  Don't upgrade
 * these calls! */

/* instance structure */
typedef struct {
	PyObject_HEAD
	DftPlan* dftplan;
	Das2Dft* das2dft;
} pyd2_Dft;

static void pyd2_Dft_dealloc(pyd2_Dft* self) {
	if (self->das2dft)
		del_Dft(self->das2dft);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* pyd2_Dft_new(
	PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	pyd2_Dft* self;

	self = (pyd2_Dft*)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->das2dft = NULL;
		self->dftplan = NULL;
	}

	return (PyObject*)self;

}

static int pyd2_Dft_init(pyd2_Dft* self, PyObject *args, PyObject *kwds) {

	char *sWindow = NULL;
	unsigned int uLen = 0;
	PyObject* pForward = NULL;
	bool bForward = true;
	das_error_msg* errMsg;

	static char *kwlist[] = {"uLen", "sWindow", "bForward", NULL};

	if (! PyArg_ParseTupleAndKeywords(args, kwds, "Izo", kwlist,
		&uLen, &sWindow))
	{
		return -1;
	}		
	
	if ( self->das2dft != NULL ) {
		del_Dft(self->das2dft);
		del_DftPlan(self->dftplan);
		self->das2dft = NULL;
		self->dftplan = NULL;
	}
	bForward = PyObject_IsTrue(pForward);
	self->dftplan = new_DftPlan(uLen, bForward);
	self->das2dft = new_Dft(self->dftplan, sWindow);

	if ( self->das2dft == NULL ) {
		errMsg = das_get_error();
		PyErr_SetString(PyExc_ValueError, errMsg->message);
		return -1;
	}

	return 0;
}

const char das2help_Dft_calculate[] =
	"Calculate a discrete Fourier transform.\n"
	"\n"
	"Using the calculation plan setup in the constructor, calculate a\n"
	"discrete Fourier transform.  When this function is called internal\n"
	"storage of any previous DFT calculations (if any) are over written.\n"
	"	Arguments\n"
	"		pReal    A \"time domain\" input vector\n"
	"		pImg     The imaginary (or quadrature phase) input vector. For \n"
	"		         a purely real signal this vector is None\n"
	"A ValueError is thrown if  pImg is not None and a different length\n"
	"             than pReal\n"
	"A ValueError is thrown if the length of pImg is odd or less than 2.\n";

static PyObject* pyd2_Dft_calculate(pyd2_Dft* self, PyObject* args) {
	PyObject* pReal = NULL;
	PyObject* pImg = Py_None;
	PyObject* pObjReal = NULL;
	PyObject* pObjImg = NULL;
	double* dReal;
	double* dImg;
	size_t uLen;
	DasErrCode err;
	das_error_msg* errMsg;
	char* tmp;
	

	if (!PyArg_ParseTuple(args, "O|O:calculate", &pReal, &pImg)) {
		return NULL;
	}

	pObjReal = PyArray_FROM_OTF(pReal, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
	if (pObjReal == NULL) {
		return NULL;
	}

	if (pImg == Py_None) {
		pObjImg = Py_None;
		Py_INCREF(Py_None);
	}
	else {
		pObjImg = PyArray_FROM_OTF(pImg, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
		if (pObjImg == NULL) {
			Py_DECREF(pObjReal);
			return NULL;
		}
	}

	if((! PyArray_Check(pObjReal)) || (! PyArray_Check(pObjImg))){
		PyErr_SetString(PyExc_TypeError, "Unexpected type in pyd2_Dft_calculate()");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}

	/* Make to pointers that are the exact same address as the generic 
	   object pointers, except they have be cast to the expected type to
	   make the compiler happy.  The PyArray_Check function above make
	   sure this is okay. */
	PyArrayObject* pAryReal = (PyArrayObject*)pObjReal;
	PyArrayObject* pAryImg = (PyArrayObject*)pObjImg;

	if ( PyArray_NDIM(pAryReal) != 1 ) {
		PyErr_SetString(PyExc_ValueError, "pReal is not 1-dimensional");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}
	if ( pObjImg != Py_None && PyArray_NDIM(pAryImg) != 1 ) {
		PyErr_SetString(PyExc_ValueError, "pImg is not 1-dimensional");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}

	uLen = PyArray_Size(pObjReal);
	if ( pObjImg != Py_None && ((ptrdiff_t)uLen) != PyArray_Size(pObjImg) ) {
		PyErr_SetString(PyExc_ValueError, "pReal and pImg must be the same length");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}

	dReal = (double*)PyArray_DATA(pAryReal);
	if (pObjImg == Py_None) {
		dImg = NULL;
	}
	else {
		dImg = (double*)PyArray_DATA(pAryImg);
	}

	err = Dft_calculate(self->das2dft,dReal,dImg);
	if ( err != DAS_OKAY ) {
		errMsg = das_get_error();
		if (err == errMsg->nErr) {
			tmp = errMsg->message;
		}
		else {
			tmp = "Unknown error";
		}
		PyErr_SetString(PyExc_ValueError, tmp);
	}

	Py_DECREF(pObjReal);
	Py_DECREF(pObjImg);
	
	Py_RETURN_NONE;
}

const char das2help_Dft_getReal[] =
	"Return the real component after a calculation.";

static PyObject* pyd2_Dft_getReal(pyd2_Dft* self, PyObject* noargs) {
	PyObject* pObjReal;
	size_t pLen;
	const double* pReal;
	npy_intp dims;

	pReal = Dft_getReal(self->das2dft,&pLen);

	dims = pLen;
	pObjReal = PyArray_SimpleNew(1,&dims,NPY_DOUBLE);
	if (pObjReal==NULL) {
		return NULL;
	}

	/* Hey NumPy! Why does simpleNew return pyObject when every
	   other function is going to want a pyArrayObject? */
	if(! PyArray_Check(pObjReal) ){
		PyErr_SetString(PyExc_TypeError, "Unexpected type in pyd2_Dft_getReal()");
		Py_DECREF(pObjReal);
		return NULL;
	}

	memcpy(PyArray_DATA((PyArrayObject*)pObjReal),pReal,sizeof(double)*pLen);

	return pObjReal;
}

const char das2help_Dft_getImg[] =
	"Return the imaginary component after a calculation.";

static PyObject* pyd2_Dft_getImg(pyd2_Dft* self, PyObject* noargs) {
	PyObject* pObjImg;
	size_t pLen;
	const double *img;
	npy_intp dims;

	img = Dft_getImg(self->das2dft,&pLen);

	dims = pLen;
	pObjImg = PyArray_SimpleNew(1,&dims,NPY_DOUBLE);
	if (pObjImg==NULL) {
		return NULL;
	}
	if(! PyArray_Check(pObjImg) ){
		PyErr_SetString(PyExc_TypeError, "Unexpected type in pyd2_Dft_getImg()");
		Py_DECREF(pObjImg);
		return NULL;
	}

	memcpy(PyArray_DATA((PyArrayObject*)pObjImg),img,sizeof(double)*pLen);

	return pObjImg;
}

const char das2help_Dft_getMagnitude[] =
	"Get the amplitude magnitude vector from a calculation.\n"
	"\n"
	"Scale the stored DFT so that it preserves amplitude, and get the\n"
	"magnitude. For real-valued inputs (complex pointer = 0) the 'positive'\n"
	"and 'negative' frequencies are combined.  For complex input vectors\n"
	"this is not the case since all DFT output amplitudes are unique.\n"
	"Stated another way, for complex input signals components above the\n"
	"Nyquist frequency have meaningful information.";

static PyObject* pyd2_Dft_getMagnitude(pyd2_Dft* self, PyObject* noargs) {
	PyObject* pObjMagn;
	size_t pLen;
	const double *magn;
	npy_intp dims;
	
	magn = Dft_getMagnitude(self->das2dft,&pLen);

	dims = pLen;
	pObjMagn = (PyObject*)PyArray_SimpleNew(1,&dims,NPY_DOUBLE);
	if(pObjMagn==NULL) 
		return NULL;
	if(! PyArray_Check(pObjMagn) ){
		PyErr_SetString(PyExc_TypeError, "Unexpected type in pyd2_Dft_getImg()");
		Py_DECREF(pObjMagn);
		return NULL;
	}

	memcpy(PyArray_DATA((PyArrayObject*)pObjMagn),magn,sizeof(double)*pLen);

	return pObjMagn;
}

const char das2help_Dft_getLength[] =
	"The length of the data vectors that will be supplied to the\n"
	"calculate function.\n";

static PyObject* pyd2_Dft_getLength(pyd2_Dft* self, PyObject* noargs) {
	return Py_BuildValue("I",self->das2dft->uLen);
}

static PyMethodDef pyd2_Dft_methods[] = {
	{"calculate", (PyCFunction)pyd2_Dft_calculate, METH_VARARGS, das2help_Dft_calculate},
	{"getReal", (PyCFunction)pyd2_Dft_getReal, METH_NOARGS, das2help_Dft_getReal},
	{"getImg", (PyCFunction)pyd2_Dft_getImg, METH_NOARGS, das2help_Dft_getImg},
	{"getMagnitude", (PyCFunction)pyd2_Dft_getMagnitude, METH_NOARGS, das2help_Dft_getMagnitude},
	{"getLength", (PyCFunction)pyd2_Dft_getLength, METH_NOARGS, das2help_Dft_getLength},
	{NULL,NULL,0,NULL} /* Sentinel */
};

const char das2help_Dft[] =
	"An amplitude preserving Discrete Fourier Transform converter"
	"\n"
	"__init__(nLen, sWindow)\n"
	"	Create a new DFT calculator\n"
	"\n"
	"		nLen	The length of the data vectors that will be supplied\n"
	"				to the calculate function\n"
	"		sWindow	A named window to apply to the data.  If None then\n"
	"				no window will be used.\n"
	"				Accepted values are ['HANN', None]\n";

static PyTypeObject pyd2_DftType = {
	PyVarObject_HEAD_INIT(NULL, 0)   /*ob_size now included compat to 2.6 */
	"_das2.Dft",         /*tp_name*/
	sizeof(pyd2_Dft),		/*tp_basicsize*/
	0,							/*tp_itemsize*/
	(destructor) pyd2_Dft_dealloc,/*tp_dealloc*/
	0,							/*tp_print*/
	0,							/*tp_getattr*/
	0,							/*tp_setattr*/
	0,							/*tp_compare*/
	0,							/*tp_repr*/
	0,							/*tp_as_number*/
	0,							/*tp_as_sequence*/
	0,							/*tp_as_mapping*/
	0,							/*tp_hash*/
	0,							/*tp_call*/
	0,							/*tp_str*/
	0,							/*tp_getattro*/
	0,							/*tp_setattro*/
	0,							/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,			/*tp_flags*/
	das2help_Dft,				/*tp_doc*/
	0,							/*tp_travsere*/
	0,							/*tp_clear*/
	0,							/*tp_richcompare*/
	0,							/*tp_weaklistoffset*/
	0,							/*tp_iter*/
	0,							/*tp_iternext*/
	pyd2_Dft_methods,			/*tp_methods*/
	0,							/*tp_members*/
	0,							/*tp_getset*/
	0,							/*tp_base*/
	0,							/*tp_ditc*/
	0,							/*tp_descr_get*/
	0,							/*tp_descr_set*/
	0,							/*tp_dictoffset*/
	(initproc)pyd2_Dft_init,	/*tp_init*/
	0,							/*tp_alloc*/
	pyd2_Dft_new,				/*tp_new*/
};

/*****************************************************************************/
/* Psd type definition */

/* instance structure */
typedef struct {
	PyObject_HEAD
	Das2Psd* das2psd;
	DftPlan* dftplan;
} pyd2_Psd;

static void pyd2_Psd_dealloc(pyd2_Psd* self) {
	if (self->das2psd){
		del_Das2Psd(self->das2psd);
		del_DftPlan(self->dftplan);
		self->das2psd = NULL;
		self->dftplan = NULL;
	}
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* pyd2_Psd_new(
	PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	pyd2_Psd* self;
	
	self = (pyd2_Psd*)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->das2psd=NULL;
		self->dftplan=NULL;
	}

	return (PyObject*)self;

}

static int pyd2_Psd_init(pyd2_Psd* self, PyObject *args, PyObject *kwds) {

	PyObject* pyCenter = NULL;
	char *sWindow = NULL;
	bool bCenter = false;
	unsigned int uLen = 0;
	das_error_msg* errMsg;

	static char *kwlist[] = {"uLen", "bCenter", "sWindow", NULL};

	if (! PyArg_ParseTupleAndKeywords(args, kwds, "IOz", kwlist,
		&uLen, &pyCenter, &sWindow))
	{
		return -1;
	}

	if (PyObject_IsTrue(pyCenter)) bCenter = true;
	else bCenter = false;
	
	if ( self->das2psd != NULL ) {
		del_Das2Psd(self->das2psd);
		del_DftPlan(self->dftplan);
		self->das2psd = NULL;
		self->dftplan = NULL;
	}

	self->dftplan = new_DftPlan(uLen, true);
	self->das2psd = new_Psd(self->dftplan, bCenter, sWindow);

	if (( self->das2psd == NULL)||(self->dftplan == NULL)) {
		errMsg = das_get_error();
		PyErr_SetString(PyExc_ValueError, errMsg->message);
		return -1;
	}

	return 0;
}

const char das2help_Psd_calculate[] =
	"Calculate a Power Spectral Density (periodogram)\n"
	"\n"
	"Using the calculation plan setup in the constructor, calculate a\n"
	"discrete Fourier transform. When this function is called, internal\n"
	"storage of any previous DFT calculations (if any) are overwritten\n"
	"	pReal	A \"time domain\" input vector\n"
	"	pImg	The imaginary (or quadrature phase) input vector the same\n"
	"			length as pReal. For a purely real signal this vector is\n"
	"			None.\n";

static PyObject* pyd2_Psd_calculate(pyd2_Psd* self, PyObject* args) {
	PyObject* pReal = NULL;
	PyObject* pImg = Py_None;
	PyObject* pObjReal = NULL;
	PyObject* pObjImg = NULL;
	double* dReal;
	double* dImg;
	size_t uLen;
	DasErrCode err;
	das_error_msg* errMsg;
	char* tmp;

	if (!PyArg_ParseTuple(args, "O|O:calculate", &pReal, &pImg)) {
		return NULL;
	}

	pObjReal = PyArray_FROM_OTF(pReal, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
	if (pObjReal == NULL) {
		return NULL;
	}

	if (pImg == Py_None) {
		pObjImg = Py_None;
		Py_INCREF(Py_None);
	}
	else {
		pObjImg = PyArray_FROM_OTF(pImg, NPY_DOUBLE, NPY_ARRAY_IN_ARRAY);
		if (pObjImg == NULL) {
			Py_DECREF(pObjReal);
			return NULL;
		}
	}

	if ( PyArray_NDIM((PyArrayObject*)pObjReal) != 1) {
		PyErr_SetString(PyExc_ValueError, "pReal is not 1-dimensional");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}
	if ( pObjImg != Py_None && PyArray_NDIM((PyArrayObject*)pObjImg) != 1) {
		PyErr_SetString(PyExc_ValueError, "pImg is not 1-dimensional");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;\
	}

	uLen = PyArray_Size(pObjReal);
	if ( pObjImg != Py_None && ((ptrdiff_t)uLen) != PyArray_Size(pObjImg) ) {
		PyErr_SetString(PyExc_ValueError, "pReal and pImg must be the same length");
		Py_DECREF(pObjReal);
		Py_DECREF(pObjImg);
		return NULL;
	}

	dReal = (double*)PyArray_DATA((PyArrayObject*)pObjReal);
	if (pObjImg == Py_None) {
		dImg = NULL;
	}
	else {
		dImg = (double*)PyArray_DATA((PyArrayObject*)pObjImg);
	}

	err = Psd_calculate(self->das2psd,dReal,dImg);
	if ( err != DAS_OKAY ) {
		errMsg = das_get_error();
		if (err == errMsg->nErr) {
			tmp = errMsg->message;
		}
		else {
			tmp = "Unknown error";
		}
		PyErr_SetString(PyExc_ValueError, tmp);
	}

	Py_DECREF(pObjReal);
	Py_DECREF(pObjImg);

	Py_RETURN_NONE;
}

const char das2help_Psd_powerRatio[] =
	"Provide a comparison of the input power and the output power.\n"
	"\n"
	"During the calculate() call the average magnitude of the input vector\n"
	"is saved along with the average magnitude of the output vector (divided\n"
	"by the Window summed and squared).  These two measures of power should\n"
	"always be close to each other when using a hann window.  When using a\n"
	"NULL window they should be almost identical, to within rounding error.\n"
	"The two measures are:\n"
	"                N-1\n"
	"            1  ----   2      2\n"
	"    Pin =  --- \\    r    +  i\n"
	"            N  /     n       n\n"
	"               ----\n"
	"                n=0\n"
	"  \n"
	"                  N-1\n"
	"             1   ----   2      2\n"
	"    Pout =  ---  \\    R    +  I\n"
	"            Wss  /     k       k\n"
	"                 ----\n"
	"                  k=0\n"
	"\n"
	"	Arguments:\n"
	"		input	(optional) if True include the input power in the return\n"
	"		output	(optional) if True include the output power in the return\n"
	"\n"
	"	returns	ratio of power out divided by power in (with no parameters)\n"
	"			(inputPower, powerRatio) with input=True\n"
	"			(outputPower, powerRatio) with output=True\n"
	"			(inputPoser, outputPoser, powerRatio) with input=True and\n"
	"			output=True\n";


static PyObject* pyd2_Psd_powerRatio(const pyd2_Psd* self, PyObject* args, PyObject* kwds) {

	PyObject* input = Py_False;
	PyObject* output = Py_False;
	double inputPower;
	double outputPower;
	double powerRatio;
	
	static char *kwlist[] = {"input", "output", NULL};

	if (! PyArg_ParseTupleAndKeywords(args, kwds, "|OO", kwlist,
		&input, &output))
	{
		return NULL;
	}

	if (PyObject_IsTrue(input) && PyObject_IsTrue(output)) {
		powerRatio=Psd_powerRatio(self->das2psd, &inputPower, &outputPower);
		return Py_BuildValue("ddd", inputPower, outputPower, powerRatio);
	}
	else if (PyObject_IsTrue(input)) {
		powerRatio=Psd_powerRatio(self->das2psd, &inputPower, NULL);
		return Py_BuildValue("dd", inputPower, powerRatio);
	}
	else if (PyObject_IsTrue(output)) {
		powerRatio=Psd_powerRatio(self->das2psd, NULL, &outputPower);
		return Py_BuildValue("dd", outputPower, powerRatio);
	}
	else {
		powerRatio=Psd_powerRatio(self->das2psd, NULL, NULL);
		return Py_BuildValue("d", powerRatio);
	}
}

const char das2help_Psd_get[] =
	"Get the amplitude magnitude vector from a calculation\n"
	"\n"
	"Scale the stored DFT so that is preserves amplitude, and get the\n"
	"magnitude. For real-value inputs (complex pointer = 0) the 'positive'\n"
	"and 'negetive' frequencies are combined. For complex input vectors this\n"
	"is not the case since all DFT output amplitudes are unique. Stated\n"
	"another way, for complex input signals components above the Nyquist\n"
	"frequency have meaningful information.\n"
	"\n"
	"	return	A pynum array holding the real signal magnitude values\n";

static PyObject* pyd2_Psd_get(const pyd2_Psd* self, PyObject* noargs) {
	
	PyObject* arrPsd;
	size_t pLen;
	const double* psd;
	npy_intp dims;

	psd = Psd_get(self->das2psd, &pLen);

	dims = pLen;
	arrPsd = (PyObject*)PyArray_SimpleNew(1,&dims,NPY_DOUBLE);
	if (arrPsd==NULL) {
		return NULL;
	}

	memcpy(PyArray_DATA((PyArrayObject*)arrPsd),psd,sizeof(double)*pLen);

	return arrPsd;
}

static PyMethodDef pyd2_Psd_methods[] = {
	{"calculate", (PyCFunction)pyd2_Psd_calculate, METH_VARARGS, das2help_Psd_calculate},
	{"powerRatio", (PyCFunction)pyd2_Psd_powerRatio, METH_VARARGS|METH_KEYWORDS, das2help_Psd_powerRatio},
	{"get", (PyCFunction)pyd2_Psd_get, METH_NOARGS, das2help_Psd_get},
	{NULL,NULL,0,NULL} /* Sentinel */
};

const char das2help_Psd[] = 
	"Create a new Power Spectral Density calculator.\n"
	"\n"
	"This estimator uses the equations given in Numerical Recipes in C,\n"
	"section 13.4, but not any of the actual Numerical Recipes source code.\n"
	"\n"
	"__init__(nLen, bCenter, sWindow)\n"
	"	Create a new DFT calculator\n"
	"\n"
	"		nLen	The length of the data vectors that will be supplied\n"
	"				to the calculate function\n"
	"		bCenter	If true, input values will be centered on the Mean value.\n"
	"				This shifts-out the DC component from the input\n"
	"		sWindow	A named window to apply to the data.  If None then\n"
	"				no window will be used.\n"
	"				Accepted values are ['HANN', None]\n";

static PyTypeObject pyd2_PsdType = {
	PyVarObject_HEAD_INIT(NULL, 0) /* ob_size is second arg, compat to 2.6 */
	"_das2.Psd",		   /*tp_name*/
	sizeof(pyd2_Psd),		/*tp_basicsize*/
	0,							/*tp_itemsize*/
	(destructor) pyd2_Psd_dealloc,/*tp_dealloc*/
	0,							/*tp_print*/
	0,							/*tp_getattr*/
	0,							/*tp_setattr*/
	0,							/*tp_compare*/
	0,							/*tp_repr*/
	0,							/*tp_as_number*/
	0,							/*tp_as_sequence*/
	0,							/*tp_as_mapping*/
	0,							/*tp_hash*/
	0,							/*tp_call*/
	0,							/*tp_str*/
	0,							/*tp_getattro*/
	0,							/*tp_setattro*/
	0,							/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,			/*tp_flags*/
	das2help_Psd,				/*tp_doc*/
	0,							/*tp_traverse*/
	0,							/*tp_clear*/
	0,							/*tp_richcompare*/
	0,							/*tp_weaklistoffset*/
	0,							/*tp_iter*/
	0,							/*tp_iternext*/
	pyd2_Psd_methods,			/*tp_methods*/
	0,							/*tp_members*/
	0,							/*tp_getset*/
	0,							/*tp_base*/
	0,							/*tp_dict*/
	0,							/*tp_descr_get*/
	0,							/*tp_descr_set*/
	0,							/*tp_dictoffset*/
	(initproc)pyd2_Psd_init,	/*tp_init*/
	0,							/*tp_alloc*/
	pyd2_Psd_new,				/*tp_new*/
};

static void dft_register(PyObject* module){
	
	Py_INCREF(&pyd2_DftType);
	PyModule_AddObject(module, "Dft", (PyObject *)&pyd2_DftType);
	Py_INCREF(&pyd2_PsdType);
	PyModule_AddObject(module, "Psd", (PyObject *)&pyd2_PsdType);
}
