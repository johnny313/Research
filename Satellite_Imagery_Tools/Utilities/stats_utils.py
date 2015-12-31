#!/usr/local/bin/python
# -*- coding: utf-8 -*-

import numpy as np
from matplotlib import pyplot as plt
from scipy.stats.kde import gaussian_kde
from sklearn import cluster as Kclust, metrics
from sklearn import preprocessing

#get prob density plot of arry
def plt_density(data,title=None,n=None,color='blue'):
    #remove nans
    data = data[~np.isnan(data)]
    if n:
        #reduce data size
        data = np.random.choice(data,n,replace=False)
    # this creates the kernel, given an array it will estimate the probability over the values
    kde = gaussian_kde( data )
    # these are the values over wich your kernel will be evaluated
    dist_space = np.linspace( min(data), max(data), 100 )
    # plot the results
    plt.title(title)
    plt.plot( dist_space, kde(dist_space), color=color)

def scale_image(array):
    ar = np.copy(array)
    x_coord,y_coord = np.where(~np.isnan(ar))
    ar[x_coord,y_coord] = preprocessing.scale(ar[x_coord,y_coord]) 
    return ar

def frequ_ct(x, cts = False): 
    x = x.flatten().astype('uint8')
    y = np.bincount(x)
    ii = np.nonzero(y)[0]
    if not cts:
        return [ct[0] for ct in sorted(zip(ii,y[ii]), key=lambda x:x[1])]
    elif cts:
        return {v:ct for v,ct in zip(ii,y[ii])}

def CH_stat(X):
    #source: http://web.stanford.edu/~hastie/Papers/gap.pdf
    tot_ss = kmeans_model = Kclust.KMeans(n_clusters=1, random_state=1332).fit(X).inertia_
    ks = np.array(range(3,10))
    Wks = np.zeros(len(ks))
    for indk, k in enumerate(ks):
        kmeans_model = Kclust.KMeans(n_clusters=k, random_state=1332).fit(X)
        Wks[indk] = kmeans_model.inertia_
    btwn_ss = (tot_ss-Wks)
    ch = (btwn_ss/(ks-1)) / (Wks/(X.shape[0] - ks))
    return ks[list(ch).index(max(ch))] 

def k_means(img_list, k=3):
    out_img = np.copy(img_list[0])
    full_x, full_y = np.where(~np.isnan(img_list[0]))
    img_array = np.array([x[full_x, full_y] for x in img_list]).T
    #If k not passed by user, estimate k using the CH stat
    if k=='CH' or k==None:
        k=CH_stat(X)
        print k
    #build model
    k_model = Kclust.KMeans(n_clusters=k, random_state=1332).fit(img_array)
    #output field array w/cluster assignments
    lables = k_model.labels_
    out_img[full_x, full_y] = lables
    return k_model.cluster_centers_,  out_img

def random_ints(i, n):
    return np.array(np.random.choice(range(i),n))

def two_step_sample(array, total_n, step=(100, 100)):
    sample = []
    w,d,_ = array.shape
    n_cells = w/step[0] * d/step[1]
    cell_samp_size = total_n / n_cells
    for i in range(step[0],w,step[0]):
        for j in range(step[0],d,step[1]):
            sub_pop = array[(i-step[0]) : i , (j-step[0]) : j , :]
            x_coords = random_ints(step[0], cell_samp_size)
            y_coords = random_ints(step[1], cell_samp_size)
            samp = sub_pop[x_coords, y_coords]
            samp = samp[np.where(~np.isnan(samp[:,1]))]
            sample = sample + samp.tolist()
    return sample
