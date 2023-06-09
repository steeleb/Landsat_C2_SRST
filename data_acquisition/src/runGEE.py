#import modules
import ee
import os 
import fiona
from pandas import read_csv
import pickle
import json

#initialize GEE
ee.Initialize()


# get locations and yml from data folder
locs = read_csv('data_acquisition/in/locs.csv')
yml = read_csv('data_acquisition/in/yml.csv')

# get EE/Google settings from yml file
proj = yml['proj'][0]
proj_folder = yml['proj_folder'][0]

# get/save start date
yml_start = yml['start_date'][0]
yml_end = yml['end_date'][0]

# configure for run
start_date_457 = '1983-01-01'
end_date_457 = '2022-04-06'

# gee processing settings
buffer = yml['site_buffer'][0]
cloud_filt = yml['cloud_filter'][0]
cloud_thresh = yml['cloud_thresh'][0]

# convert locations to an eeFeatureCollection
locs_feature = csv_to_eeFeat(locs, yml['location_crs'][0])

# check to see if we user desires lake extent
extent = yml['extent'][0]

if 'lake' in extent:
  
  #if lake is in extent, check for shapefile
  shapefile = yml['lake_poly'][0]
  
  # if shapefile provided by user 
  if shapefile == 'True':
    # pull directory path from yml
    shpDir = yml['lake_poly_dir'][0]
    shpFile = yml['lake_poly_file'][0]
    
    # load the shapefile into a Fiona object
    with fiona.open(os.path.join(shpDir+shpFile)) as src:
      shapes = [ee.Geometry.Polygon(
        [[x[0], x[1]] for x in feature['geometry']['coordinates'][0]])
        for feature in src]
      # Create an ee.Feature for each shape
      features = [ee.Feature(shape, {}) for shape in shapes]
    
    # Create an ee.FeatureCollection from the ee.Features
    lakes_feat = ee.FeatureCollection(features)
    
    #else: pull in poly file from getNHD in R (out directory)
      

#if 'center' in extent:
  



wrs = (ee.FeatureCollection('users/sntopp/wrs2_asc_desc')
    .filterBounds(locs_feature)) #grab only wrs overlap with dp
wrs = wrs.filterMetadata('MODE', 'equals', 'D') #only grab the descending (daytime) path
    
pr = wrs.aggregate_array('PR').getInfo() #create PathRow list


#grab images and apply scaling factors
l7 = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', cloud_thresh))
    .filterDate(r.start_date_457, r.end_date_457))
l5 = (ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', cloud_thresh))
    .filterDate(r.start_date_457, r.end_date_457))
l4 = (ee.ImageCollection('LANDSAT/LT04/C02/T1_L2')
    .map(applyScaleFactors)
    .filter(ee.Filter.lt('CLOUD_COVER', cloud_thresh))
    .filterDate(r.start_date_457, r.end_date_457))
    
# merge collections by image processing groups
ls457 = (ee.ImageCollection(l4.merge(l5).merge(l7))
    .filterBounds(wrs))  
    
# existing band names
bn457 = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL', 'SR_CLOUD_QA', 'QA_RADSAT', 'ST_B6', 'ST_QA', 'ST_CDIST']
# new band names
bns = ['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'pixel_qa', 'cloud_qa', 'radsat_qa', 'SurfaceTemp', 'temp_qa', 'ST_CDIST']
  
# rename bands  
ls457 = ls457.select(bn457, bns)


## Set up a counter and a list to keep track of what's been done already
counter = 0
done = []    

pr = [i for i in pr if i not in done] #this removes pathrow values that have already been processed


## run the pull!
for tiles in pr:
  tile = wrs.filterMetadata('PR', 'equals', tiles)
  
  ## get locs feature ##
  locs = (locs_feature.filterBounds(tile.geometry())
    .map(dpBuff))
  extent = locs
  # snip the ls data by the geometry of the lake points    
  locs_stack = ls457.filterBounds(locs.geometry()) 
  # map the refpull function across the 'stack', flatten to an array,
  locs_out = locs_stack.map(RefPull457).flatten()
  locs_srname = r.proj+'_point_LS457_C2_SRST_'+str(tiles)+'_v'+str(date.today())
  locs_dataOut = (ee.batch.Export.table.toDrive(collection = locs_out,
                                          description = locs_srname,
                                          folder = r.proj_folder,
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
  locs_dataOut.start()
  print('locs extraction for tile ' + str(tiles) + ' sent to GEE')
  
  ## get lakes stack ##
  # if there is a lakes feature, run the lakes stack.
  try:
    lakes = lakes_feat.filterBounds(tile.geometry())
    extent = lakes
    # snip the ls data by the geometry of the lake points    
    lakes_stack = ls457.filterBounds(lakes.geometry()) 
    # map the refpull function across the 'stack', flatten to an array,
    lakes_out = lakes_stack.map(RefPull457).flatten()
    lakes_srname = r.proj+'_lake_LS457_C2_SRST_'+str(tiles)+'_v'+str(date.today())
    lakes_dataOut = (ee.batch.Export.table.toDrive(collection = lakes_out,
                                            description = lakes_srname,
                                            folder = r.proj_folder,
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
    lakes_dataOut.start()
    print('lakes extraction for tile ' + str(tiles) + ' sent to GEE')
  except NameError:
    print('No lake feature to extract')
  
  ## get metadata ##
  meta_srname = r.proj+'_metadata_LS457_C2_'+str(tiles)+'_v'+str(date.today())
  meta_dataOut = (ee.batch.Export.table.toDrive(collection = ls457,
                                          description = meta_srname,
                                          folder = r.proj_folder,
                                          fileFormat = 'csv'))
  
  #Check how many existing tasks are running and take a break of 120 secs if it's >25 
  maximum_no_of_tasks(10, 120)
  #Send next task.                                        
  meta_dataOut.start()

  #advance the counter
  counter = counter + 1
  done.append(tiles)
  print('done with number ' + str(counter) + ', tile ' + str(tiles))
  
print('done with all tiles')
