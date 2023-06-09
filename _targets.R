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
  source('data_acquisition/src/pySetup.R')
} else {
  use_condaenv(file.path(getwd(), 'env'))
}


# Source functions --------------------------------------------------------

source('data_acquisition/src/general_functions.R')
source_python('data_acquisition/src/gee_functions.py')

# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = "tidyverse")

# target objects in workflow
list(
  # load, format, save yml as a csv
  tar_target(name = ymlSave,
             command = formatYaml(yaml_file),
             packages = c('yaml', 'readr')),
  
  # track the yml file
  tar_file_read(name = yml,
                command = tar_read(ymlSave),
                read = read_csv(!!.x),
                packages = 'readr'),
  
  # load, format, save locs as an updated csv
  tar_target(name = locsSave,
             command = grabLocs(yml),
             packages = 'readr'),

  # track locs file
  tar_file_read(name = locs,
                command = tar_read(locsSave),
                read = read_csv(!!.x),
                packages = 'readr'),
  
  # use location to get polygons for NHD
  tar_target(name = polySave,
             command = getNHD(locs, yml),
             packages = c('nhdplusTools', 'sf', 'readr')),
  
  # track polygons file
  tar_file_read(name = polygon,
                command = tar_read(polySave),
                read = read_sf(!!.x),
                packages = 'sf'),
  
  # use polygon to calculate centers
  tar_target(name = centersSave,
             command = calcCenter(polygon),
             packages =  c('sf', 'polylabelr')),
  
  # track centers file
  tar_file_read(name = centers,
                command = tar_read(centersSave),
                read = read_sf(!!.x),
                packages = 'sf'),

  # run the landsat pull
  tar_target(name = eeRun,
             command = { # here, we include dependencies so that this runs in the proper order
               yml
               locs
               polygon
               centers
               addRadMask
               srCloudMask
               maximum_no_of_tasks
               Mbsrv
               Ndvi
               applyScaleFactors
               Awesh
               dpBuff
               CalcHillShadows
               cfMask
               DSWE
               removeGeo
               Mbsrn
               RefPull457
               CalcHillShades
               Mndwi
               csv_to_eeFeat
               source_python('data_acquisition/src/runGEE.py')
               },
             packages = 'reticulate')
  
)