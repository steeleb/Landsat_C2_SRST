# Landsat Collection 2 Surface Reflectance and Temperature Acquisition hub

Workflow to acquire Landsat Collection 2 Surface Reflectance and Surface Temperature products for lakes and reservoirs.

Note, before any code that requires access to GEE is run, you must execute the following command in your **zsh** terminal and follow the prompts in your browser.

`earthengine authenticate`

When complete, your terminal will read:

`Successfully saved authorization token.`

## Repository Overview

This repository is powered by {targets}, an r-based workflow manager. The following commands are useful starting points within the Project directory:

> tar_make() \# to run the pipeline
>
> tar_visnetwork() \# to see visual summary

In order to use this workflow, you must have a [Google Earth Engine account](https://earthengine.google.com/signup/), and you will need to [download, install, and initialize gcloud](https://cloud.google.com/sdk/docs/install). For common issues with `gcloud`, please [see the notes here](https://github.com/rossyndicate/ROSS_RS_mini_tools/blob/main/helps/CommonIssues.md).
