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
    usage = "Usage: test_rash <model_path> <val_dataset_path>"
    parser = argparse.ArgumentParser(description='test if driving is rash or not')
    (opts, args) = parser.parse_known_args()
    
    model_path = arg[0]
    val_dataset_path = arg[1]
    
    path = join(val_dataset_path,"rash")
    files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
    X = []
    for i, file in enumerate(files):
        with open(join(path,file),'r') as fileobject:
            b = pickle.load(fileObject)
            X.extend(b)
    rash_len = len(X)
    
    path = join(val_dataset_path,"normal")
    files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.dat')]
    for i, file in enumerate(files):
        with open(join(path,file),'r') as fileobject:
            b = pickle.load(fileObject)
            X.extend(b)

    print( "Starting Testing: rash_len {0} , normal_len {1}" .format(rash_len,(len(X)-rash_len))
    
    with open('\\'.join([model_path,"model.dump"]), 'w') as fileobject:
        clf = pickle.load(fileobject)

    Y = clf.predict(X)
    
    print("### SVM Model dumped ###")
    
    

