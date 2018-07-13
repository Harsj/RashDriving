#!/usr/bin/env python

import argparse
#import Image
import cv2
import os, sys

def resizeImage(infile, cw_dir="", input_dir="", output_dir="", size=(1242,375)):
     outfile = os.path.splitext(infile)[0]
     extension = os.path.splitext(infile)[1]

     if (cmp(extension, ".png")):
        return

     if infile != outfile:
        try :
            os.chdir(input_dir)
            #im = Image.open(infile)
            im = cv2.imread(infile)
            #im.thumbnail(size, Image.ANTIALIAS)
            im2 = cv2.resize(im,size)
            os.chdir(cw_dir)
            #os.chdir(output_dir)
            #im.save(output_dir+'/'+outfile+extension,"PNG")
            cv2.imwrite((output_dir+'/'+outfile+extension),im2)
        except IOError:
            print "cannot reduce image for ", infile


if __name__=="__main__":
    output_dir = "resized"
    data_dir = "data"
    usage = "Usage: image_resize <test video path where data folder is present>"
    parser = argparse.ArgumentParser(description='Convert video to png')
    (opts, args) = parser.parse_known_args()
    cdir = args[0]
    cwd = os.getcwd()

    if not os.path.exists(os.path.join(cdir,output_dir)):
        os.chdir(cdir)
        os.mkdir(output_dir)
        output_dir = os.path.join(cdir,output_dir)
        cdir = os.path.join(cdir,data_dir)
        os.chdir(cwd)

    for file1 in os.listdir(cdir):
        resizeImage(file1, cwd, cdir, output_dir)
