# Landsat Collection 2 Surface Reflectance and Temperature Acquisition hub

Workflow to acquire Landsat Collection 2 Surface Reflectance and Surface Temperature 
products for lakes and reservoirs from point locations or lake polygons. The output 
of this workflow is stored in your Google Drive as tabular summaries of band data 
for your area of interest.

## Scope of this branch

This repository acquires historical data for all lakes and reservoirs greater 
than 1 ha for the Cache La Poudre HUC08 watershed.


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

See the config file 'northern-poudre-historical-config.yml'. This pull gathers 
the polygon-Chebyshev center point (aka, point of inaccessibility), full lake area summary,
and sampling point locations for all NW lakes/reservoirs and all reservoirs 
within the CLP greater than 1 ha.

## Running the workflow

When your configuration file is complete and you have successfully authenticated 
your Earth Engine account, you are ready to run the {targets} pipeline! There are 
two steps to this:

1.  update line 5 of the `_targets.R` file with the name of your config file

2.  run the `run_targets.Rmd` file
