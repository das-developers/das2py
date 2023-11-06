# Conda Package Build Instructions

Most of the miniconda setup that you'll need is defined in the 
(das2C conda setup)[https://github.com/das-developers/das2C/blob/master/buildfiles/conda/README.md]
instructions.  If you haven't built das2C then *stop* now and make
sure your miniconda and compiler environments are setup and work.
The best way to do that is to simply build das2C as a conda package
as well.

## To build

1. Activate your miniconda enviorment

2. Get the sources:
   ```bash
   (base) $ git clone https://github.com/das-developers/das2C.git
   (base) $ cd das2C
   ```

3. Run conda build:
   ```bash
   (base) $ conda build -c dasdevelopers buildfiles/conda
   ```

## Install and test

