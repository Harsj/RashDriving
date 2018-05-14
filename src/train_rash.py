#!/usr/bin/env python
import argparse
import os
from os import listdir
import pickle
import numpy as np
from sklearn.svm import NuSVC
from sklearn.model_selection import RepeatedKFold

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: train_rash <dataset_path>"
    parser = argparse.ArgumentParser(description='train for rashness ')
    (opts, args) = parser.parse_known_args()
    if (len(args) < 1):
        print(usage)
        exit(-1)
    dataset_path = args[0]

    dirs = [f for f in listdir(dataset_path) if isdir(join(dataset_path, f))]
    X = []
    for j, dir in enumerate(dirs):
        path = join(join(dataset_path,dir),"rash")
        if isdir(path):
            files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
            for i, file in enumerate(files):
                with open(join(path,file),'r') as fileobject:
                    b = pickle.load(fileobject)
                    X.extend(b)
    rash_len = len(X)

    dirs = [f for f in listdir(dataset_path) if isdir(join(dataset_path, f))]
    for j, dir in enumerate(dirs):
        path = join(join(dataset_path,dir),"normal")
        if isdir(path):
            files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
            for i, file in enumerate(files):
                with open(join(path,file),'r') as fileobject:
                    b = pickle.load(fileobject)
                    X.extend(b)

    Y = [0] * len(X)
    Y[:rash_len] = [1] * rash_len

    print( "Starting Training: rash_len {0} , normal_len {1}" .format(rash_len,(len(X)-rash_len)))
    
    clf = NuSVC(probability=True)

    #using cross validation as number of data points are less
    #clf.fit(X, Y)
    rkf = RepeatedKFold(n_splits=10, n_repeats=5, random_state=123123)
    for train, test in rkf.split(X):
        X_train = [X[idx] for idx in list(train)]
        Y_train = [Y[idx] for idx in list(train)]
        X_test = [X[idx] for idx in list(test)]
        Y_test = [Y[idx] for idx in list(test)]
        
        score = clf.fit(X_train, Y_train).score(X_test, Y_test)
        print(score)
    
    with open(join(dataset_path,"model.dump"), 'w') as fileobject:
        pickle.dump(clf,fileobject)
        
    print("### SVM Model dumped ###")
