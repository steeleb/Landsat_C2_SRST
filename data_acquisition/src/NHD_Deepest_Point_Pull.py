import ee
import math
import time
ee.Initialize()

## Deepest point calculation adapted from Xiao Yang
### https: // doi.org / 10.5281 / zenodo.4136754
### Functions
def get_scale(polygon):
    area = polygon.get('areasqkm')
    radius = ee.Number(area).divide(math.pi).sqrt().multiply(1000)
    scale = radius.divide(20)
    scale = ee.Algorithms.If(ee.Number(scale).lte(10),10,scale)
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
        tileScale=1
    ).getNumber('distance').int16())

    outputDp = (ee.Feature(dist.addBands(ee.Image.pixelLonLat()).updateMask(dist.gte(maxDistance))
                          .sample(geo, scale).first()))

    dp = ee.Geometry.Point([outputDp.get('longitude'), outputDp.get('latitude')])

    regions = ee.FeatureCollection([ee.Feature(dp, {'type': 'dp'})])

    output = dist.sampleRegions(
        collection=regions,
        properties=['type'],
        scale=scale,
        tileScale=1,
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


## Remove geometries
def remove_geo(image):
  """ Funciton to remove the geometry from an ee.Image
  
  Args:
      image: ee.Image of an ee.ImageCollection
      
  Returns:
      ee.Image with the geometry removed
  """
  return image.setGeometry(None)


def get_lat_long(feature):
  lat_lon = feature.geometry().coordinates()
  lat = lat_lon.get(1)
  lon = lat_lon.get(0)
  return (feature.set({
    'latitude': lat,
    'longitude': lon}))


## Get NHD Asset Lists
state_assets = ee.data.listAssets({'parent': 'projects/sat-io/open-datasets/NHD'})['assets']


## Get State asset
states = ee.FeatureCollection('TIGER/2018/States')


## for each state, run each grid cell and then export to file
for i in range(len(state_assets)):
    state_asset = state_assets[i]['id']
    state_waterbody = (ee.FeatureCollection(f"{state_asset}/NHDWaterbody")
      .filter(ee.Filter.gte('areasqkm',0.01))
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
        csc = ee.FeatureCollection(csc).map(get_lat_long)
        
        name = state_asset.split('/')[-1]+'_'+str(g)+'_'+str(grid_count)
        
        cscOut = (ee.batch.Export.table.toDrive(collection = csc, 
          description = name,
          folder = 'EE_CSC_Exports',
          fileFormat = 'CSV',
          selectors = ('permanent', 'latitude', 'longitude', 'areasqkm', 'distance', 'type')))
        maximum_no_of_tasks(3, 60)
        cscOut.start()
      
    print(state_asset.split('/')[-1])

#f"projects/earthengine-legacy/assets/users/sntopp/NHD/{state_asset.split('/')[-1]}/NHDDeepestPoint"


state_dps = ee.data.listAssets({'parent': 'projects/earthengine-legacy/assets/users/sntopp/NHD/DeepestPoint'})['assets']

for i in state_dps:
    dps = ee.FeatureCollection(i['id'])
    id =  i['id'].split('/')[-1]
    dpsOut = ee.batch.Export.table.toDrive(dps,id,'EE_DP_Exports',id)
    maximum_no_of_tasks(15, 60)
    dpsOut.start()