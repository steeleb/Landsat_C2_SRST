# this script sets up a python virtual environment for use in this workflow

library('reticulate')

try(install_miniconda())

py_install(c('earthengine-api', 'pandas', 'fiona', 'pyreadr'))

#create a conda environment named 'apienv' with the packages you need
conda_create(envname = file.path(getwd(), 'env'),
             packages = c('earthengine-api', 'pandas', 'fiona', 'pyreadr'))

Sys.setenv(RETICULATE_PYTHON = file.path(getwd(), 'env/bin/python/'))

use_condaenv(file.path(getwd(), "env/"))
