library(targets)
library(tarchetypes)
# run tar_make() to run the pipeline
# and tar_read(data_summary) to view the results.


source('data_acquisition/gee_functions.R')

if(!dir.exists('env')) {
  source('data_acquisition/pySetup.R')
}

# Set target-specific options such as packages.
tar_option_set(packages = "tidyverse")


# target objects in workflow
list(

  tar_target(yml,
             read_yaml('test.yml'),
             packages = 'yaml')
  
  # tar_target()
  # tar_file()
  # tar_render()
)
