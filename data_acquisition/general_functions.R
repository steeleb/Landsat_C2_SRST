library(yaml)
library(tidyverse)

# Function to read in yaml, reformat and pivot for easy use in scripts.

formatYaml = function(yml_file) {
  yaml = read_yaml(yml_file)
  nested = map_dfr(names(yaml), 
                   function(x) {
                     tibble(set_name = x,
                            param = yaml[[x]])
                     })
  nested$desc = NA_character_
  unnested = map_dfr(seq(1:length(nested$param)),
                     function(x) {
                       name <- names(nested$param[[x]])
                       nested$desc[x] <- name
                       nested <- nested %>% 
                         unnest(param) %>% 
                         mutate(param = as.character(param))
                       nested[x,]
                       })
  unnested %>% 
    select(desc, param) %>% 
    pivot_wider(names_from = desc, values_from = param)
}


grabLocs = function(yaml) {
  locs <- read_csv(file.path(yaml$data_dir, yaml$location_file))
  lat <- yaml$latitude
  lon <- yaml$longitude
  id <- yaml$unique_id
  locs %>% 
    rename_with(~c('Latitude', 'Longitude', 'id'), any_of(c(lat, lon, id)))
}