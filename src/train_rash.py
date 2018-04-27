#!/usr/bin/env python
import argparse
import os
import pickle
import numpy as np
from sklearn.svm import NuSVC

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: train_rash <dataset_path>"
    parser = argparse.ArgumentParser(description='train for rashness ')
    (opts, args) = parser.parse_known_args()
    
    dataset_path = arg[0]
    path = join(dataset_path,"rash")
    files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
    X = []
    for i, file in enumerate(files):
        with open(join(path,file),'r') as fileobject:
            b = pickle.load(fileObject)
            X.extend(b)
    rash_len = len(X)
    
    path = join(dataset_path,"normal")
    files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
    for i, file in enumerate(files):
        with open(join(path,file),'r') as fileobject:
            b = pickle.load(fileObject)
            X.extend(b)
    
    Y[len(X)] = 0
    Y[0:rash_len] = 1
    Y[rash_len:-1] = 2
    
    print( "Starting Training: rash_len {0} , normal_len {1}" .format(rash_len,(len(X)-rash_len))
    
    clf = NuSVC()
    clf.fit(X, Y)
    
    with open('\\'.join([dataset_path,"model.dump"]), 'w') as fileobject:
        pickle.dump(clf,fileobject)
        
    print("### SVM Model dumped ###")
    
    

