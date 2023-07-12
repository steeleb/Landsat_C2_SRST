# format_yaml: Function to read in yaml, reformat and pivot for easy use in scripts ----
format_yaml <-  function(yml_file) {
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
  write_csv(unnested, 'data_acquisition/in/yml.csv')
  'data_acquisition/in/yml.csv'
}


# grab_locs: Load in and format location file using yaml file ----

grab_locs <- function(yaml) {
  if (grepl('site', yaml$extent[1])) {
    locs <- read_csv(file.path(yaml$data_dir, yaml$location_file))
    # store yaml info as objects
    lat <- yaml$latitude
    lon <- yaml$longitude
    id <- yaml$unique_id
    # apply objects to tibble
    locs <- locs %>% 
      rename_with(~c('Latitude', 'Longitude', 'id'), any_of(c(lat, lon, id)))
    write_csv(locs, 'data_acquisition/in/locs.csv')
    return('data_acquisition/in/locs.csv')
  } else {
    message('Not configured to use site locations.')
  }
}


# get_NHD: if user desires lake extent and does not provide lake polygons, use NHDPlus to grab and export polygons

get_NHD <- function(locs, yaml) {
  yaml = read_csv(yaml)
  if (grepl('poly', yaml$extent[1])) { # if polygon is specified in desired extent - either polycenter or polgon
    if (yaml$polygon[1] == 'FALSE') { # and no polygon is provided, then use nhdplustools
      locations = read_csv(locs)
      # create sf
      wbd_pts = st_as_sf(locations, crs = yaml$location_crs[1], coords = c('Longitude', 'Latitude'))
      id = locations$id
      for(w in 1:length(id)) {
        aoi_name = wbd_pts[wbd_pts$id == id[w],]
        lake = get_waterbodies(AOI = aoi_name)
        if (w == 1) {
          all_lakes = lake
        } else {
          all_lakes = rbind(all_lakes, lake)
        }
      }
      all_lakes = all_lakes %>% select(id, comid, gnis_id:elevation, meandepth:maxdepth)
      write_csv(st_drop_geometry(all_lakes), 'data_acquisition/out/NHDPlus_stats_lakes.csv')
      all_lakes = all_lakes %>% select(id, comid, gnis_name)
      st_write(all_lakes, 'data_acquisition/out/NHDPlus_polygon.shp')
      return('data_acquisition/out/NHDPlus_polygon.shp')
    } else { # otherwise read in specified file
      polygons = read_sf(file.path(yaml$poly_dir[1], yaml$poly_file[1])) 
      st_drop_geometry(polygons) %>% 
        rowid_to_column('id') %>% 
        mutate(id = id-1) %>% 
        write_csv(., 'data_acquisition/out/user_polygon_withrowid.csv')
      st_write(polygons, 'data_acquisition/out/user_polygon.shp')
      return('data_acquisition/out/user_polygon.shp')
    }
  } else {
    return(message('Not configured to use polygon area.'))
  }
}

# calc_center
calc_center <- function(poly, yaml) {
  yaml = read_csv(yaml)
  if (grepl('center', yaml$extent[1])) {
    # load polygon
    polygon = read_sf(poly)
    # create an empty tibble
    cc_df = tibble(
      rowid = integer(),
      lon = numeric(),
      lat = numeric(),
      dist = numeric()
    )
    for (i in 1:length(polygon[[1]])) {
      coord = polygon[i,] %>% st_coordinates()
      x = coord[,1]
      y = coord[,2]
      poly_poi = poi(x,y, precision = 0.00001)
      cc_df  <- cc_df %>% add_row()
      cc_df$rowid[i] = i
      cc_df$lon[i] = poly_poi$x
      cc_df$lat[i] = poly_poi$y
      cc_df$dist[i] = poly_poi$dist
    }
    cc_dp <- polygon %>%
      st_drop_geometry() %>% 
      full_join(., cc_dp)
    cc_geo <- st_as_sf(cc_df, coords = c('lon', 'lat'), crs = st_crs(polygon))
    
    if (yaml$lake_poly[1] == FALSE) {
      write_sf(cc_geo, file.path('data_acquisition/out/NHDPlus_polygon_centers.shp'))
      cc_df %>% 
        rename(center_lat = lat,
               center_lon = lon) %>% 
        write_csv(paste0('data_acquisition/out/NHDPlus_polygon_centers.csv')) 
      return('data_acquisition/out/NHDPlus_polygon_centers.shp')
      } else {
      write_sf(cc_geo, file.path('data_acquisition/out/user_polygon_centers.shp'))
      cc_df %>% 
        rename(center_lat = lat,
               center_lon = lon) %>% 
        write_csv(paste0('data_acquisition/out/user_polygon_centers.csv'))
      return('data_acquisition/out/user_polygon_centers.shp')
    }
  } else {
    return(message('Not configured to pull polygon center.'))
  }
}
  

### get_WRS_detection: function to name the file to grab WRS tiles

# points are the easiest, so prioritize those.
get_WRS_detection <- function(yml) {
  yml = read_csv(yml)
  extent = yml$extent[1]
  if (grepl('site', extent)) {
    return('site')
  } else {
    if (grepl('center', extent)) {
      return('center')
    } else {
      if (grepl('poly', extent)) {
        return('polygon')
      }
    }
  }
}

### get_WRS_tiles: function to get all WRS tiles for branching

get_WRS_tiles <- function(detection, yml) {
  yml <- read_csv(yml)
  if (detection == 'site') {
    locations <- read_csv(tar_read(locs)) 
    locations <- st_as_sf(locations, coords = c('Longitude', 'Latitude'))
    st_crs(locations) <- yml$location_crs
    WRS <- read_sf('data_acquisition/in/WRS2_descending.shp')
    WRS_subset <- WRS[locations,]
    write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
    return(WRS_subset$PR)
  } else {
    if (detection == 'centers') {
      centers <- tar_read(centers)
      centers_cntrd <- st_centroid(centers)
      WRS <- read_sf('data_acquisition/in/WRS2_descending.shp')
      WRS_subset <- WRS[centers_cntrd,]
      write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
      return(WRS_subset$PR)
    } else {
      if (detection == 'polygon') {
        poly <- tar_read(polygons)
        poly_cntrd <- st_centroid(poly)
        WRS <- read_sf('data_acquisition/in/WRS2_descending.shp')
        WRS_subset <- WRS[poly_cntrd,]
        write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
        return(WRS_subset$PR)
      }
    }
  }
}
  

### run_GEE_per_tile: function to run a single tile through the 'run_GEE.py' file

run_GEE_per_tile <- function(WRS_tile) {
  tile <- WRS_tile
  write_lines(tile, 'data_acquisition/out/current_tile.txt', sep = '')
  source_python('data_acquisition/src/runGEEperTile.py')
}