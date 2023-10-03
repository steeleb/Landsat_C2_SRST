#' @description
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

