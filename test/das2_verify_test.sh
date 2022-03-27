#!/usr/bin/env bash

# Need to stop using bash for unit tests!

echo "Testing: Strict Stream Validation"

for file in ex06_yset_binary_2.3.d2s ex08_zset_dynaspec_2.3.d2t ex12_wset_sounder_2.3.d2t ex96_yscan_multispec_2.2.d2t ; do
	echo "   exec: python${PYVER} scripts/das2_verify -S test/${file}"
	
	if ! python${PYVER} scripts/das2_verify -S test/${file} ; then
		echo "   FAILED: verify test/${file}"
		exit 7
	fi

	if ! python${PYVER} scripts/das2_verify test/${file} ; then
		echo "   FAILED: verify test/${file}"
		exit 7
	fi

done

echo "Testing: Extended Stream Validation"


file=ex05_yset_custom_2.3.d2t
echo "   exec: python${PYVER} scripts/das2_verify -S test/${file}"
if ! python${PYVER} scripts/das2_verify test/${file} ; then
	echo "   FAILED: verify test/${file}"
	exit 7
fi

exit 0
