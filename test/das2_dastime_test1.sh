#!/usr/bin/env bash

# The original input dataset was generated using the commands:

# vgr_env
# vgpw_sa_rdr -R /opt/project/voyager/DATA 1 2014-04-02 2014-04-12 > FILE


echo "Testing: DasTime functions"

echo "   exec: python${PYVER} test/das2_dastime_test1.py $1 > $1/das2_dastime_output1.txt"
python${PYVER} test/das2_dastime_test1.py $1 > $1/das2_dastime_output1.txt

if [ "$?" != "0" ]; then
	echo "  Result: FAILED"
	exit 4
fi

echo -n "   exec: cat test/das2_dastime_output1.txt | md5sum"
s1=$(cat test/das2_dastime_output1.txt | md5sum)
echo " --> $s1"

if [ "$?" != "0" ]; then
	echo "  Result: FAILED"
	exit 4
fi


echo -n "   exec: cat $1/das2_dastime_output1.txt | md5sum"
s2=$(cat $1/das2_dastime_output1.txt | md5sum)
echo " --> $s2"

if [ "$?" != "0" ]; then
	echo "  Result: FAILED"
	exit 4
fi


if [ "$s1" != "$s2" ] ; then
	echo " Result: FAILED"
	echo
	exit 4
fi

echo " Result: PASSED"
echo
exit 0
