# Building RPMs

First setup your build environment, including an rpmbuild tree in your home 
directory:
```bash
$ yum install gcc rpm-build rpm-devel rpmlint make python bash coreutils diffutils patch rpmdevtools
$ rpmdev-setuptree
```

Copy the included spec and patch files to locations within your rpmbuild tree.  The
destdir patch is needed because version `v2.3-pre4` did not have the DESTDIR macro
and thus the install targets were not relocatable for two-stage installs.  Future releases (aka v2.3-pre5, etc.) will not need this file.
```bash
cp makefiles/rpm/das2py.spec $HOME/rpmbuild/SPECS/
```

Install dependencies as usual, but also include the das2C rpms:
```bash
yum install expat-devel fftw-devel openssl-devel
yum localinstall das2C-2.3~pre4-1.el7.x86_64.rpm
yum localinstall das2C-devel-2.3~pre4-1.el7.x86_64.rpm  # build dependency
```

In general the das2C version numbers track with the das2py version numbers, but
not necessarily.  The `das2py.spec` file should handle dependency tracking and will
complain if the version of das2C you installed won't work for some reason.

Build the RPMs and the SRPM:
```bash
$ rpmbuild -bs $HOME/rpmbuild/SPECS/das2py.spec  # Source RPM
$ rpmbuild -bb $HOME/rpmbuild/SPECS/das2py.spec  # lib, devel & debug RPMs
```

Install the binary RPMs
```bash
$ sudo yum localinstall $HOME/rpmbuild/RPMS/x86_64/das2py*.rpm
```

A basic test:
```bash
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex01_source_queries.py
```

Test das2 federated catalog node walking:
```bash
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex11_catalog_listings.py
```

Test plot creation (requires matplotlib):
```bash
# Getting matplotlib (CentOS 7)
$ sudo yum install libjpeg-turbo-devel 
$ pip3.6 install matplotlib --user      # CentOS 7

# Getting matplotlib (CentOS 8)
$ sudo yum install python3-matplotlib   # CentOS 8

# Now make a plot file and show it
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex02_galileo_pws_spectra.py
$ eog ex02_galileo_pws_spectra.png
```





