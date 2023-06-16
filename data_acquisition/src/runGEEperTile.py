#import modules
import ee
import time
from datetime import date
import os 
import fiona
from pandas import read_csv

#initialize GEE
ee.Initialize()

# get locations and yml from data folder
locations = read_csv('data_acquisition/in/locs.csv')
yml = read_csv('data_acquisition/in/yml.csv')

with open('data_acquisition/out/current_tile.txt', 'r') as file:
  tiles = file.read()
    
# get EE/Google settings from yml file
proj = yml['proj'][0]
proj_folder = yml['proj_folder'][0]

# get/save start date
yml_start = yml['start_date'][0]
yml_end = yml['end_date'][0]

# configure for run
start_date_457 = '1983-01-01'
end_date_457 = '2022-04-06'
start_date_89 = '2013-01-01'
end_date_89 = date.today().strftime('%Y-%m-%d')

# gee processing settings
buffer = yml['site_buffer'][0]
cloud_filt = yml['cloud_filter'][0]
cloud_thresh = yml['cloud_thresh'][0]

# convert locations to an eeFeatureCollection
locs_feature = csv_to_eeFeat(locations, yml['location_crs'][0])

# check to see if we user desires lake extent
extent = yml['extent'][0]

if 'polygon' in extent:
  
  #if lake is in extent, check for shapefile
  shapefile = yml['polygon'][0]
  
  # if shapefile provided by user 
  if shapefile == 'True':
    # load the shapefile into a Fiona object
    with fiona.open('data_acquisition/out/lakes.shp') as src:
      shapes = [ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]])
        for feature in src]
      # Create an ee.Feature for each shape
      features = [ee.Feature(shape, {}) for shape in shapes]
    
    # Create an ee.FeatureCollection from the ee.Features
    lakes_feat = ee.FeatureCollection(features)
    

# if 'center' in extent:
#   
#   if 'site' in extent:
#     #join the two together and specifiy location type
#     
#   else:
#     # just create feature


  

##############################################
##---- CREATING EE FEATURECOLLECTIONS   ----##
##############################################


wrs = (ee.FeatureCollection('users/sntopp/wrs2_asc_desc')
  .filterMetadata('PR', 'equals', int(tiles)))

#grab images and apply scaling factors
l7 = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(start_date_457, end_date_457))
l5 = (ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(start_date_457, end_date_457))
l4 = (ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(start_date_457, end_date_457))
    
# merge collections by image processing groups
ls457 = (ee.ImageCollection(l4.merge(l5).merge(l7))
    .filterBounds(wrs))  
    
# existing band names
bn457 = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL', 'SR_CLOUD_QA', 'QA_RADSAT', 'ST_B6', 'ST_QA', 'ST_CDIST']
# new band names
bns = ['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'pixel_qa', 'cloud_qa', 'radsat_qa', 'SurfaceTemp', 'temp_qa', 'ST_CDIST']
  
# rename bands  
ls457 = ls457.select(bn457, bns)


#grab images and apply scaling factors
l8 = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(start_date_89, end_date_89))
l9 = (ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', ee.Number.parse(str(cloud_thresh))))
    .filterDate(start_date_89, end_date_89))

# merge collections by image processing groups
ls89 = ee.ImageCollection(l8.merge(l9)).filterBounds(wrs)  
    
# existing band names
bn89 = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL', 'SR_QA_AEROSOL', 'QA_RADSAT', 'ST_B10', 'ST_QA', 'ST_CDIST']
# new band names
bns = ['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2','pixel_qa', 'aerosol_qa', 'radsat_qa', 'SurfaceTemp', 'temp_qa', 'ST_CDIST']
 
# rename bands  
ls89 = ls89.select(bn89, bns)


##########################################
##---- LANDSAT 457 SITE ACQUISITION ----##
##########################################

## run the pull for LS457
if 'site' in extent:
  
  print('Starting Landsat 4, 5, 7 acquisition for site locations at tile ' + str(tiles))
  
  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  locs = (locs_feature
    .filterBounds(geo)
    .map(dpBuff))
      
  ## process 457 stack
  #snip the ls data by the geometry of the lake points    
  locs_stack_ls457 = ls457.filterBounds(locs.geometry()) 
  # map the refpull function across the 'stack', flatten to an array,
  locs_out_457 = locs_stack_ls457.map(RefPull457).flatten()
  locs_srname_457 = proj+'_point_LS457_C2_SRST_'+str(tiles)+'_v'+str(date.today())
  locs_dataOut_457 = (ee.batch.Export.table.toDrive(collection = locs_out_457,
                                          description = locs_srname_457,
                                          folder = proj_folder,
                                          fileFormat = 'csv',
                                          selectors = ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa',
                                          'min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa',
                                          'max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa',
                                          'Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp', 
                                          'Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp', 
                                          'sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa',
                                          'kurt_SurfaceTemp','prop_clouds','prop_hillShadow','pCount_dswe1', 'pCount_dswe3','min_cloud_dist', 'mean_cloud_dist','system:index']))
  #Check how many existing tasks are running and take a break of 120 secs if it's >25 
  maximum_no_of_tasks(10, 120)
  #Send next task.                                        
  locs_dataOut_457.start()
  
  print('Completed Landsat 4, 5, 7 stack acquisitions for site location at tile ' + str(tiles))
  
else: 
  print('No sites to extract Landsat 4, 5, 7 at ' + str(tiles))



#########################################
##---- LANDSAT 89 SITE ACQUISITION ----##
#########################################

if 'site' in extent:
  print('Starting Landsat 8, 9 acquisition for site locations at tile ' + str(tiles))

  geo = wrs.geometry()
  
  ## get locs feature and buffer ##
  locs = (locs_feature
    .filterBounds(geo)
    .map(dpBuff))
  
  # snip the ls data by the geometry of the lake points    
  locs_stack_89 = ls89.filterBounds(locs.geometry()) 
  # map the refpull function across the 'stack', flatten to an array,
  locs_out_89 = locs_stack_89.map(RefPull89).flatten()
  locs_srname_89 = proj+'_point_LS89_C2_SRST_'+str(tiles)+'_v'+str(date.today())
  locs_dataOut_89 = (ee.batch.Export.table.toDrive(collection = locs_out_89,
                                          description = locs_srname_89,
                                          folder = proj_folder,
                                          fileFormat = 'csv',
                                          selectors = ['med_Aerosol','med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa',
                                          'min_Aerosol','min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa',
                                          'max_Aerosol','max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa',
                                          'Q1_Aerosol','Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp',
                                          'Q3_Aerosol','Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp',
                                          'sd_Aerosol','sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa',
                                          'pCount_Aerosol','pCount_Blue', 'pCount_Green', 'pCount_Red', 'pCount_Nir', 'pCount_Swir1', 'pCount_Swir2', 'pCount_SurfaceTemp',
                                          'kurt_SurfaceTemp', 'prop_clouds','prop_medHighAero','prop_hillShadow','pCount_dswe1', 'pCount_dswe3', 'min_cloud_dist', 'mean_cloud_dist','system:index']))
  
  #Check how many existing tasks are running and take a break of 120 secs if it's >25 
  maximum_no_of_tasks(10, 120)
  #Send next task.                                        
  locs_dataOut_89.start()

  print('Completed Landsat 8, 9 stack acquisitions for site location at tile ' + str(tiles))
  
else:
  print('No sites to extract Landsat 8, 9 at tile ' +str(tiles))


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
