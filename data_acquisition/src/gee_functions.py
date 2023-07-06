# Python-based GEE functions

# create an eeFeature from the location info
def csv_to_eeFeat(df, proj):
  features=[]
  for i in range(df.shape[0]):
    x,y = df.Longitude[i],df.Latitude[i]
    latlong =[x,y]
    loc_properties = {'system:index':str(df.id[i]), 'id':str(df.id[i])}
    g=ee.Geometry.Point(latlong, proj) 
    feature = ee.Feature(g, loc_properties)
    features.append(feature)
  ee_object = ee.FeatureCollection(features)
  return ee_object


## per GEE code to scale SR 
def applyScaleFactors(image):
  opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
  thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
  return image.addBands(opticalBands, None, True).addBands(thermalBands, None,True)


## Buffer the lake sites
def dpBuff(i):
  return i.buffer(ee.Number.parse(str(buffer)))


def addRadMask(image):
  #grab the radsat band
  satQA = image.select('radsat_qa')
  # all must be non-saturated per pixel
  satMask = satQA.eq(0).rename('radsat')
  return image.addBands(satMask).updateMask(satMask)


def cfMask(image):
  #grab just the pixel_qa info
  qa = image.select('pixel_qa')
  cloudqa = (qa.bitwiseAnd(1 << 1).rename('cfmask') #dialated clouds value 1
    .where(qa.bitwiseAnd(1 << 3), ee.Image(2)) # clouds value 2
    .where(qa.bitwiseAnd(1 << 4), ee.Image(3)) # cloud shadows value 3
    .where(qa.bitwiseAnd(1 << 5), ee.Image(4))) # snow value 4
  return image.addBands(cloudqa)


def srCloudMask(image):
  srCloudQA = image.select('cloud_qa')
  srMask = (srCloudQA.bitwiseAnd(1 << 1).rename('sr_cloud') # cloud
    .where(srCloudQA.bitwiseAnd(1 << 2), ee.Image(2)) # cloud shadow
    .where(srCloudQA.bitwiseAnd(1 << 3), ee.Image(3)) # adjacent to cloud
    .where(srCloudQA.bitwiseAnd(1 << 4), ee.Image(4))) # snow/ice
  return image.addBands(srMask)

# grabbing qualitative measure of aerosol Level

def srAerosol(image):
  aerosolQA = image.select('aerosol_qa')
  medHighAero = aerosolQA.bitwiseAnd(1 << 7).rename('medHighAero')# pull out mask out where aeorosol is med and high
  return image.addBands(medHighAero)



# modified normalized difference water index
def Mndwi(image):
  return (image.expression('(GREEN - SWIR1) / (GREEN + SWIR1)', {
    'GREEN': image.select(['Green']),
    'SWIR1': image.select(['Swir1'])
  }))
  

# multi-band Spectral Relationship Visible
def Mbsrv(image):
  return (image.select(['Green']).add(image.select(['Red'])).rename('mbsrv'))


# Multi-band Spectral Relationship Near infrared
def Mbsrn(image):
  return (image.select(['Nir']).add(image.select(['Swir1'])).rename('mbsrn'))


# Normalized Difference Vegetation Index
def Ndvi(image):
  return (image.expression('(NIR - RED) / (NIR + RED)', {
    'RED': image.select(['Red']),
    'NIR': image.select(['Nir'])
  }))


# Automated Water Extent Shadow
def Awesh(image):
  return (image.expression('Blue + 2.5 * Green + (-1.5) * mbsrn + (-0.25) * Swir2', {
    'Blue': image.select(['Blue']),
    'Green': image.select(['Green']),
    'mbsrn': Mbsrn(image).select(['mbsrn']),
    'Swir2': image.select(['Swir2'])
  }))


## The DSWE Function itself    
def DSWE(i):
  mndwi = Mndwi(i)
  mbsrv = Mbsrv(i)
  mbsrn = Mbsrn(i)
  awesh = Awesh(i)
  swir1 = i.select(['Swir1'])
  nir = i.select(['Nir'])
  ndvi = Ndvi(i)
  blue = i.select(['Blue'])
  swir2 = i.select(['Swir2'])
  # These thresholds are taken from the LS Collection 2 DSWE Data Format Control Book
  # Inputs are meant to be scaled reflectance values 
  t1 = mndwi.gt(0.124) # MNDWI greater than Wetness Index Threshold
  t2 = mbsrv.gt(mbsrn) # MBSRV greater than MBSRN
  t3 = awesh.gt(0) #AWESH greater than 0
  t4 = (mndwi.gt(-0.44)  #Partial Surface Water 1 thresholds
   .And(swir1.lt(0.09)) #900 for no scaling (LS Collection 1)
   .And(nir.lt(0.15)) #1500 for no scaling (LS Collection 1)
   .And(ndvi.lt(0.7)))
  t5 = (mndwi.gt(-0.5) #Partial Surface Water 2 thresholds
   .And(blue.lt(0.1)) #1000 for no scaling (LS Collection 1)
   .And(swir1.lt(0.3)) #3000 for no scaling (LS Collection 1)
   .And(swir2.lt(0.1)) #1000 for no scaling (LS Collection 1)
   .And(nir.lt(0.25))) #2500 for no scaling (LS Collection 1)
  t = (t1
    .add(t2.multiply(10))
    .add(t3.multiply(100))
    .add(t4.multiply(1000))
    .add(t5.multiply(10000)))
  noWater = (t.eq(0)
    .Or(t.eq(1))
    .Or(t.eq(10))
    .Or(t.eq(100))
    .Or(t.eq(1000)))
  hWater = (t.eq(1111)
    .Or(t.eq(10111))
    .Or(t.eq(11011))
    .Or(t.eq(11101))
    .Or(t.eq(11110))
    .Or(t.eq(11111)))
  mWater = (t.eq(111)
    .Or(t.eq(1011))
    .Or(t.eq(1101))
    .Or(t.eq(1110))
    .Or(t.eq(10011))
    .Or(t.eq(10101))
    .Or(t.eq(10110))
    .Or(t.eq(11001))
    .Or(t.eq(11010))
    .Or(t.eq(11100)))
  pWetland = t.eq(11000)
  lWater = (t.eq(11)
    .Or(t.eq(101))
    .Or(t.eq(110))
    .Or(t.eq(1001))
    .Or(t.eq(1010))
    .Or(t.eq(1100))
    .Or(t.eq(10000))
    .Or(t.eq(10001))
    .Or(t.eq(10010))
    .Or(t.eq(10100)))
  iDswe = (noWater.multiply(0)
    .add(hWater.multiply(1))
    .add(mWater.multiply(2))
    .add(pWetland.multiply(3))
    .add(lWater.multiply(4)))
  return iDswe.rename('dswe')


def CalcHillShades(image, geo):
  MergedDEM = ee.Image("users/eeProject/MERIT").clip(geo.buffer(3000))
  hillShade = ee.Terrain.hillshade(MergedDEM, 
    ee.Number(image.get('SUN_AZIMUTH')), 
    ee.Number(image.get('SUN_ELEVATION')))
  hillShade = hillShade.rename(['hillShade'])
  return hillShade


def CalcHillShadows(image, geo):
  MergedDEM = ee.Image("users/eeProject/MERIT").clip(geo.buffer(3000))
  hillShadow = ee.Terrain.hillShadow(MergedDEM, 
    ee.Number(image.get('SUN_AZIMUTH')),
    ee.Number(90).subtract(image.get('SUN_ELEVATION')), 
    30)
  hillShadow = hillShadow.rename(['hillShadow'])
  return hillShadow


## Remove geometries
def removeGeo(i):
  return i.setGeometry(None)


## Set up the reflectance pull
def RefPull457(image):
  # process image with the radsat mask
  r = addRadMask(image).select('radsat')
  # process image with cfmask
  f = cfMask(image).select('cfmask')
  # process image with st SR cloud mask
  s = srCloudMask(image).select('sr_cloud')
  # where the f mask is > 2 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #apply dswe function
  d = DSWE(image).select('dswe')
  dswe1 = d.eq(1).rename('dswe1').updateMask(f.eq(0)).updateMask(r.eq(1)).updateMask(s.eq(0)).selfMask()
  # band where dswe is 3 and apply all masks
  dswe3 = d.eq(3).rename('dswe3').updateMask(f.eq(0)).updateMask(r.eq(1)).updateMask(s.eq(0)).selfMask()
  #calculate hillshade
  h = CalcHillShades(image, tile.geometry()).select('hillShade')
  #calculate hillshadow
  hs = CalcHillShadows(image, tile.geometry()).select('hillShadow')
  
  pixOut = (# make some dummy bands for the reducer
            image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa'])
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa', 'ST_CDIST'],
            ['min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa', 'min_cloud_dist']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
            ['Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
            ['Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa']))
            .addBands(image.select(['Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa','ST_CDIST'],
            ['mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp', 'mean_temp_qa', 'mean_cloud_dist']))
            .addBands(image.select(['SurfaceTemp']))
            .updateMask(d.eq(1)) # only high confidence water
            .updateMask(r.eq(1)) #1 == no saturated pixels
            .updateMask(f.eq(0)) #no snow or clouds
            .updateMask(s.eq(0)) # no SR processing artefacts
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(clouds) 
            .addBands(hs)) 
  combinedReducer = (ee.Reducer.median().unweighted().forEachBand(pixOut.select(['med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa']))
    .combine(ee.Reducer.min().unweighted().forEachBand(pixOut.select(['min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa', 'min_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.max().unweighted().forEachBand(pixOut.select(['max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa'])), sharedInputs = False)
    .combine(ee.Reducer.percentile([25]).unweighted().forEachBand(pixOut.select(['Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.percentile([75]).unweighted().forEachBand(pixOut.select(['Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp'])), sharedInputs = False)
    .combine(ee.Reducer.stdDev().unweighted().forEachBand(pixOut.select(['sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa'])), sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted().forEachBand(pixOut.select(['mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp', 'mean_temp_qa', 'mean_cloud_dist'])), sharedInputs = False)
    .combine(ee.Reducer.kurtosis().unweighted().forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
    .combine(ee.Reducer.count().unweighted().forEachBand(pixOut.select(['dswe1', 'dswe3'])), outputPrefix = 'pCount_', sharedInputs = False)
    #.combine(ee.Reducer.sum().unweighted().forEachBand(pixOut.select(['dswe1', 'dswe3'])), outputPrefix = 'pCount_', sharedInputs = False)
    .combine(ee.Reducer.mean().unweighted().forEachBand(pixOut.select(['clouds', 'hillShadow'])), outputPrefix = 'prop_', sharedInputs = False))
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(locs, combinedReducer, 30))
  out = lsout.map(removeGeo)
  return out


def RefPull89(image):
  # process image with the radsat mask
  r = addRadMask(image).select('radsat')
  # process image with cfmask
  f = cfMask(image).select('cfmask')
  # process image with st SR cloud mask
  a = srAerosol(image).select('medHighAero')
  # where the f mask is > 2 (clouds and cloud shadow), call that 1 (otherwise 0) and rename as clouds.
  clouds = f.gte(1).rename('clouds')
  #apply dswe function
  d = DSWE(image).select('dswe')
  dswe1 = d.eq(1).rename('dswe1').updateMask(f.eq(0)).updateMask(r.eq(1)).selfMask()
  # band where dswe is 3 and apply all masks
  dswe3 = d.eq(3).rename('dswe3').updateMask(f.eq(0)).updateMask(r.eq(1)).selfMask()
  #calculate hillshade
  h = CalcHillShades(image, tile.geometry()).select('hillShade')
  #calculate hillshadow
  hs = CalcHillShadows(image, tile.geometry()).select('hillShadow')
  pixOut = (image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['med_Aerosol','med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa'])
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa', 'ST_CDIST'],
            ['min_Aerosol','min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa', 'min_cloud_dist']))
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['max_Aerosol', 'max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa']))
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
            ['Q1_Aerosol', 'Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp']))
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp'],
            ['Q3_Aerosol','Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp']))
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa'],
            ['sd_Aerosol','sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa']))
            .addBands(image.select(['Aerosol','Blue', 'Green', 'Red', 'Nir', 'Swir1', 'Swir2', 'SurfaceTemp', 'temp_qa', 'ST_CDIST'],
            ['mean_Aerosol','mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp', 'mean_temp_qa', 'mean_cloud_dist']))
            .addBands(image.select(['SurfaceTemp']))
            .updateMask(d.eq(1)) # only high confidence water
            .updateMask(r.eq(1)) #1 == no saturated pixels
            .updateMask(f.eq(0)) #no snow or clouds
            .addBands(dswe1)
            .addBands(dswe3)
            .addBands(hs)
            .addBands(clouds) 
            .addBands(a)
            ) 
            
  combinedReducer = (ee.Reducer.median().unweighted().forEachBand(pixOut.select(['med_Aerosol','med_Blue', 'med_Green', 'med_Red', 'med_Nir', 'med_Swir1', 'med_Swir2', 'med_SurfaceTemp', 'med_temp_qa']))
  .combine(ee.Reducer.min().unweighted().forEachBand(pixOut.select(['min_Aerosol','min_Blue', 'min_Green', 'min_Red', 'min_Nir', 'min_Swir1', 'min_Swir2', 'min_SurfaceTemp', 'min_temp_qa', 'min_cloud_dist'])), sharedInputs = False)
  .combine(ee.Reducer.max().unweighted().forEachBand(pixOut.select(['max_Aerosol','max_Blue', 'max_Green', 'max_Red', 'max_Nir', 'max_Swir1', 'max_Swir2', 'max_SurfaceTemp', 'max_temp_qa'])), sharedInputs = False)
  .combine(ee.Reducer.percentile([25]).unweighted().forEachBand(pixOut.select(['Q1_Aerosol','Q1_Blue', 'Q1_Green', 'Q1_Red', 'Q1_Nir', 'Q1_Swir1', 'Q1_Swir2', 'Q1_SurfaceTemp'])), sharedInputs = False)
  .combine(ee.Reducer.percentile([75]).unweighted().forEachBand(pixOut.select(['Q3_Aerosol','Q3_Blue', 'Q3_Green', 'Q3_Red', 'Q3_Nir', 'Q3_Swir1', 'Q3_Swir2', 'Q3_SurfaceTemp'])), sharedInputs = False)
  .combine(ee.Reducer.stdDev().unweighted().forEachBand(pixOut.select(['sd_Aerosol','sd_Blue', 'sd_Green', 'sd_Red', 'sd_Nir', 'sd_Swir1', 'sd_Swir2', 'sd_SurfaceTemp', 'sd_temp_qa'])), sharedInputs = False)
  .combine(ee.Reducer.mean().unweighted().forEachBand(pixOut.select(['mean_Aerosol','mean_Blue', 'mean_Green', 'mean_Red', 'mean_Nir', 'mean_Swir1', 'mean_Swir2', 'mean_SurfaceTemp', 'mean_temp_qa', 'mean_cloud_dist'])), sharedInputs = False)
  .combine(ee.Reducer.kurtosis().unweighted().forEachBand(pixOut.select(['SurfaceTemp'])), outputPrefix = 'kurt_', sharedInputs = False)
  .combine(ee.Reducer.count().unweighted().forEachBand(pixOut.select(['dswe1', 'dswe3'])), outputPrefix = 'pCount_', sharedInputs = False)
  .combine(ee.Reducer.mean().unweighted().forEachBand(pixOut.select(['hillShadow', 'clouds', 'medHighAero'])), outputPrefix = 'prop_', sharedInputs = False))
  # Collect median reflectance and occurance values
  # Make a cloud score, and get the water pixel count
  lsout = (pixOut.reduceRegions(locs, combinedReducer, 30))
  out = lsout.map(removeGeo)
  return out


##Function for limiting the max number of tasks sent to
#earth engine at one time to avoid time out errors
def maximum_no_of_tasks(MaxNActive, waitingPeriod):
  ##maintain a maximum number of active tasks
  ## initialize submitting jobs
  ts = list(ee.batch.Task.list())
  NActive = 0
  for task in ts:
     if ('RUNNING' in str(task) or 'READY' in str(task)):
         NActive += 1
  ## wait if the number of current active tasks reach the maximum number
  ## defined in MaxNActive
  while (NActive >= MaxNActive):
    time.sleep(waitingPeriod) # if reach or over maximum no. of active tasks, wait for 2min and check again
    ts = list(ee.batch.Task.list())
    NActive = 0
    for task in ts:
      if ('RUNNING' in str(task) or 'READY' in str(task)):
        NActive += 1
  return()


  
  
  
