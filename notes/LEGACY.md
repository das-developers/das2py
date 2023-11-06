# Building Python 2 / Numpy for Legacy Project Support

## Building Python2 from source on MacOS


**Get a compiler**
You will need a C compiler.  To see if one is already installed open a terminal
and run:
```bash
$ cc --version
```
If this produces nothing, then you'll need to install the C compiler first.  On
MacOS the standard compiler is supplied by the xcode package.  Run the command
```bash
xcode-select --install
```
to install it if needed.

There a few places you don't want to install your legacy version of python.
*Don't* put it under `/usr/local` as [homebrew](https://brew.sh/) uses that
location.  *Don't* put it in `/usr` as the system python uses that location.
In these notes we are supporting old Juno Mission project code on MacOS.
The top level project directory will be:

```bash
/project/juno/opt/darwin13
```

everything will be installed relative to that location.  Choose a suitable 
replacement directory for your project.  Furthermore we are on a shared NFS
system so OS specific binaries must be in a different path from general items.
Since these notes were generated on a Mac OS 10.13 system, I'll use the name
`darwin13` to denote host OS specific items.

```bash
$ export PY_PRE=/project/juno/opt/darwin13

$ cd $HOME
$ curl https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz > Python-2.7.18.tgz
$ mkdir tmp && cd tmp
$ tar -xvzf ../Python-2.7.18.tgz
$ cd Python-2.7.18

$ ./configure --prefix=$PY_PRE --enable-ipv6 --enable-shared \
   --with-ensurepip=install LDFLAGS="-W1,-rpath=$PYTHON_PREFIX/lib"

$ make
$ make install
```
Make sure at least something works.  Run make test, you don't have to wait
for the entire test battery to finish, though it's a good idea.

```bash
$ make test
```
Finally symlink the python binary to some location on your project path.
$ cd /project/juno/bin/darwin13
$ ln -s /project/juno/opt/darwin13/bin/python2.7
$ ln -s /project/juno/opt/darwin13/bin/python2
$ ln -s /project/juno/opt/darwin13/bin/python
```



## Building numpy 1.17 from source on any POSIX system

First we'll need the prerequisites:
```bash
$ brew install fftw
$ brew install 
```

Next get the source code for the last version of NumPy to support python 2.7.
```bash
$ cd $HOME
$ cd tmp
# curl doesn't work for github, download via browser or issue:
$ wget https://github.com/numpy/numpy/releases/download/v1.16.6/numpy-1.16.6.tar.gz
$ tar -xvzf numpy-1.16.6.tar.gz
$ cd numpy-1.16.6.tar.gz
```

Make sure that your getting the version of python that was built above. This is
just a sanity check to make sure you're not running `/usr/bin/python`,
`/usr/local/bin/python` or some other system location.  

```bash
$ which python
/project/juno/bin/darwin13/python  # Specific example, yours will be different
```

Now build/install numpy 1.16.
```bash
$ python setup.py build
$ python setup.py install
```



