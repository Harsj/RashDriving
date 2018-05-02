#!/usr/bin/env python
import argparse
import numpy as np
import cv2

# Convert video to png

#if iscv3(): 
#    CAP_PROP_FRAME_COUNT = cv2.CAP_PROP_FRAME_COUNT 
#    CAP_PROP_FPS = cv2.CAP_PROP_FPS
#    CAP_PROP_POS_FRAMES = cv2.CAP_PROP_POS_FRAMES
#elif iscv2():
#    CAP_PROP_FRAME_COUNT = cv2.cv.CV_CAP_PROP_FRAME_COUNT 
#    CAP_PROP_FPS = cv2.cv.CV_CAP_PROP_FPS
#    CAP_PROP_POS_FRAMES = cv2.cv.CV_CAP_PROP_POS_FRAMES

CAP_PROP_FRAME_COUNT = cv2.CAP_PROP_FRAME_COUNT 
CAP_PROP_FPS = cv2.CAP_PROP_FPS
CAP_PROP_POS_FRAMES = cv2.CAP_PROP_POS_FRAMES

if __name__ == '__main__':
    import sys
    from os.path import *
    usage = "Usage: video2png <videopath> <outputdir>"
    parser = argparse.ArgumentParser(description='Convert video to png')
    parser.add_argument('--start-sec', dest='startsec', type=int, default=0, nargs='?', 
            help='specify path for the image file')
    parser.add_argument('--num-frame', dest='numframe', type=int, default=1, nargs='?', 
            help='specify path for the image file')
    parser.add_argument('--crop_top', dest='crop_top', type=int, default=0, nargs='?', 
            help='Num Pixel to be cropped from top')
    parser.add_argument('--crop_bottom', dest='crop_bottom', type=int, default=0, nargs='?', 
            help='Num Pixel to be cropped from bottom')
    parser.add_argument('--crop_left', dest='crop_left', type=int, default=0, nargs='?', 
            help='Num Pixel to be cropped from left')
    parser.add_argument('--crop_right', dest='crop_right', type=int, default=0, nargs='?', 
            help='Num Pixel to be cropped from right')
    parser.add_argument('--height', dest='height', type=int, default=375, nargs='?', 
            help='Num Pixel to be cropped from right')
    parser.add_argument('--width', dest='width', type=int, default=1242, nargs='?', 
            help='Num Pixel to be cropped from right')
    (opts, args) = parser.parse_known_args()
    if (len(args) < 2):
        print(usage)
        exit(-1)

    vi = args[0]
    outdir = join(args[1],'data')
    outoxts = join(args[1], 'oxts')
    if os.path.isdir(args[1]):
        os.mkdir(outoxts)
    else:
        print(usage)
        exit(-1)

    outoxts = join(outoxts, 'data')
    os.mkdir(outoxts)

    cap = cv2.VideoCapture(join(vi,"video.mp4"))
    fileoxts= open(join(vi,join("output","motion.txt"),'r')

    fcnt = int(cap.get(CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(CAP_PROP_FPS))

    startframe = fps * opts.startsec
    cap.set(CAP_PROP_POS_FRAMES, startframe);

    print('[video2png] Starting at {0}s (frame {1}). Total number of frames: {2}. Saving {3} frames...'.format(
            opts.startsec, startframe, fcnt, opts.numframe))

    readsuc, img = cap.read()
    i = startframe
    while readsuc and i-startframe<fcnt:
        outFile = '%010d.png'% (i-startframe)
        outfileoxts = '%010d.txt'% (i-startframe)
        im1 = img[opts.crop_top:img.shape[0]-opts.crop_bottom, opts.crop_left:img.shape[1]-opts.crop_right]
        im2 = cv2.resize(im1,(opts.width,opts.height))
        cv2.imwrite(join(outdir,outFile),im2)
        motion = fileoxts.readline()
        with open(join(outoxts,outfileoxts),'w') as foxts:
            foxts.write(motion)
        print(outFile)
		
        #reducing from 30fps to 10fps
        for J in range(3) :
            if i-startframe+J < fcnt :
                readsuc, img = cap.read()
                fileoxts.readline()
        i += 1

		
