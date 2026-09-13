
import das3.pycdf
import numpy as np

cdf = das3.pycdf.CDF("test","")

zVar = cdf.new("test", data=[1,2,3])

#n33 = np.array(33)

#cdf.attrs['test'].type = das3.pycdf.const.CDF_TIME_TT2000
#cdf.attrs.new('test', das3.pycdf.const.FILLED_TT2000_VALUE, das3.pycdf.const.CDF_TIME_TT2000)
#cdf.attrs.new('test', -9223372036854775807 - 1, das3.pycdf.const.CDF_TIME_TT2000.value)

zVar.attrs.new('FILLVAL',"9999-12-31 23:59:59.999999" )
#zVar.attrs.type('my_attr', das3.pycdf.const.CDF_INT8.value)


cdf.close()
