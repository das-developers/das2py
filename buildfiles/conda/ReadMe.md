# Conda Package Build Instructions

Most of the miniconda setup that you'll need is defined in the 
(das2C conda setup)[https://github.com/das-developers/das2C/blob/master/buildfiles/conda/README.md]
instructions.  If you haven't built das2C then *stop* now and make
sure your miniconda and compiler environments are setup and work.
The best way to do that is to simply build das2C as a conda package
as well.

## To build a das2py conda package

Activate your miniconda enviorment and get the build and upload tools:
```bash
$ source ~/miniconda3/bin/activate
(base) $ conda install conda-build
(base) $ conda install anaconda-client
```

2. Get the conda build recipe.  Though the sources aren't used to build the
   package, the conda recipe is in a sub directory.
   ```bash
   (base) $ git clone https://github.com/das-developers/das2py.git
   ```

3. Activate your miniconda environment and run conda build.  Note that the
   dasdevelopers channel will need to be specified on the command line in
   order for the build tools to find the das2c package

   ```bash
   (base) $ conda build -c dasdevelopers das2py/buildfiles/conda
   ```

## To upload a das2py conda package

This is rather straightforward.  If the description file contains no single quotes
you can:
```bash
(base) $ anaconda upload -u dasdevelopers \
   -d $( echo -n "'" && cat das2py/buildfiles/conda/description.html && echo -n "'") \
   $HOME/miniconda3/conda-bld/linux-64/das2py-2.3.0-pre3-py38h1de35cc_0.tar.bz2  # for example
```
otherwise just issues:
```bash
(base) $ anaconda upload -u dasdevelopers \
   $HOME/miniconda3/conda-bld/linux-64/das2py-2.3.0-pre3-py38h1de35cc_0.tar.bz2  # for example
```
and update the description at:
[https://anaconda.org/DasDevelopers/das2c](https://anaconda.org/DasDevelopers/das2c)

## To test a das2py conda package

Install via:
```bash
(base) $ conda install -c dasdevelopers das2py
```

And test via:
```bash
conda install matplotlib  #if not already present
wget wget http://das2.org/das2py/examples/ex02_galileo_pws_spectra.py
python ex02_galileo_pws_spectra.py
okular ex02_galileo_pws_spectra.png  # or whatever image viewer you prefer
```
