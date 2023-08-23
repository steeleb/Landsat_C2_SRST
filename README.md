# Landsat Collection 2 Surface Reflectance and Temperature Acquisition hub

Workflow to acquire Landsat Collection 2 Surface Reflectance and Surface Temperature 
products for lakes and reservoirs from point locations or lake polygons. The output 
of this workflow is stored in your Google Drive as tabular summaries of band data 
for your area of interest.

## Scope of this branch

This repository acquires historical data for all of EcoRegion Level 3, Zone 21, and all NW lakes/reservoirs.

Primary repository contact: B Steele <b dot steele at colostate dot edu>

## Repository Overview

This repository is powered by {targets}, an r-based workflow manager. In order 
to use this workflow, you must have a [Google Earth Engine account](https://earthengine.google.com/signup/), 
and you will need to [download, install, and initialize gcloud](https://cloud.google.com/sdk/docs/install). 
For common issues with `gcloud`, please 
[see the notes here](https://github.com/rossyndicate/ROSS_RS_mini_tools/blob/main/helps/CommonIssues.md).

### Requirements

Note, before any code that requires access to Google Earth Engine is run, you must 
execute the following command in your **zsh** terminal and follow the prompts in 
your browser:

`earthengine authenticate`

When complete, your terminal will read:

`Successfully saved authorization token.`

This token is valid for 7 days from the time of authentication.

## Completing the config.yml file

See the config file 'northern-poudre-regional-config.yml'. Note that the name of 
this yml does not match the pull here (this pull does not contain the entirety)
of the CLP HUC8 watershed. Renaming this file would invalidate the {targets} 
workflow, so until this pull is updated, the name will be, unfortunately, 
ill-fitting. This pull only gathers the polygon-Chebyshev center 
point (aka, point of inaccessibility) for all lakes and reservoirs greater than 
1 ha in the EcoRegion Level 3, Zone 21 (plus Boulder Reservoir, which is outside
of the ER Zone).

## Running the workflow

When your configuration file is complete and you have successfully authenticated 
your Earth Engine account, you are ready to run the {targets} pipeline! There are 
two steps to this:

1.  update line 5 of the `_targets.R` file with the name of your config file

2.  run the `run_targets.Rmd` file

## Folder architecture

 * _targets contains output of the _targets.R package and can be ignored.
 * example_yml contains some example yml files for running this workflow, and the associated
   location data
 * data_acquisition contains the sourced functions in the _targets.R workflow, as well as an
   `in` and `out` folder which store end-user's data, though these files are not tracked (other
   than the WRS2 shapefile) by GitHub.
