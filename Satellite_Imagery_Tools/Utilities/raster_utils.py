#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from osgeo import gdal, gdalconst, osr, ogr
from matplotlib import pyplot as plt
import numpy as np

# linear stretch to min/max of the DN values in the raster  
def linear_stretch(x):
    x = x.astype(float) 
    mx = np.nanmax(x)
    mn = np.nanmin(x)              
    x = (x-mn)*255.0/(mx-mn)
    return np.asarray(x,dtype=np.uint8)
    
#  histogram equalization stretch of the min/max scaled DNs raster     
def hist_equalize_stretch(x):
    hist,bin_bound = np.histogram(x,256,(0,256))
    cdf = hist.cumsum()
    lut = 255*cdf/float(cdf[-1])                                
    return np.interp(x,bin_bound[:-1],lut)

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

    

