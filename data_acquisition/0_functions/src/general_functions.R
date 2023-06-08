library(yaml)
library(tidyverse)

# formatYaml: Function to read in yaml, reformat and pivot for easy use in scripts ----

formatYaml <-  function(yml_file) {
  yaml <-  read_yaml(yml_file)
  # create a nested tibble from the yaml file
  nested <-  map_dfr(names(yaml), 
                   function(x) {
                     tibble(set_name = x,
                            param = yaml[[x]])
                     })
  # create a new column to contain the nested parameter name and unnest the name
  nested$desc <- NA_character_
  unnested <- map_dfr(seq(1:length(nested$param)),
                     function(x) {
                       name <- names(nested$param[[x]])
                       nested$desc[x] <- name
                       nested <- nested %>% 
                         unnest(param) %>% 
                         mutate(param = as.character(param))
                       nested[x,]
                       })
  # re-orient to make it easy to grab necessary info in future functions
  unnested <- unnested %>% 
    select(desc, param) %>% 
    pivot_wider(names_from = desc, values_from = param)
  write_csv(unnested, 'data_acquisition/1_prepare/data/yml.csv')
  'data_acquisition/1_prepare/data/yml.csv'
}


# grabLocs: Load in and format location file using yaml file ----

grabLocs <- function(yaml) {
  locs <- read_csv(file.path(yaml$data_dir, yaml$location_file))
  # store yaml info as objects
  lat <- yaml$latitude
  lon <- yaml$longitude
  id <- yaml$unique_id
  # apply objects to tibble
  locs <- locs %>% 
    rename_with(~c('Latitude', 'Longitude', 'id'), any_of(c(lat, lon, id)))
  write_csv(locs, 'data_acquisition/1_prepare/data/locs.csv')
  'data_acquisition/1_prepare/data/locs.csv'
}

