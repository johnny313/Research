#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from osgeo import gdal, gdalconst, osr, ogr
from matplotlib import pyplot as plt
import numpy as np
import datetime
import json


##########################################################
# Generic Raster Processing Functions
##########################################################

# linear stretch to min/max of the DN values in the raster  
def normalize(x, scale=255.):
    x = x.astype(float) 
    mx = np.nanmax(x)
    mn = np.nanmin(x)              
    x = (x-mn)*scale/(mx-mn)
    return np.asarray(x,dtype=np.uint8)
    
def stretch_histogram(x, percentile=95):
    new_max = np.nanpercentile(x, percentile)
    x[np.where(np.logical_and(x>new_max, ~(np.isnan(x))))] = new_max
    return normalize(x)

#  histogram equalization stretch of the normalized scaled DNs raster     
def hist_equalize_stretch(x):
    hist,bin_bound = np.histogram(x,256,(0,256))
    cdf = hist.cumsum()
    lut = 255*cdf/float(cdf[-1])                                
    return np.interp(x,bin_bound[:-1],lut)

def gamma_correction(x, gamma):
    invGamma = 1.0 / gamma
    lut = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return np.interp(x, np.arange(0, 256), lut)

def enhance_rast(dn_array, method = None, gamma_cor = None):
     if method=='stretch_histogram':
         rast = stretch_histogram(dn_array)
     elif method=='hist_equalize':
         rast = hist_equalize_stretch(dn_array)
     else:
         rast = dn_array
     #apply gamma correction?
     if gamma_cor:
         rast = gamma_correction(rast, gamma_cor)
     return rast

#####################################################################
# Functions for working with Landsat Data
#####################################################################

# format Landsat 8 metadata file into a dict with string keywords
def process_metadata_line(line):
    return line.strip('   \n')

def build_metadata_table(metadata_fn):
  with open(metadata_fn) as f:
      m_data = f.readlines()[:-1]
  table = {x.split(' = ')[0] : x.split(' = ')[1] for x in [process_metadata_line(m) for m in m_data]}
  return table

# extract date acquired from LANDSAT metadata
def get_DOY(metadata_dict):
  return datetime.datetime.strptime(metadata_dict['DATE_ACQUIRED'], '%Y-%m-%d').date().timetuple().tm_yday

#Function retrieves data from the landsat tiff file:
#    _filter applies the QA band to the band, setting cloud pixels to np.nan
#    extent = (top, bottom, left, right)

def get_raster_DN_array(landsat_base, bn, extent=(None,None,None,None), _filter=True):
    #get band fn
    bnd_fn = landsat_base + '_B' + str(bn) + '.TIF'
    # read raster as ndarray
    dn_array = gdal.Open(bnd_fn)
    dn_array = np.array(dn_array.GetRasterBand(1).ReadAsArray()).astype(float)
    if all(extent):
        dn_array = dn_array[extent[2]:extent[3], extent[0]:extent[1]]
    #set the pixels with no data (DN=0) to np.nan
    nd_x, nd_y = np.where(dn_array==0)
    dn_array[nd_x, nd_y] = np.nan
    #apply cloud filter from the Landsat QA band
    if _filter:
        dn_array = cloud_filter(dn_array, landsat_base)
    return dn_array


#get the parameters needed from metadata to transform the DN values to top of atmosphere reflectance
def get_reflectance_parameters(landsat_base, bn):
    #use base scene string to get fn for metadata 
    metadata_fn = landsat_base + '_MTL.TXT'
    #build lut for metadata and get keys for band of interest
    mdata = build_metadata_table(metadata_fn)
    # metadata keywords (2: BLUE, 4: RED, 5: NIR)
    mult_key = "REFLECTANCE_MULT_BAND_"+str(bn)
    add_key  = "REFLECTANCE_ADD_BAND_"+str(bn)
    #get parameters from the metadata
    sun_elevation = mdata['SUN_ELEVATION']
    mult = mdata[mult_key]
    add = mdata[add_key]
    return mult, add, sun_elevation

def get_quality_band(landsat_base):
    #build fn for quality band
    qa_fn = landsat_base + '_BQA.TIF'
    dnQA = gdal.Open(qa_fn)
    dnQA_array = np.array(dnQA.GetRasterBand(1).ReadAsArray())
    return dnQA_array 

#see http://landsat.usgs.gov/L8QualityAssessmentBand.php for more details
def cloud_filter(rf_array,landsat_base):
    qa_band = get_quality_band(landsat_base)
    c_x, c_y= np.where(qa_band > 24575)
    output_array = np.copy(rf_array).astype(float)
    output_array[c_x, c_y] = np.nan
    return output_array
    
def convert_dn_to_reflectance(dn_array, landsat_base, bn):
    #sun elevation scale factor
    mult, add, sun_elevation = get_reflectance_parameters(landsat_base, bn)
    sun_elevation_factor = np.sin(float(sun_elevation)*np.pi/180)
    # calculate TOA reflectance given digital number
    rf_array  = float(mult)*dn_array  + float(add)
    # scaled for sun elevation
    return rf_array/sun_elevation_factor

def transform_TOA(landsat_base, bn, cloud_filter = True):
    dn_array = get_raster_DN_array(landsat_base, bn, _filter=cloud_filter)
    #convert the DN to reflectances, corrected for solar angle
    rf_array = convert_dn_to_reflectance(dn_array, landsat_base, bn)
    return rf_array

#default returns RGB array
def get_multiband_array(landsat_base, bn=(4,3,2), BB = (None,None,None,None), enhance=None, gamma=None, mask = False ):
    rast_tup = (normalize(get_raster_DN_array(landsat_base, b, BB, mask)) for b in bn)
    if enhance:
        rast_tup = (enhance_rast(rast,enhance, gamma) for rast in rast_tup)
    return np.dstack(rast_tup).astype(np.uint8)

#calculate WDRVI
# see http://www.gap.uidaho.edu/Bulletins/12/The%20Wide%20Dynamic%20Range%20Vegetation%20Index.htm
def WDRVI(red,nir,alpha=0.2):
    return (alpha*nir - red)/(alpha*nir + red)



####################################################################
#Writing rasters to file
####################################################################
#returns the geotransform and the projection of the original raster
def get_geotrans_prj(fn):
    rast  = gdal.Open(fn)
    geo_trans = rast.GetGeoTransform()
    prj = rast.GetProjection()
    return {'geo_trns':geo_trans,'prj':prj}

def write_tiff(array, fn, spatial_ref_dict):
    pixel_dims = array.shape
    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(
                            fn,
                            pixel_dims[1],
                            pixel_dims[0],
                            1,
                            gdal.GDT_Float32)
    dataset.SetGeoTransform(spatial_ref_dict['geo_trns'])  
    dataset.SetProjection(spatial_ref_dict['prj'])
    dataset.GetRasterBand(1).WriteArray(array)
    dataset.FlushCache()  # Write to disk.
    dataset = None

#plot list of images
def show_images(images,col ='RdYlGn', mx=1,mn=0, titles=None):
    fig = plt.figure()
    n_ims = len(images)
    if titles is None: 
        titles = ['(%d)' % i for i in range(1,n_ims + 1)]
    n = 1
    for image,title in zip(images,titles): 
        a = fig.add_subplot(1,n_ims,n) # Make subplot
        if  type(col)==dict:
            plt.imshow(image,vmin=mn, vmax=mx,cmap=col['cmap'], norm=col['norm'])
        else:
            plt.set_cmap(col)
        plt.imshow(image,vmin=mn, vmax=mx)
        a.set_title(title)
        n += 1
    fig.set_size_inches(np.array(fig.get_size_inches()) * n_ims)
    plt.show()

