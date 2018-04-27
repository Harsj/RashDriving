#!/usr/bin/env python
import argparse
import os
import pickle

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: generate_dataset <oxtspath> <outputdir>"
    parser = argparse.ArgumentParser(description='create dataset for rash driving')
    parser.add_argument('--start-frame', dest='startframe', type=int, default=0, nargs='?', 
            help='frame num from where rashness started')
    parser.add_argument('--end-frame', dest='endframe', type=int, default=1, nargs='?', 
            help='frame num from where rashness ends')
    parser.add_argument('--data-size', dest='size', type=int, default=20, nargs='?', 
            help='size of data point')
    parser.add_argument('--skip', dest='skip', type=int, default=2, nargs='?', 
            help='Number of frames skipped to next generate dataset')
    parser.add_argument('--is-rash', dest='isrash', action='store_true',default=True, 
            help='set is rash or not')

    (opts, args) = parser.parse_known_args()
    if (len(args) < 2):
        print(usage)
        exit(-1)

    vi = args[0]    
    outdir = args[1]

    if(opts.endframe < opts.startframe):
        opts.endframe = opts.startframe

    if(opts.endframe-opts.startframe > opts.size):
        print( "patch size should be smaller than data_size.. May be divide it")
        exit(1)
    
    if opts.endframe - opts.size >= 0:
        pos = opts.endframe - opts.size
    else:
        pos = 0
    
    data = []
    data_num = 0
    with open(vi, 'r') as openfileobject:
        line_num = 0
        for line in openfileobject:
            if line_num >= pos:
                if line_num <= opts.startframe + opts.size :
                    val = line.strip().split(',')
                    data.append([float(val[0]),float(val[1])])
                    data_num += 1
                else:
                    break
            line_num += 1
    
    #number of data points to be collected    
    num = (data_num - opts.size)/opts.skip + 1   
    num_dataset = num
    dataset = []
    start_pos = 0
    while num:
        data_point = []
        for i in range(opts.size):
            data_point.append(data[start_pos+i][0])
            data_point.append(data[start_pos+i][1])
        
        dataset.append(data_point)
        num -= 1
        start_pos += opts.skip

    #create file named vi + startframe + endframe + size + num
    #dump dataset into it
    name = vi.split('\\')[-2]+ '-' + str(opts.startframe)+'-' + str(opts.endframe)+'-'+str(opts.size) +'-'+str(num_dataset)+'.dat'

    print('[generate_dataset] in file {0}. Total number of sets: {1}'.format(name, num_dataset))   
 
    #create out folder using isrash if doesn't exsist
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    if opts.isrash == True:
        path = outdir + "\\rash"
    else:
        path = outdir + "\\normal"
    if not os.path.exists(path):
        os.mkdir(path)
    
    with open('\\'.join([path,name]), 'w') as openfileobject:
        pickle.dump(dataset,openfileobject)
        
        
    print("### dump done###")
    
    

