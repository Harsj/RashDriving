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
#python test_video.py ..\motion_data_gt\model.dump ..\motion_data_gt\2018_05_06-16_44_29.png --motion_gt="..\rash\2018_05_06-16_44_29\output\motion.txt" --motion_pred="..\motion_pred\2018_05_06-16_44_29\motion.txt"

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

    (opts, args) = parser.parse_known_args()
    if (len(args) < 2):
        print(usage)
        exit(-1)
    
    model = args[0]
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
                    data_gt.append([float(val[0]),float(val[1])])
                    data_num_gt += 1
                line_num += 1
        
        out_gt = check_rash(args[0], data_gt, data_num_gt, skip)
        out = out_gt*5 ## Will be good to display
        out = np.repeat(out,skip)
        
        plt.plot(np.array(data_gt)[:,0], 'r', label='vf_gt')
        plt.plot(np.array(data_gt)[:,1] * 5, 'g',  label='wu_gt')
        plt.plot(out, 'b', label='rash_gt')
        plt.axis([1, data_num_gt, -5, 20])
            
                
    if have_pred:
        data_num_pred = 0
        data_pred = []
        with open(opts.motion_pred, 'r') as openfileobject:
            for line in openfileobject:
                val = line.strip().split(' ')
                if val[0] == 'nan' or val[1] == 'nan':
                    print("*****Pred has nan ****** ERROR ERROR")
                    break;
                data_pred.append([float(val[0]),float(val[1])])
                data_num_pred += 1
                
        out_pred = check_rash(args[0], data_pred, data_num_pred, skip)
        out = out_pred*5 ## Will be good to display
        out = np.repeat(out,skip)
        
        plt.plot(np.array(data_pred)[:,0], 'r', marker = 'o', ls='--', label='vf_pred')
        plt.plot(np.array(data_pred)[:,1] * 5, 'g', marker = 'o', ls='--', label='wu_pred')
        plt.plot(out, 'b', marker = 'o', ls='--', label='rash_pred')
        if data_num_gt < data_num_pred :
            plt.axis([1, data_num_pred, -5, 20])
 
    plt.legend(loc=2) 
    plt.savefig(args[1])
    plt.show()        
    
    print(" Testing Completed ::  Check Plot")
    
