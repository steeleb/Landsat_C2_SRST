library(targets)
library(tarchetypes)
library(reticulate)

yaml_file <- "example_yml/northern-poudre-regional-config.yml"

# MUST READ ---------------------------------------------------------------

# IMPORTANT NOTE:
#
# you must execute the command 'earthengine authenticate' in a zsh terminal
# before initializing this workflow. See the repository README for complete
# dependencies and troubleshooting.

# RUNNING {TARGETS}:
#
# use the file 'run_targets.Rmd', which includes EE authentication.


# Set up python virtual environment ---------------------------------------

if (!dir.exists("env")) {
  tar_source("data_acquisition/src/pySetup.R")
} else {
  use_condaenv(file.path(getwd(), "env"))
}


# Source functions --------------------------------------------------------

tar_source("data_acquisition/src/general_functions.R")
source_python("data_acquisition/src/gee_functions.py")


# Define {targets} workflow -----------------------------------------------

# Set target-specific options such as packages.
tar_option_set(packages = "tidyverse")

# target objects in workflow
list(
  # read and track the config file
  tar_file_read(
    name = config_file,
    command = yaml_file,
    read = read_yaml(!!.x),
    packages = 'yaml'
  ),

  # load, format, save yml as a csv
  tar_target(
    name = yml_save,
    command = {
      # make sure that {targets} runs the config_file target before this target
      config_file 
      format_yaml(yaml_file)
      },
    packages = c("yaml", "tidyverse") #for some reason, you have to load TV.
  ),

  # read in and track the formatted yml .csv file
  tar_file_read(
    name = yml,
    command = yml_save,
    read = read_csv(!!.x),
    packages = "readr"
  ),

  # load, format, save user locations as an updated csv called locs.csv
  tar_target(
    name = locs_save,
    command = grab_locs(yml),
    packages = "readr"
  ),

  # read and track formatted locations shapefile
  tar_file_read(
    name = locs,
    command = locs_save,
    read = read_csv(!!.x),
    packages = "readr"
  ),
  
  # use location shapefile and configurations to get polygons from NHDPlusv2
  tar_target(
    name = poly_save,
    command = get_NHD(locs, yml),
    packages = c("nhdplusTools", "sf", "tidyverse")
  ),

  # load and track polygons file
  tar_file_read(
    name = polygons, # this will throw an error if the configure extent does not include polygon
    command = tar_read(poly_save),
    read = read_sf(!!.x),
    packages = "sf",
    error = "null"
  ),

  # use `polygons` sfc to calculate Chebyshev centers
  tar_target(
    name = centers_save,
    command = calc_center(polygons, yml),
    packages = c("sf", "polylabelr", "tidyverse")
  ),

  # track centers file
  tar_file_read(
    name = centers, # this will throw an error if the configure extent does not include center.
    command = tar_read(centers_save),
    read = read_sf(!!.x),
    packages = "sf",
    error = "null"
  ),

  # get WRS tile acquisition method from yaml
  tar_target(
    name = WRS_detection_method,
    command = {
      locs
      centers
      polygons
      get_WRS_detection(yml)
      },
    packages = "readr"
  ),
  
  # get WRS tiles
  tar_target(
    name = WRS_tiles,
    command = get_WRS_tiles(WRS_detection_method, yml),
    packages = c("readr", "sf")
  ),

  # run the landsat pull as function per tile
  tar_target(
    name = eeRun,
    command = {
      yml
      locs
      polygons
      centers
      csv_to_eeFeat
      apply_scale_factors
      dp_buff
      DSWE
      Mbsrv
      Ndvi
      Mbsrn
      Mndwi
      Awesh
      add_rad_mask
      sr_cloud_mask
      sr_aerosol
      cf_mask
      calc_hill_shadows
      calc_hill_shades
      remove_geo
      maximum_no_of_tasks
      ref_pull_457_DSWE1
      ref_pull_89_DSWE1
      ref_pull_457_DSWE3
      ref_pull_89_DSWE3
      run_GEE_per_tile(WRS_tiles)
    },
    pattern = map(WRS_tiles),
    packages = "reticulate"
  )
)
