#' Function to read in yaml, reformat and pivot for easy use in scripts
#' 
#' @param yml_file user-specified file containing configuration details for the
#' pull.
#' @returns filepath for the .csv of the reformatted yaml file. Silently saves 
#' the .csv in the `data_acquisition/in` directory path.
#' 
#' 
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


#' Load in and format location file using config settings
#' 
#' @param yaml contents of the yaml .csv file
#' @returns filepath for the .csv of the reformatted location data or the message
#' 'Not configured to use site locations'. Silently saves 
#' the .csv in the `data_acquisition/in` directory path if configured for site
#' acquisition.
#' 
#' 
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


#' Use NHDPlusTools to create a polygon shapefile if user wants whole-lake 
#' summaries, or use the user-specified shapefile.
#' 
#' @param yaml contents of the yaml .csv file
#' @param locations contents of the formatted locations file
#' @returns filepath for the .shp of the polygons or the message
#' 'Not configured to use polygons'. Silently saves 
#' the .shp in the `data_acquisition/in` directory path if configured for polygon
#' acquisition.
#' 
#' 
get_NHD <- function(locations, yaml) {
  if (grepl('poly', yaml$extent[1])) { # if polygon is specified in desired extent - either polycenter or polgon
    if (yaml$polygon[1] == 'False') { # and no polygon is provided, then use nhdplustools
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
      st_write(all_lakes, 'data_acquisition/out/NHDPlus_polygon.shp', append = F)
      return('data_acquisition/out/NHDPlus_polygon.shp')
    } else { # otherwise read in specified file
      polygons = read_sf(file.path(yaml$poly_dir[1], yaml$poly_file[1])) 
      polygons = st_zm(polygons)#drop z or m if present
      polygons = st_make_valid(polygons)
      st_drop_geometry(polygons) %>% 
        rowid_to_column('id') %>% 
        mutate(id = id-1) %>% #subract 1 so that it matches with Py output
        write_csv(., 'data_acquisition/out/user_polygon_withrowid.csv')
      st_write(polygons, 'data_acquisition/out/user_polygon.shp', append = F)
      return('data_acquisition/out/user_polygon.shp')
    }
  } else {
    return(message('Not configured to use polygon area.'))
  }
}

#' Use polygon and 'point of inaccessibility' function (polylabelr::poi()) to 
#' determine the equivalent of
#' Chebyshev center, furthest point from every edge of a polygon
#' 
#' @param yaml contents of the yaml .csv file
#' @param poly sfc object of polygon areas for acquisition
#' @returns filepath for the .shp of the polygon centers or the message
#' 'Not configured to use polygon centers'. Silently saves 
#' the polygon centers shapefile in the `data_acquisition/in` directory path 
#' if configured for polygon centers acquisition.
#' 
#' 
calc_center <- function(poly, yaml) {
  if (grepl('center', yaml$extent[1])) {
    # create an empty tibble
    cc_df = tibble(
      rowid = integer(),
      lon = numeric(),
      lat = numeric(),
      dist = numeric()
    )
    for (i in 1:length(poly[[1]])) {
      coord = poly[i,] %>% st_coordinates()
      x = coord[,1]
      y = coord[,2]
      poly_poi = poi(x,y, precision = 0.00001)
      cc_df  <- cc_df %>% add_row()
      cc_df$rowid[i] = i
      cc_df$lon[i] = poly_poi$x
      cc_df$lat[i] = poly_poi$y
      cc_df$dist[i] = poly_poi$dist
    }
    cc_dp <- poly %>%
      st_drop_geometry() %>% 
      rowid_to_column() %>% 
      full_join(., cc_df)
    cc_geo <- st_as_sf(cc_df, coords = c('lon', 'lat'), crs = st_crs(poly))
    
    if (yaml$polygon[1] == FALSE) {
      write_sf(cc_geo, file.path('data_acquisition/out/NHDPlus_polygon_centers.shp'))
      cc_df %>% 
        rename(Latitude = lat,
               Longitude = lon) %>% 
        mutate(id = rowid - 1) %>% 
        write_csv('data_acquisition/out/NHDPlus_polygon_centers.csv')
      return('data_acquisition/out/NHDPlus_polygon_centers.shp')
      } else {
      write_sf(cc_geo, file.path('data_acquisition/out/user_polygon_centers.shp'))
      cc_df %>% 
        rename(Latitude = lat,
               Longitude = lon) %>% 
        mutate(id = rowid - 1) %>% 
        write_csv('data_acquisition/out/user_polygon_centers.csv')
      return('data_acquisition/out/user_polygon_centers.shp')
    }
  } else {
    return(message('Not configured to pull polygon center.'))
  }
}
  

#' Function to use the yaml file extent to define the optimal shapefile for 
#' determining the WRS paths that need to be extracted.
#' 
#' @param yaml contents of the yaml .csv file
#' @returns text string
#' 
#' @details Polygons are the first choice for WRS overlap, as they cover more
#' area and are most likely to cross the boundaries of WRS tiles. 
#' 
#' 
get_WRS_detection <- function(yaml) {
  extent = yaml$extent[1]
  if (grepl('poly', extent)) {
    return('polygon')
  } else {
    if (grepl('site', extent)) {
      return('site')
    } else {
      if (grepl('center', extent)) {
        return('center')
      }
    }
  }
}


#' Function to use the optimal shapefile from get_WRS_detection() to define
#' the list of WRS2 tiles for branching
#' 
#' @param detection_method optimal shapefile from get_WRS_detection()
#' @param yaml contents of the yaml .csv file
#' @returns list of WRS2 tiles
#' 
#' 
get_WRS_tiles <- function(detection_method, yaml) {
  WRS <- read_sf('data_acquisition/in/WRS2_descending.shp')
  if (detection_method == 'site') {
    locations <- tar_read(locs)
    locs <- st_as_sf(locations, 
                     coords = c('Longitude', 'Latitude'), 
                     crs = yaml$location_crs[1])
    if (st_crs(locs) == st_crs(WRS)) {
      WRS_subset <- WRS[locs,]
    } else {
      locs = st_transform(locs, st_crs(WRS))
      WRS_subset <- WRS[locs,]
    }
    write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
    return(WRS_subset$PR)
  } else {
    if (detection_method == 'centers') {
      centers <- tar_read(centers)
      centers_cntrd <- st_centroid(centers)
      if (st_crs(centers_cntrd) == st_crs(WRS)) {
        WRS_subset <- WRS[centers_cntrd,]
      } else {
        centers_cntrd = st_transform(centers_cntrd, st_crs(WRS))
        WRS_subset <- WRS[centers_cntrd,]
      }
      write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
      return(WRS_subset$PR)
    } else {
      if (detection_method == 'polygon') {
        poly <- tar_read(polygons)
        poly_cntrd <- st_centroid(poly)
        if (st_crs(poly_cntrd) == st_crs(WRS)) {
          WRS_subset <- WRS[poly_cntrd,]
        } else {
          poly_cntrd = st_transform(poly_cntrd, st_crs(WRS))
          WRS_subset <- WRS[poly_cntrd,]
        }
        write_csv(st_drop_geometry(WRS_subset), 'data_acquisition/out/WRS_subset_list.csv')
        return(WRS_subset$PR)
      }
    }
  }
}
  

#' Function to run the Landsat Pull for a specified WRS2 tile.
#' 
#' @param WRS_tile tile to run the GEE pull on
#' @returns Silently writes a text file of the current tile (for use in the
#' Python script). Silently triggers GEE to start stack acquisition per tile.
#' 
#' 
run_GEE_per_tile <- function(WRS_tile) {
  write_lines(WRS_tile, 'data_acquisition/out/current_tile.txt', sep = '')
  source_python('data_acquisition/src/runGEEperTile.py')
}