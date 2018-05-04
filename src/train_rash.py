#!/usr/bin/env python
import argparse
import os
from os import listdir
import pickle
import numpy as np
from sklearn.svm import NuSVC

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: train_rash <dataset_path>"
    parser = argparse.ArgumentParser(description='train for rashness ')
    (opts, args) = parser.parse_known_args()
    
    dataset_path = args[0]

    dirs = [f for f in listdir(dataset_path) if isdir(join(dataset_path, f))]
    X = []
    for j, dir in enumerate(dirs):
        path = join(join(dataset_path,dir),"rash")
        files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
        for i, file in enumerate(files):
            with open(join(path,file),'r') as fileobject:
                b = pickle.load(fileobject)
                X.extend(b)
    rash_len = len(X)

    dirs = [f for f in listdir(dataset_path) if isdir(join(dataset_path, f))]
    for j, dir in enumerate(dirs):
        path = join(join(dataset_path,dir),"normal")
        files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
        for i, file in enumerate(files):
            with open(join(path,file),'r') as fileobject:
                b = pickle.load(fileobject)
                X.extend(b)

    Y = [0] * len(X)
    Y[:rash_len] = [1] * rash_len

    print( "Starting Training: rash_len {0} , normal_len {1}" .format(rash_len,(len(X)-rash_len)))
    
    clf = NuSVC()
    clf.fit(X, Y)
    
    with open(join(dataset_path,"model.dump"), 'w') as fileobject:
        pickle.dump(clf,fileobject)
        
    print("### SVM Model dumped ###")
