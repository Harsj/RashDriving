#!/usr/bin/env python
import argparse
import os
import pickle
import numpy as np
import scipy
from sklearn.svm import NuSVC

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: test_rash <model_path> <test_dataset_path>"
    parser = argparse.ArgumentParser(description='test if driving is rash or not')
    (opts, args) = parser.parse_known_args()
    
    model_path = arg[0]
    test_dataset_path = arg[1]
    
    path = test_dataset_path
    files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
    X = []
    for i, file in enumerate(files):
        with open(join(path,file),'r') as fileobject:
            b = pickle.load(fileObject)
            X.extend(b)
    
    print( "Starting Testing: data_len {0}" .format(len(X))
    
    with open('\\'.join([model_path,"model.dump"]), 'w') as fileobject:
        clf = pickle.load(fileobject)

    Y = clf.predict(X)
    
    print("### SVM Model dumped ###")
    
    

