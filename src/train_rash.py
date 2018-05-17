#!/usr/bin/env python
import argparse
import os
from os import listdir
import pickle
import numpy as np
from sklearn.svm import NuSVC
from sklearn.model_selection import RepeatedKFold

# scale angular velocity to have better loss calculation

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: train_rash <dataset_path>"
    parser = argparse.ArgumentParser(description='train for rashness ')
    parser.add_argument('--scale_factor', dest='scale', type=int, default=1, nargs='?',
            help='how much to scale wu')
    parser.add_argument('--method', dest='method', type=int, default=0, nargs='?',
        help='simple SVM = 0, use cross-validation kfold = 1, NN =2')
    (opts, args) = parser.parse_known_args()
    if (len(args) < 1):
        print(usage)
        exit(-1)
    dataset_path = args[0]
    scale = opts.scale
    dirs = [f for f in listdir(dataset_path) if isdir(join(dataset_path, f))]
    X = []
    for j, dir in enumerate(dirs):
        path = join(join(dataset_path,dir),"rash")
        if isdir(path):
            files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
            for i, file in enumerate(files):
                with open(join(path,file),'r') as fileobject:
                    b = pickle.load(fileobject)
                    for i, val in enumerate(b):
                        for j,val1 in enumerate(val):
                            if j%2:
                              val[j] = val[j]*scale
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
                    for i, val in enumerate(b):
                        for j,val1 in enumerate(val):
                            if j%2:
                              val[j] = val[j]*scale
                    X.extend(b)

    Y = [0] * len(X)
    Y[:rash_len] = [1] * rash_len

    print( "Starting Training: rash_len {0} , normal_len {1}" .format(rash_len,(len(X)-rash_len)))
    
    #using cross validation as number of data points are less
    rkf = RepeatedKFold(n_splits=10, n_repeats=5, random_state=123123)

    ## first train
    if opts.method == 0:
        clf = NuSVC(probability=True)
        clf.fit(X, Y)
        for train, test in rkf.split(X):
            X_test = [X[idx] for idx in list(test)]
            Y_test = [Y[idx] for idx in list(test)]

            score = clf.score(X_test, Y_test)
            print(score)
    elif opts.method ==1:
        # Cross Validation code
        clf = NuSVC(probability=True)
        for train, test in rkf.split(X):
            X_train = [X[idx] for idx in list(train)]
            Y_train = [Y[idx] for idx in list(train)]
            X_test = [X[idx] for idx in list(test)]
            Y_test = [Y[idx] for idx in list(test)]

            score = clf.fit(X_train, Y_train).score(X_test, Y_test)
            print(score)

    elif opts.method ==2:
        from sklearn.neural_network import MLPClassifier
        clf = MLPClassifier(solver='lbfgs', alpha=1e-4, hidden_layer_sizes=(200, 100), random_state=1)
        clf.fit(X, Y)
        for train, test in rkf.split(X):
            X_test = [X[idx] for idx in list(test)]
            Y_test = [Y[idx] for idx in list(test)]

            score = clf.score(X_test, Y_test)
            print(score)
    with open(join(dataset_path,"model.dump"), 'w') as fileobject:
        pickle.dump(clf,fileobject)
        
    print("### SVM Model dumped ###")
