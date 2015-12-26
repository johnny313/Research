#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from osgeo import gdal, gdalnumeric, ogr, osr
import numpy as np
import datetime
import json

def process_metadata_line(line):
    return line.strip('   \n')

# format L8 metadata file into a dict with string keywords
def build_metadata_table(metadata_fn):
  with open(metadata_fn) as f:
      m_data = f.readlines()[:-1]
  table = {x.split(' = ')[0] : x.split(' = ')[1] for x in [process_metadata_line(m) for m in m_data]}
  return table

# extract date acquired from LANDSAT metadata
def get_DOY(metadata_dict):
  return datetime.datetime.strptime(metadata_dict['DATE_ACQUIRED'], '%Y-%m-%d').date().timetuple().tm_yday

# given L8 files for B2, B4, B5, metadata, and a polyhon within
# the bounds of the raster, returns the mean NDVI value in the
# polygon accounting for B2 cloud coverage

def mk_16(x):
    if len(x) == 16:
        return x
    else:
        return mk_16('0'+ x)    

def QA_logic(x):
    biny = np.binary_repr(x)
    if len(biny) < 16:
        biny = mk_16(biny)
    cloud = int(biny[0:2],2)
    cirrus = int(biny[2:4],2)
    return cloud + cirrus


def WDRVI(red,nir,alpha=0.2):
    return (alpha*nir - red)/(alpha*nir + red)
     # see http://www.gap.uidaho.edu/Bulletins/12/The%20Wide%20Dynamic%20Range%20Vegetation%20Index.htm

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

def get_quality_filter(landsat_base):
    #build fn for quality band
    qa_fn = landsat_base + '_BQA.TIF'
    #get quality filter
    dnQA = gdal.Open(qa_fn)
    dnQA_array = np.array(dnQA.GetRasterBand(1).ReadAsArray())
    #vectorize QA_logic for use on the array
    QA_filter = np.vectorize(QA_logic)
    return QA_filter(dnQA_array)

def cloud_filter(rf_array,landsat_base,qa_threshold=2):
    qa_cloud_filter = get_quality_filter(landsat_base)
    c_x, c_y= np.where(qa_cloud_filter>qa_threshold)
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

def get_band_raster(landsat_base, bn, _filter = True):
    #get band fn
    bnd_fn = landsat_base + '_B' + str(bn) + '.TIF'
    # read raster as ndarray
    dn_array = gdal.Open(bnd_fn)
    dn_array = np.array(dn_array.GetRasterBand(1).ReadAsArray()).astype(float)
    #set the pixels with no data (DN=0) to np.nan
    nd_x, nd_y = np.where(dn_array==0)
    dn_array[nd_x, nd_y] = np.nan
    #apply cloud filter from the Landsat QA band
    if _filter:
        dn_array = cloud_filter(dn_array, landsat_base)
    #convert the DN to reflectances, corrected for solar angle
    rf_array = convert_dn_to_reflectance(dn_array, landsat_base, bn)
    return rf_array

# TESTING
if __name__ == "__main__":
    from matplotlib import pyplot as plt
    landsat_base = '/Applications/bda/Bulk_Order_596039/L8_OLI_TIRS/LC80210302015127LGN00/LC80210302015127LGN00' 
    #red_img = get_band_raster(landsat_base, 4)
    NIR_img = get_band_raster(landsat_base, 5)
    plt.imshow(NIR_img)#WDRVI(red_img, NIR_img))
    plt.show(block=True)

