library(targets)
library(tarchetypes)
library(reticulate)

# point to the yaml file that holds your configurations

yaml_file = 'test.yml'

# MUST READ ---------------------------------------------------------------

# IMPORTANT NOTE:
#
# you must execute the command 'earthengine authenticate' in a zsh terminal 
# before initializing this workflow. See the repository README for complete 
# dependencies and troubleshooting.

# RUNNING {TARGETS}:
#
# run tar_make() to run the pipeline
# run tar_visnetwork() to see visual summary


# Set up python virtual environment ---------------------------------------

if(!dir.exists('env')) {
  source('data_acquisition/pySetup.R')
} else {
  use_condaenv(file.path(getwd(), 'env'))
}


# Source functions --------------------------------------------------------

source('data_acquisition/general_functions.R')
source('data_acquisition/gee_functions.R')


# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = "tidyverse")

# target objects in workflow
list(

  tar_target(yml,
             formatYaml(yaml_file),
             packages = 'yaml',
             memory = 'persistent'),
  
  tar_target(name = locs,
             command = grabLocs(yml),
             packages = c('readr')),
  
  #tar_target()
  
  tar_target(file,
             print(locs))
  
  # tar_target()
  # tar_file()
  # tar_render()
)
