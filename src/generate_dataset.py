#!/usr/bin/env python
import argparse
import os
import pickle

# usage example
# python generate_dataset ..\own\2018_04_26-14_00_27\output\motion.txt ..\motion_data\ --sf=5 --ef=10 --skipfps=9 --skip=2 --is-rash

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: generate_dataset <oxtspath> <outputdir>"
    parser = argparse.ArgumentParser(description='create dataset for rash driving')
    parser.add_argument('--sf', dest='startframe', type=int, default=0, nargs='?', 
            help='frame num from where rashness started')
    parser.add_argument('--ef', dest='endframe', type=int, default=1, nargs='?', 
            help='frame num from where rashness ends')
    parser.add_argument('--data-size', dest='size', type=int, default=20, nargs='?', 
            help='size of data point')
    parser.add_argument('--skip', dest='skip', type=int, default=1, nargs='?', 
            help='Number of frames skipped to next generate dataset')
    parser.add_argument('--skipfps', dest='skipfps', type=int, default=1, nargs='?', 
            help='set 9 for pilotguru, 1 for VMD')
    parser.add_argument('--is-rash', dest='isrash', action='store_true',default=True, 
            help='set is rash or not')

    (opts, args) = parser.parse_known_args()
    if (len(args) < 2):
        print(usage)
        exit(-1)

    vi = args[0]    
    outdir = args[1]

    ef = opts.endframe/opts.skipfps
    sf = opts.startframe/opts.skipfps
    if(ef < sf):
        print( "wrong start OR end")
        exit(1)

    if(ef-sf > opts.size):
        print( "patch size should be smaller than data_size.. May be divide it")
        exit(1)
    
    if ef - opts.size >= 0:
        pos = (ef + 1 - opts.size)*opts.skipfps
    else:
        pos = 0
    
    data = []
    data_num = 0
    with open(vi, 'r') as openfileobject:
        line_num = 0
        for line in openfileobject:
            if line_num >= pos:
                if line_num <= (sf - 1 + opts.size)*opts.skipfps :
                    if line_num % opts.skipfps == 0:
                        val = line.strip().split(' ')
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
    outdir = join(args[1],vi.split('\\')[-3])
    name = str(opts.startframe)+'-' + str(opts.endframe)+'-'+str(opts.size) +'-'+str(num_dataset)+'.dat'

    print('[generate_dataset] in file {0}. Total number of sets: {1}'.format(name, num_dataset))   
 
    #create out folder using isrash if doesn't exsist
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    if opts.isrash == True:
        path = join(outdir, "rash")
    else:
        path = join(outdir, "normal")
    if not os.path.exists(path):
        os.mkdir(path)
    
    with open(join(path,name), 'w') as openfileobject:
        pickle.dump(dataset,openfileobject)
        
        
    print("### dump done###")
    
    

