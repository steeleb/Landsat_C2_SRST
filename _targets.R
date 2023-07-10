library(targets)
library(tarchetypes)
library(reticulate)

yaml_file <- "test_config.yml"

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
  #track the config file
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
      config_file
      format_yaml(yaml_file)
      },
    packages = c("yaml", "readr")
  ),

  # track the yml file
  tar_file_read(
    name = yml,
    command = yml_save,
    read = read_csv(!!.x),
    packages = "readr"
  ),

  # load, format, save locs as an updated csv
  tar_target(
    name = locs_save,
    command = grab_locs(yml),
    packages = "readr"
  ),

  # track locs file
  tar_file_read(
    name = locs,
    command = locs_save,
    read = read_csv(!!.x),
    packages = "readr"
  ),

  # use location to get polygons for NHD
  tar_target(
    name = poly_save,
    command = get_NHD(locs_save, yml_save),
    packages = c("nhdplusTools", "sf", "readr")
  ),

  # track polygons file
  tar_file_read(
    name = polygon, # this will throw an error if the configure extent does not include polygon
    command = tar_read(poly_save),
    read = read_sf(!!.x),
    packages = "sf",
    error = "null"
  ),

  # use polygon to calculate centers
  tar_target(
    name = centers_save,
    command = calc_center(poly_save, yml_save),
    packages = c("sf", "polylabelr")
  ),

  # track centers file
  tar_file_read(
    name = centers, # this will throw an error if the configure extent does not include center.
    command = tar_read(centers_save),
    read = read_sf(!!.x),
    packages = "sf",
    error = "null"
  ),

  # get WRS tiles
  tar_target(
    name = WRS_tiles,
    command = get_WRS_tiles(locs_file, yml_file),
    packages = c("readr", "sf")
  ),

  # run the landsat pull as function per tile
  tar_target(
    name = eeRun,
    command = {
      locs
      polygon
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
      ref_pull_457
      ref_pull_89
      run_GEE_per_tile(WRS_tiles)
    },
    pattern = map(WRS_tiles),
    packages = "reticulate"
  )
)
