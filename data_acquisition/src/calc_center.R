#' @title Calculate POI for polygons
#' 
#' @description
#' Use polygon and 'point of inaccessibility' function (polylabelr::poi()) to 
#' determine the equivalent of Chebyshev center, furthest point from every edge 
#' of a polygon. POI function here will calculate distance in meters using the 
#' UTM coordinate system and the POI location as Latitude/Longitude in WGS84 
#' decimal degrees.
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
      poi_df  <- poi_df %>% add_row()
      one_wbd = wbd[i,]
      # get coordinates to calculate UTM zone
      coord_for_UTM = one_wbd %>% st_coordinates()
      mean_x = mean(coord_for_UTM[,1])
      mean_y = mean(coord_for_UTM[,2])
      utm_suffix = as.character(ceiling((mean_x + 180) / 6))
      utm_code = if_else(mean_y >= 0,
                         paste0('EPSG:326', utm_suffix),
                         paste0('EPSG:327', utm_suffix))
      # transform wbd to UTM
      one_wbd_utm = st_transform(one_wbd, 
                                 crs = utm_code)
      # get UTM coordinates
      coord = one_wbd_utm[i,] %>% st_coordinates()
      x = coord[,1]
      y = coord[,2]
      # using coordinates, get the poi distance
      poly_poi = poi(x,y, precision = 0.01)
      # add info to poi_df
      poi_df$rowid[i] = wbd[i,]$rowid
      poi_df$Permanent_Identifier[i] = as.character(wbd[i,]$Permanent_Identifier)
      poi_df$poi_dist_m[i] = poly_poi$dist
      # make a point feature and re-calculate decimal degrees in WGS84
      point = st_point(x = c(as.numeric(poly_poi$x),
                             as.numeric(poly_poi$y)))
      point = st_sfc(point, crs = utm_code)
      point = st_transform(st_sfc(point), crs = 'EPSG:4326')
      
      new_coords = point %>% st_coordinates()
      poi_df$poi_Longitude[i] = new_coords[,1]
      poi_df$poi_Latitude[i] = new_coords[,2]    }
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

