#in order to successfully run this in RStudio, you will need to initiate the conda env 
#to do so, type the following in the console:
#reticulate::use_condaenv(file.path(getwd(), "env"))
# you will need to have the Landsat_C2_SRST project open.

import ee
import math
import time

ee.Initialize(project = 'ee-ls-c2-srst')

## Deepest point calculation adapted from Xiao Yang
### https: // doi.org / 10.5281 / zenodo.4136754
### Functions
def get_scale(polygon):
    radius = polygon.get('areasqkm')
    radius = ee.Number(radius).divide(math.pi).sqrt().multiply(1000)
    scale = radius.divide(20)
    #scale = ee.Algorithms.If(ee.Number(scale).lte(10),10,scale)
    scale = ee.Algorithms.If(ee.Number(scale).gte(500),500,scale)
    return ee.Number(scale)


def getUTMProj(lon, lat):
    # see
    # https: // apollomapping.com / blog / gtm - finding - a - utm - zone - number - easily and
    # https: // sis.apache.org / faq.html
    utmCode = ee.Number(lon).add(180).divide(6).ceil().int()
    output = ee.Algorithms.If(ee.Number(lat).gte(0),
                              ee.String('EPSG:326').cat(utmCode.format('%02d')),
                              ee.String('EPSG:327').cat(utmCode.format('%02d')))
    return output

def GetLakeCenters(polygon):

    ## Calculate both the deepest point an centroid
    ## for the inpout polygon ( or multipolygon)
    ## for each input, export geometries for both centroid and deepest point and their distance to shore.
    scale = get_scale(polygon)
    geo = polygon.geometry()
    ct = geo.centroid(scale)
    utmCode = getUTMProj(ct.coordinates().getNumber(0), ct.coordinates().getNumber(1))

    polygonImg = ee.Image.constant(1).toByte().paint(ee.FeatureCollection(ee.Feature(geo, None)), 0)

    dist = polygonImg.fastDistanceTransform(2056).updateMask(polygonImg.Not()).sqrt().reproject(utmCode, None, scale).multiply(scale) # convert unit from pixel to meter

    # dist = (polygonImg.fastDistanceTransform(2056).updateMask(polygonImg.not ())
    # .sqrt().reproject('EPSG:4326', None, scale).multiply(scale)  # convert unit from pixel to meter

    maxDistance = (dist.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=geo,
        scale=scale,
        bestEffort=True,
        tileScale=2 
    ).getNumber('distance').int16())

    outputDp = (ee.Feature(dist.addBands(ee.Image.pixelLonLat()).updateMask(dist.gte(maxDistance))
                          .sample(geo, scale).first()))

    dp = ee.Geometry.Point([outputDp.get('longitude'), outputDp.get('latitude')])

    regions = ee.FeatureCollection([ee.Feature(dp, {'type': 'csc'})])

    output = dist.sampleRegions(
        collection=regions,
        properties=['type'],
        scale=scale,
        tileScale=2,
        geometries=True)

    return (ee.Feature(output.first()).copyProperties(polygon,['permanent','areasqkm']))


def buff_dp(dp):
    return dp.buffer(dp.getNumber('distance'))


def maximum_no_of_tasks(MaxNActive, waitingPeriod):
    ## maintain a maximum number of active tasks
    time.sleep(10)
    ## initialize submitting jobs
    ts = list(ee.batch.Task.list())

    NActive = 0
    for task in ts:
        if ('RUNNING' in str(task) or 'READY' in str(task)):
            NActive += 1
    ## wait if the number of current active tasks reach the maximum number
    ## defined in MaxNActive
    while (NActive >= MaxNActive):
        time.sleep(waitingPeriod)
        ts = list(ee.batch.Task.list())
        NActive = 0
        for task in ts:
            if ('RUNNING' in str(task) or 'READY' in str(task)):
                NActive += 1
    return ()


def calc_area(feature):
    return(feature.set('area_calc',feature.area().divide(1e6)))

## Get NHD Asset Lists
assets_done = ee.data.listAssets({'parent': 'projects/ee-ls-c2-srst/assets/NHD_centers'})['assets']
ids_done = [i['id'].split('/')[-1] for i in assets_done]
state_assets = ee.data.listAssets({'parent': 'projects/sat-io/open-datasets/NHD'})['assets']
states_left = [i for i in assets_parent if i['id'].split('/')[-1] not in ids_done]
#assets_parent = [i for i in assets_parent if i['id'].split('/')[-1] not in ['NHD_MO','NHD_TX','NHD_AK']]

## Get State asset
states = ee.FeatureCollection('TIGER/2018/States')

## for each state, run each grid cell and then export to file
for i in range(len(states_left)):
    state_asset = states_left[i]['id']
    state_waterbody = (ee.FeatureCollection(f"{state_asset}/NHDWaterbody")
      .filter(ee.Filter.gte('areasqkm',0.001))
      .filter(ee.Filter.lte('areasqkm',5000))  #Remove Great Lakes
      .filter(ee.Filter.inList('ftype',[361,436,390]))) #Only grab lakes, ponds, and reservoirs
    
    ## Added to trouble shoot NM where some of the NHD areas are don't match the actual polygon areas
    state_waterbody=ee.FeatureCollection(state_waterbody.map(calc_area)).filter(ee.Filter.gte('area_calc',0.001))
    
    #get the state outline
    state_usps = state_asset.split('_')[-1]
    state_bound = states.filter(ee.Filter.eq('STUSPS', state_usps))

    # break down the state into a grid
    state_geo = state_bound.geometry()
    state_grid = ee.Geometry(state_geo).coveringGrid(state_geo.projection())

    grid_count = state_grid.size().getInfo()

    for g in range(grid_count):
      grid_cell = state_grid.toList(state_grid.size()).get(g)
      grid_cell = ee.Feature(grid_cell)
      grid_waterbody = state_waterbody.filterBounds(grid_cell.geometry())
      
      if grid_waterbody.size().getInfo() > 0:
    
        csc = grid_waterbody.map(GetLakeCenters)
  
        dataOut = (ee.batch.Export.table.toAsset(collection=dp,
          description=state_asset.split('/')[-1]+'_'+str(g)+'_'+str(grid_count),
          assetId=f"projects/ee-ls-c2-srst/assets/NHD_centers/{state_asset.split('/')[-1]}_{str(g)}"))
  
        ## Check how many existing tasks are running and take a break if it's >15
        maximum_no_of_tasks(5, 240)
        ## Send next task.
        dataOut.start()
      
    print(state_asset.split('/')[-1])


state_csc = ee.data.listAssets({'parent': 'projects/ee-ls-c2-srst/assets/NHD_centers'})['assets']

for i in state_csc:
    csc = ee.FeatureCollection(i['id'])
    id =  i['id'].split('/')[-1]
    cscOut = ee.batch.Export.table.toDrive(csc,id,'EE_CSC_Exports',id)
    maximum_no_of_tasks(15, 60)
    cscOut.start()
