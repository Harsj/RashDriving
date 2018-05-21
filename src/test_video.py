#!/usr/bin/env python
import argparse
import os
from os import listdir
import pickle
import numpy as np
import scipy
from sklearn.svm import NuSVC
from matplotlib import pyplot as plt

## Demo Command
#python test_video.py ..\motion_data_gt\model.dump ..\motion_data_gt\2018_05_06-16_44_29.png --motion_gt="..\normal\2018_05_06-16_44_29\output\motion.txt" --motion_pred="..\motion_pred\2018_05_06-16_44_29\motion.txt"

# scale angular velocity to have better loss calculation

def savitzky_golay(y, window_size, order, deriv=0, rate=1):

    import numpy as np
    from math import factorial

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError, msg:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m[::-1], y, mode='valid')

def check_rash(model, data, data_num, skip) :
    dataset = []
    start_pos = 0
    while data_num - start_pos >= 20:
        data_point = []
        for i in range(data_size):
            data_point.append(data[start_pos+i][0])
            data_point.append(data[start_pos+i][1])
        
        dataset.append(data_point)
        start_pos += skip
    
    with open(model, 'r') as fileobject:
        clf = pickle.load(fileobject)
        probY = clf.predict_proba(dataset)
        
    return np.array(probY)[:,1]

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: test_video <_rashness_model> <output file>"
    parser = argparse.ArgumentParser(description='test if driving is rash or not')
    parser.add_argument('--motion_gt', dest='motion_gt', action='store', default='',
            help='Specify path for video motion.txt')
    parser.add_argument('--motion_pred', dest='motion_pred', action='store', default='',
            help='Specify path for video motion.txt')
    parser.add_argument('--scale_factor', dest='scale', type=int, default=1, nargs='?',
            help='how much to scale wu')

    (opts, args) = parser.parse_known_args()
    if (len(args) < 2):
        print(usage)
        exit(-1)
    
    model = args[0]
    scale = opts.scale
    if not isfile(model):
        print("Model path not correct")
        exit(-1)
    
    if opts.motion_gt == '':
        have_gt = False
    else : 
        if isfile(opts.motion_gt):
            have_gt = True
        else :
            print("motion_gt path not correct")
            exit(-1)
            
    if opts.motion_pred == '':
        have_pred = False
    else : 
        if isfile(opts.motion_pred):
            have_pred = True
        else :
            print("motion_pred path not correct")
            exit(-1)
            
    if not isdir(os.path.dirname(args[1])):
        print("output folder doesn't exsist")
        exit(-1)
    data_size = 20
    skip = 5 # so 4 rash value in 1 datapoint size of 20 samples (20 samples == 6 secs)
    plt.figure(dpi=140)
    plt.grid(True)
    plt.xlabel("frames")
    
    data_num_gt = 0
    if have_gt:
        data_gt = []
        with open(opts.motion_gt, 'r') as openfileobject:
            line_num = 0
            for line in openfileobject:
                if line_num % 9 == 0:
                    val = line.strip().split(' ')
                    if val[0] == 'nan' or val[1] == 'nan':
                        break;
                    data_gt.append([float(val[0]),float(val[1])*scale])
                    data_num_gt += 1
                line_num += 1
        
        out_gt = check_rash(args[0], data_gt, data_num_gt, skip)
        out = out_gt*5 ## Will be good to display
        out = np.repeat(out,skip)
        
        plt.plot(np.array(data_gt)[:,0], 'r', label='vf_gt')
        plt.plot(np.array(data_gt)[:,1], 'g',  label='wu_gt')
        plt.plot(out, 'b', label='rash_gt')
        plt.axis([1, data_num_gt, -5, 20])
            
                
    if have_pred:
        data_num_pred = 0
        data_pred = []
        arr_vf = []
        arr_wu = []
        with open(opts.motion_pred, 'r') as openfileobject:
            for line in openfileobject:
                val = line.strip().split(' ')
                if val[0] == 'nan' or val[1] == 'nan':
                    print("*****Pred has nan ****** ERROR ERROR")
                    break;
                #data_pred.append([float(val[0]),np.deg2rad(float(val[1]))*scale])
                arr_vf.append(float(val[0]))
                arr_wu.append(np.deg2rad(float(val[1]))*scale)
                data_num_pred += 1

                
        arr_vf_s = list(savitzky_golay(np.array(arr_vf),25,3))
        arr_wu_s = list(savitzky_golay(np.array(arr_wu),25,3))
        #arr_vf_s = arr_vf
        #arr_wu_s = arr_wu
        data_pred = zip(arr_vf_s, arr_wu_s)

        out_pred = check_rash(args[0], data_pred, data_num_pred, skip)
        out = out_pred*5 ## Will be good to display
        out = np.repeat(out,skip)
        
        plt.plot(np.array(data_pred)[:,0], 'r', ls='--', label='vf_pred')
        plt.plot(np.array(data_pred)[:,1], 'm', ls='-', label='wu_pred')
        plt.plot(out, 'b', ls='--', label='rash_pred')
        if data_num_gt < data_num_pred :
            plt.axis([1, data_num_pred, -5, 20])
 
    plt.legend(loc=2) 
    plt.savefig(args[1])
    #plt.show()
    plt.pause(5)
    
    print(" Testing Completed ::  Check Plot")
    
