#import modules
import ee
import time
from datetime import date, datetime
import os 
import fiona
from pandas import read_csv

# get locations and yml from data folder
yml = read_csv('data_acquisition/in/yml.csv')

eeproj = yml['ee_proj'][0]
#initialize GEE
ee.Initialize(project = eeproj)

# get current tile
with open('data_acquisition/out/current_tile.txt', 'r') as file:
  tiles = file.read()

# get EE/Google settings from yml file
proj = yml['proj'][0]
proj_folder = yml['proj_folder'][0]

# get/save start date
yml_start = yml['start_date'][0]
yml_end = yml['end_date'][0]

if yml_end == 'today':
  yml_end = date.today().strftime('%Y-%m-%d')

# gee processing settings
buffer = yml['site_buffer'][0]
cloud_filt = yml['cloud_filter'][0]
cloud_thresh = yml['cloud_thresh'][0]

try: 
  dswe = yml['DSWE_setting'][0].astype(str)
except AttributeError: 
  dswe = yml['DSWE_setting'][0]

# get extent info
extent = yml['extent'][0]

if 'site' in extent:
  locations = read_csv('data_acquisition/in/locs.csv')
  # convert locations to an eeFeatureCollection
  locs_feature = csv_to_eeFeat(locations, yml['location_crs'][0])

if 'poly' in extent:
  #if polygon is in extent, check for shapefile
  shapefile = yml['polygon'][0]
  # if shapefile provided by user 
  if shapefile == True:
    # load the shapefile into a Fiona object
    with fiona.open('data_acquisition/out/user_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  else: #otherwise use the NHDPlus file
    # load the shapefile into a Fiona object
    with fiona.open('data_acquisition/out/NHDPlus_polygon.shp') as src:
      shapes = ([ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]]
        ) for feature in src])
  # Create an ee.Feature for each shape
  features = [ee.Feature(shape, {}) for shape in shapes]
  # Create an ee.FeatureCollection from the ee.Features
  poly_feat = ee.FeatureCollection(features)

    
if 'center' in extent:
  if yml['polygon'][0] == True:
    centers_csv = read_csv('data_acquisition/out/user_polygon_centers.csv')
    # load the shapefile into a Fiona object
    centers = csv_to_eeFeat(centers_csv, yml['poly_crs'][0])
  else: #otherwise use the NHDPlus file
    centers_csv = read_csv('data_acquisition/out/NHDPlus_polygon_centers.csv')
    centers = csv_to_eeFeat(centers_csv, 'EPSG:4326')
  # Create an ee.FeatureCollection from the ee.Features
  ee_centers = ee.FeatureCollection(centers)    

  

##############################################
##---- CREATING EE FEATURECOLLECTIONS   ----##
##############################################


wrs = (ee.FeatureCollection('projects/ee-ls-c2-srst/assets/WRS2_descending')
  .filterMetadata('PR', 'equals', tiles))

#grab images and apply scaling factors
l7 = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .map(apply_scale_factors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end))
l5 = (ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .map(apply_scale_factors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end))
l4 = (ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
    .map(apply_scale_factors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end))
    
# merge collections by image processing groups
ls457 = (ee.ImageCollection(l4.merge(l5).merge(l7))
    .filterBounds(wrs))  
    
# existing band names
bn457 = (['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 
  'QA_PIXEL', 'SR_CLOUD_QA', 'QA_RADSAT', 'ST_B6', 
  'ST_QA', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  
# new band names
bns457 = (['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 
  'pixel_qa', 'cloud_qa', 'radsat_qa', 'SurfaceTemp', 
  'temp_qa', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  
# rename bands  
ls457 = ls457.select(bn457, bns457)


#grab images and apply scaling factors
l8 = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .map(apply_scale_factors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end))
l9 = (ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .map(apply_scale_factors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(yml_start, yml_end))

# merge collections by image processing groups
ls89 = ee.ImageCollection(l8.merge(l9)).filterBounds(wrs)  
    
# existing band names
bn89 = (['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 
  'QA_PIXEL', 'SR_QA_AEROSOL', 'QA_RADSAT', 'ST_B10', 
  'ST_QA', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
  
# new band names
bns89 = (['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2',
  'pixel_qa', 'aerosol_qa', 'radsat_qa', 'SurfaceTemp', 
  'temp_qa', 'ST_CDIST', 'ST_ATRAN', 'ST_DRAD', 'ST_EMIS',
  'ST_EMSD', 'ST_TRAD', 'ST_URAD'])
 
# rename bands  
ls89 = ls89.select(bn89, bns89)


##########################################
##---- LANDSAT 457 SITE ACQUISITION ----##
##########################################

## run the pull for LS457
if 'site' in extent:
  
  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  feat = (locs_feature
    .filterBounds(geo)
    .map(dp_buff))
      
  ## process 457 stack
  #snip the ls data by the geometry of the location points    
  locs_stack_ls457 = ls457.filterBounds(feat.geometry()) 
  
  # map the refpull function across the 'stack', flatten to an array
  if '1' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE1 acquisition for site locations at tile ' + str(tiles))
    locs_out_457_D1 = locs_stack_ls457.map(ref_pull_457_DSWE1).flatten()
    locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D1 = proj+'_point_LS457_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                            description = locs_srname_457_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_457_D1.start()
    print('Completed Landsat 4, 5, 7 DSWE 1 stack acquisitions for site location at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 1 stack for Landsat 4, 5, 7 for sites.')
  
  if '3' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE3 acquisition for site locations at tile ' + str(tiles))
    locs_out_457_D3 = locs_stack_ls457.map(ref_pull_457_DSWE3).flatten()
    locs_out_457_D3 = locs_out_457_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D3 = proj+'_point_LS457_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_457_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D3,
                                            description = locs_srname_457_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_457_D3.start()
    print('Completed Landsat 4, 5, 7 DSWE 3 stack acquisitions for site location at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 3 stack for Landsat 4, 5, 7 for sites.')

else: 
  print('No sites to extract Landsat 4, 5, 7 at ' + str(tiles))



#########################################
##---- LANDSAT 89 SITE ACQUISITION ----##
#########################################

if 'site' in extent:

  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  feat = (locs_feature
    .filterBounds(geo)
    .map(dp_buff))
  
  # snip the ls data by the geometry of the location points    
  locs_stack_ls89 = ls89.filterBounds(feat.geometry()) 
  
  if '1' in dswe:
    print('Starting Landsat 8, 9 DSWE1 acquisition for site locations at tile ' + str(tiles))
    locs_out_89_D1 = locs_stack_ls89.map(ref_pull_89_DSWE1).flatten()
    locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D1 = proj+'_point_LS89_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                            description = locs_srname_89_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_89_D1.start()
    print('Completed Landsat 8, 9 DSWE 1 stack acquisitions for site location at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 8, 9 for sites.')
  
  if '3' in dswe:
    print('Starting Landsat 8, 9 DSWE3 acquisition for site locations at tile ' + str(tiles))
    locs_out_89_D3 = locs_stack_ls89.map(ref_pull_89_DSWE3).flatten()
    locs_out_89_D3 = locs_out_89_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D3 = proj+'_point_LS89_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_89_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D3,
                                            description = locs_srname_89_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_89_D3.start()
    print('Completed Landsat 8, 9 DSWE 3 stack acquisitions for site location at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 3 stack for Landsat 8,9 for sites.')

else: print('No sites to extract Landsat 8, 9 at tile ' +str(tiles))
 
 
 
#############################################
##---- LANDSAT 457 POLYGON ACQUISITION ----##
#############################################

## run the pull for LS457
if 'poly' in extent:
  
  geo = wrs.geometry()
  
  ## get the polygon stack ##
  feat = poly_feat.filterBounds(geo)
    
  # snip the ls data by the geometry of the location points    
  poly_stack_ls457 = ls457.filterBounds(feat.geometry()) 
  
  # map the refpull function across the 'stack', flatten to an array
  if '1' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE1 acquisition for polygons at tile ' + str(tiles))
    poly_out_457_D1 = poly_stack_ls457.map(ref_pull_457_DSWE1).flatten()
    poly_out_457_D1 = poly_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
    poly_srname_457_D1 = proj+'_poly_LS457_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    poly_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = poly_out_457_D1,
                                            description = poly_srname_457_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    poly_dataOut_457_D1.start()
    print('Completed Landsat 4, 5, 7 DSWE 1 stack acquisitions for polygon at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 4, 5, 7 for polygons.')
  
  if '3' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE3 acquisition for polygons at tile ' + str(tiles))
    poly_out_457_D3 = poly_stack_ls457.map(ref_pull_457_DSWE3).flatten()
    poly_out_457_D3 = poly_out_457_D3.filter(ee.Filter.notNull(['med_Blue']))
    poly_srname_457_D3 = proj+'_poly_LS457_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    poly_dataOut_457_D3 = (ee.batch.Export.table.toDrive(collection = poly_out_457_D3,
                                            description = poly_srname_457_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    poly_dataOut_457_D3.start()
    print('Completed Landsat 4, 5, 7 DSWE 3 stack acquisitions for polygons at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 3 stack for Landsat 4, 5, 7 for polygons.')

else: print('No polygons to extract Landsat 4, 5, 7 at ' + str(tiles))


############################################
##---- LANDSAT 89 POLYGON ACQUISITION ----##
############################################

if 'poly' in extent:

  geo = wrs.geometry()
  
  ## get the polygon stack ##
  feat = poly_feat.filterBounds(geo)
    
  # snip the ls data by the geometry of the location points    
  poly_stack_ls89 = ls89.filterBounds(feat.geometry()) 
  
  if '1' in dswe:
    print('Starting Landsat 8, 9 DSWE1 acquisition for polygons at tile ' + str(tiles))
    poly_out_89_D1 = poly_stack_ls89.map(ref_pull_89_DSWE1).flatten()
    poly_out_89_D1 = poly_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
    poly_srname_89_D1 = proj+'_poly_LS89_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    poly_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = poly_out_89_D1,
                                            description = poly_srname_89_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    poly_dataOut_89_D1.start()
    print('Completed Landsat 8, 9 DSWE 1 stack acquisitions for polygons at tile ' + str(tiles))
  else:
    print('Not configured to acquire DSWE 3 stack for Landsat 4,5,7 for polygons.')
  
  if '3' in dswe:
    print('Starting Landsat 8, 9 DSWE3 acquisition for polygons at tile ' + str(tiles))
    poly_out_89_D3 = poly_stack_ls89.map(ref_pull_89_DSWE3).flatten()
    poly_out_89_D3 = poly_out_89_D3.filter(ee.Filter.notNull(['med_Blue']))
    poly_srname_89_D3 = proj+'_poly_LS89_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    poly_dataOut_89_D3 = (ee.batch.Export.table.toDrive(collection = poly_out_89_D3,
                                            description = poly_srname_89_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    poly_dataOut_89_D3.start()
    print('Completed Landsat 8, 9 DSWE 3 stack acquisitions for polygons at tile ' + str(tiles))
  else:
    print('Not configured to acquire DSWE 3 stack for Landsat 8,9 for polygons.')
  
else:
  print('No polygons to extract Landsat 8, 9 at tile ' +str(tiles))


##########################################
##---- LANDSAT 457 CENTERS ACQUISITION ----##
##########################################

## run the pull for LS457
if 'center' in extent:
  
  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  feat = (ee_centers
    .filterBounds(geo)
    .map(dp_buff))
      
  ## process 457 stack
  #snip the ls data by the geometry of the location points    
  locs_stack_ls457 = ls457.filterBounds(feat.geometry()) 
  
  # map the refpull function across the 'stack', flatten to an array
  if '1' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE 1 acquisition for centers at tile ' + str(tiles))
    locs_out_457_D1 = locs_stack_ls457.map(ref_pull_457_DSWE1).flatten()
    locs_out_457_D1 = locs_out_457_D1.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D1 = proj+'_centers_LS457_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_457_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D1,
                                            description = locs_srname_457_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_457_D1.start()
    print('Completed Landsat 4, 5, 7 DSWE 1 stack acquisitions for centers at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 4, 5, 7 for centers.')
  
  if '3' in dswe:
    print('Starting Landsat 4, 5, 7 DSWE 3 acquisition for centers at tile ' + str(tiles))
    locs_out_457_D3 = locs_stack_ls457.map(ref_pull_457_DSWE3).flatten()
    locs_out_457_D3 = locs_out_457_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_457_D3 = proj+'_centers_LS457_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_457_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_457_D3,
                                            description = locs_srname_457_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_457_D3.start()
    print('Completed Landsat 4, 5, 7 DSWE 3 stack acquisitions for polygon centers at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 3 stack for Landsat 4, 5, 7 for centers.')

else: 
  print('No centers to extract Landsat 4, 5, 7 at ' + str(tiles))



#########################################
##---- LANDSAT 89 CENTERS ACQUISITION ----##
#########################################

if 'center' in extent:
  print('Starting Landsat 8, 9 acquisition for centers at tile ' + str(tiles))

  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  feat = (ee_centers
    .filterBounds(geo)
    .map(dp_buff))
  
  # snip the ls data by the geometry of the location points    
  locs_stack_ls89 = ls89.filterBounds(feat.geometry()) 
  
  if '1' in dswe:
    locs_out_89_D1 = locs_stack_ls89.map(ref_pull_89_DSWE1).flatten()
    locs_out_89_D1 = locs_out_89_D1.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D1 = proj+'_centers_LS89_C2_SRST_DSWE1_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_89_D1 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D1,
                                            description = locs_srname_89_D1,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_89_D1.start()
    print('Completed Landsat 8, 9 DSWE 1 stack acquisitions for centersn at tile ' + str(tiles))
  
  else: print('Not configured to acquire DSWE 1 stack for Landsat 8, 9 for centers.')
  
  if '3' in dswe:
    locs_out_89_D3 = locs_stack_ls89.map(ref_pull_89_DSWE3).flatten()
    locs_out_89_D3 = locs_out_89_D3.filter(ee.Filter.notNull(['med_Blue']))
    locs_srname_89_D3 = proj+'_centers_LS89_C2_SRST_DSWE3_'+str(tiles)+'_v'+str(date.today())
    locs_dataOut_89_D3 = (ee.batch.Export.table.toDrive(collection = locs_out_89_D3,
                                            description = locs_srname_89_D3,
                                            folder = proj_folder,
                                            fileFormat = 'csv',
                                            selectors = ['system:index',
                                            'med_Aerosol', 'med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 
                                            'med_SurfaceTemp', 'med_temp_qa', 'med_atran', 'med_drad', 'med_emis',
                                            'med_emsd', 'med_trad', 'med_urad',
                                            'min_SurfaceTemp', 'min_cloud_dist',
                                            'sd_Aerosol', 'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp',
                                            'mean_Aerosol', 'mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 
                                            'mean_SurfaceTemp',
                                            'kurt_SurfaceTemp', 
                                            'pCount_dswe_gt0', 'pCount_dswe1', 'pCount_dswe3', 
                                            'prop_clouds','prop_hillShadow','mean_hillShade']))
    #Check how many existing tasks are running and take a break of 120 secs if it's >25 
    maximum_no_of_tasks(10, 120)
    #Send next task.                                        
    locs_dataOut_89_D3.start()
    print('Completed Landsat 8, 9 DSWE 3 stack acquisitions for polygon centers at tile ' + str(tiles))
    
  else: print('Not configured to acquire DSWE 3 stack for Landsat 8,9 for centers.')

else: print('No centers to extract Landsat 8, 9 at tile ' +str(tiles))
 


##############################################
##---- LANDSAT 457 METADATA ACQUISITION ----##
##############################################

print('Starting Landsat 4, 5, 7 metadata acquisition for tile ' +str(tiles))

## get metadata ##
meta_srname_457 = proj+'_metadata_LS457_C2_'+str(tiles)+'_v'+str(date.today())
meta_dataOut_457 = (ee.batch.Export.table.toDrive(collection = ls457,
                                        description = meta_srname_457,
                                        folder = proj_folder,
                                        fileFormat = 'csv'))

#Check how many existing tasks are running and take a break of 120 secs if it's >25 
maximum_no_of_tasks(10, 120)
#Send next task.                                        
meta_dataOut_457.start()

print('Completed Landsat 4, 5, 7 metadata acquisition for tile ' + str(tiles))


#############################################
##---- LANDSAT 89 METADATA ACQUISITION ----##
#############################################

print('Starting Landsat 8, 9 metadata acquisition for tile ' +str(tiles))

## get metadata ##
meta_srname_89 = proj+'_metadata_LS89_C2_'+str(tiles)+'_v'+str(date.today())
meta_dataOut_89 = (ee.batch.Export.table.toDrive(collection = ls89,
                                        description = meta_srname_89,
                                        folder = proj_folder,
                                        fileFormat = 'csv'))

#Check how many existing tasks are running and take a break of 120 secs if it's >25 
maximum_no_of_tasks(10, 120)
#Send next task.                                        
meta_dataOut_89.start()
  
  
print('completed Landsat 8, 9 metadata acquisition for tile ' + str(tiles))


#############################################
##---- DOCUMENT Landsat IDs ACQUIRED   ----##
#############################################

ls89_id_stack = ls89.aggregate_array('L1_LANDSAT_PRODUCT_ID').getInfo()
ls457_id_stack = ls457.aggregate_array('L1_LANDSAT_PRODUCT_ID').getInfo()

# open file in write mode and save each id as a row
with open(('data_acquisition/out/L89_stack_ids_v'+str(date.today())+'.txt'), 'w') as fp:
    for id in ls89_id_stack:
        # write each item on a new line
        fp.write("%s\n" % id)
    print('Done')

# open file in write mode and save each id as a row
with open(('data_acquisition/out/L457_stack_ids_v'+str(date.today())+'.txt'), 'w') as fp:
    for id in ls457_id_stack:
        # write each item on a new line
        fp.write("%s\n" % id)
    print('Done')
    
