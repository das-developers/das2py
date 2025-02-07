This version of das2py provides support for dasStream version 3.0 while
retaining backwards compatability to v2.3.  If you have existing source
code based on das2py, change calls of the form:
```python
lDs = das2.read_http()
```
to
```python
dHdr, lDs = das2.read_http()
```
because the stream header is returned as it's own dictionary instead of
being merged into each dataset in the stream.

das2py versioning has been reset to match the github project and has
switched to semantic versioning.
Please issue:
```bash
conda remove das2py
conda install dasdevelopers::das2py
```

to update. This will provide version github tag 3.0-pre1, which is the
newest release.

To test stream verification issue:
```bash
wget https://raw.githubusercontent.com/das-developers/das2py/main/test/ex96_yscan_multispec.d2t
das_verify ex96_yscan_multispec.d2t
```

To test plot generation issue:
```bash
conda install matplotlib   # <-- if not already present
wget https://raw.githubusercontent.com/das-developers/das2py/main/examples/ex09_cassini_fce_ephem_ticks.py
python ex09_cassini_fce_ephem_ticks.py 2017-09-14
okular cas_mag_fce_2017-09-14.png (or whichever PNG viewer you like)
```
You should get the same plot as the one 
[the one on github](https://github.com/das-developers/das2py/blob/main/examples/ex09_cassini_fce_ephem_ticks.png">ex09_cassini_fce_ephem_ticks.png)

Thanks for trying das2py v3 :)

