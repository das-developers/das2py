#include <stdio.h>
#include <math.h>

int main(int argc, char** argv){
	
	double dSc = 60.000000001;    # All seconds
	int nSc = (int)dSc;           # seconds field

	double dMs = (dSc - nSc)*1e3; # All Milliseconds
	int nMs = (int)dMs;           # Millisec field

	double dUs = (dMs - nMs)*1e3; # All microseconds
	int nUs = (int)dUs;           # Microsec field

	double dNs = round( (dUs - nUs)*1e3);  # All nanosec
	int nNs = (int)dNs;                    # nanosec field

	printf("Input:     %.9f\n",   dSc);
	printf("Seconds:   %d\n",     nSc);
	printf("Fraction:  %.9f\n\n", dSc - nSc);

	printf("Input:    %.9f\n",   dMs);
	printf("MilliSec: %d\n",     nMs);
	printf("Fraction: %.9f\n\n", dMs - nMs);

	printf("Input:    %.9f\n",   dUs);
	printf("MicroSec: %d\n",     nUs);
	printf("Fraction: %.9f\n\n", dUs - nUs);

	printf("Input:    %.9f\n",   dNs);
	printf("NanoSec:  %d\n",     nNs);
	printf("Fraction: %.9f\n\n", dNs - nNs);

	return 0;
}