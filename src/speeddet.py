import argparse
from os import listdir
from os.path import isfile, join, splitext, dirname, basename
from ntpath import basename
import numpy as np
import cv2
from matplotlib import pyplot as plt
from util import *
from path import *
from objdet import *
import csv
from multiprocessing.pool import ThreadPool
from functools import partial
from sklearn import datasets, linear_model
import pickle
from linearmodel import *

def lookup(speedmode):
    if (speedmode==0):
        includeflow = True
        includeobj = False
        includeimg = False
    elif (speedmode ==1):
        includeflow = True
        includeobj = True
        includeimg = False
    elif (speedmode==2):
        includeflow = True
        includeobj = False
        includeimg = True
    elif (speedmode==3):
        includeflow = True
        includeobj = True
        includeimg = True
    elif (speedmode==4):
        includeflow = False
        includeobj = False
        includeimg = True
    return includeflow, includeobj, includeimg

def drawflow(img, flow, step=16):
    h, w = img.shape[:2]
    y, x = np.mgrid[step/2:h:step, step/2:w:step].reshape(2,-1).astype(int)
    fx, fy = flow[y,x].T
    lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
    lines = np.int32(lines + 0.5)
    cv2.polylines(img, lines, 0, bgr('g'))
    for (x1, y1), (x2, y2) in lines:
        cv2.circle(img, (x1, y1), 2, bgr('g'), -1)
    return img

def drawAvgflow(img, avgflow):
    h, w = img.shape[:2]
    hs, ws = avgflow.shape[:2]
    hstep = h/hs
    wstep = w/ws
    # print(h,w, hstep, wstep, hs, ws, h/hstep, w/wstep)
    y, x = np.mgrid[hstep/2:hstep*hs:hstep, wstep/2:wstep*ws:wstep].reshape(2,-1).astype(int)
    ys, xs = np.mgrid[0:hs, 0:ws].reshape(2,-1).astype(int)
    fx, fy = avgflow[ys,xs].T
    lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
    lines = np.int32(lines + 0.5)
    cv2.polylines(img, lines, 0, bgr('r'), thickness=2)
    for (x1, y1), (x2, y2) in lines:
        cv2.circle(img, (x1, y1), 4, bgr('r'), -1)
    return img

def detflow(frame, prev, cur, **options):
    flowmode = options['flowmode']
    flow = getflow(prev, cur, checkcache=False, **options)
    avgflow = getAvgChannel(flow, **options)
    frame = drawflow(frame, flow)
    frame = drawAvgflow(frame, avgflow)
    return frame

def getflow(prev, cur, **options):
    path = options['path']
    fn = options['fn']
    flow_path = '{0}{1}.flow'.format(SCRATCH_PATH,
      '{0}/{1}'.format(path,fn).replace('/','_').replace('..',''))

    if 'flowMap' in options and flow_path in options['flowMap']:
        flow = options['flowMap'][flow_path]
    elif isfile(flow_path):
        if options['checkcache']: return
        # print('load {}'.format(flow_path))
        try:
          flow = pickle.load(open(flow_path, "rb" ))
        except:
          print('Fail to load {}'.format(flow_path))
          sys.exit(-1)
        if 'flowMap' in options:
            options['flowMap'][flow_path] = flow
    else:
        # print('recompute {}'.format(flow_path))
        prevgray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
        gray = cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)
        if iscv2():
            flow = cv2.calcOpticalFlowFarneback(prevgray, gray, 0.5, 3, 15, 3, 5, 1.2, 0)
        elif iscv3():
            flow = cv2.calcOpticalFlowFarneback(prevgray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        pickle.dump(flow , open(flow_path, "wb"))
    return flow

def getAvgChannel(channel, **options):
    rseg = options['rseg']
    cseg = options['cseg']
    h, w = channel.shape[:2]
    rstride = h / rseg
    cstride = w / cseg
    avg = np.ndarray((rseg, cseg, channel.shape[2]), dtype=channel.dtype)
    for ir in range(0, rseg):
        rstart = ir*rstride
        rend = min(rstart+rstride, h)
        for ic in range(0, cseg):
            cstart = ic*cstride
            cend = min(cstart+cstride, w)
            grid = channel[rstart:rend, cstart:cend, :]
            avg[ir, ic, :] = np.mean(grid, axis=(0,1))
    return avg

def loadHeader(path):
    headers = {}
    if os.path.isdir(path):
      with open('{0}/dataformat.txt'.format(path), 'r') as dataformat:
          for i, line in enumerate(dataformat):
              headers[line.split(':')[0]] = i
    return headers

def loadLabels(fn, headers, labels, labelpath):
    if os.path.isdir(labelpath):
      with open('{0}/data/{1}.txt'.format(labelpath, fn), 'r') as data:
        line = data.readline()
        vals = line.split(' ')
        for key in labels:
            labels[key].append(float(vals[headers[key]]))

def loadFlow(prev, cur, **options):
    flowmode = options['flowmode']
    if flowmode==0:
        flow = getflow(prev, cur, **options)
    elif flowmode==1:
        flow = getflow(prev, cur, **options)
        flow = polarflow(flow, **options)
    elif flowmode==2:
        flow = getflow(prev, cur, **options)
        flow = getAvgChannel(flow, **options)
    elif flowmode==3:
        flow = getflow(prev, cur, **options)
        flow = getAvgChannel(flow, **options)
        flow = polarflow(flow, **options)
    return flow

def loadObj(im, **options):
    flowmode = options['flowmode']
    objchannel = getObjChannel(im, **options)
    if flowmode in [2,3]:
        objchannel = getAvgChannel(objchannel, **options)
    return objchannel

def loadImg(rgb, **options):
    flowmode = options['flowmode']
    if flowmode in [2,3]:
        rgb = getAvgChannel(rgb, **options)
    return rgb

def loadInputX(prev, cur, **options):
    H,W,C = options['inputshape']
    model = options['model']
    path = options['path']
    fn = options['fn']
    speedmode = options['speedmode']
    flowmode = options['flowmode']
    rseg = options['rseg']
    cseg = options['cseg']
    if flowmode in [2,3]:
        H = rseg; W = cseg
    speedX = np.zeros((H,W,0))
    includeflow, includeobj, includeimg = lookup(speedmode)
    options['checkcache'] = False
    if includeflow:
        flow = loadFlow(prev, cur, **options)
        speedX = np.concatenate((speedX,flow), axis=-1)
    if includeobj:
        objchannel = loadObj(cur, **options)
        speedX = np.concatenate((speedX,objchannel), axis=-1)
    if includeimg:
        rgb = loadImg(cur, **options)
        speedX = np.concatenate((speedX, rgb), axis=-1)
    if (speedX.shape != (H,W,C)):
        raise Exception('data input shape={} not equals to expected shape!{}'.format(
            (H,W,C), speedX.shape))
    return speedX

def loadData(framePaths, **options):
    H,W,C = options['inputshape']
    speedmode = options['speedmode']
    flowmode = options['flowmode']
    rseg = options['rseg']
    cseg = options['cseg']
    speedXs = []
    path = dirname(framePaths[0])
    headers = loadHeader('{0}/../oxts'.format(path))
    if options['if_af'] == 1:
        labels = dict(vf=[], wu=[], af=[])
    elif options['if_af'] == 0:
        labels = dict(vf=[], wu=[])
    elif options['if_af'] == 2:
        labels = dict(vf=[])
    elif options['if_af'] == 3:
        labels = dict(wu=[])
    im = None
    if flowmode in [2,3]:
        H = rseg; W = cseg
    for framePath in framePaths:
        fn, ext = splitext(basename(framePath))
        path = dirname(framePath) + "/"
        options['path'] = path
        options['fn'] = fn
        includeflow, includeobj, includeimg = lookup(speedmode)
        if includeobj or includeimg:
            im = cv2.imread(framePath, cv2.IMREAD_COLOR)
        else:
            im = None
        speedX = loadInputX(None, im, **options)
        speedXs.append(speedX)
        # print('speedmode={} speedX.shape={}'.format(speedmode, np.array(speedX).shape))
        loadLabels(fn, headers, labels, '{0}/../oxts'.format(path))
    speedXs = np.reshape(np.array(speedXs), (-1, H,W,C))
    if options['if_af']==1:
        vf = np.reshape(labels['vf'], (-1, 1))
        wu = np.reshape(labels['wu'], (-1, 1))
        af = np.reshape(labels['af'], (-1, 1))
        speedYs = np.hstack((vf, wu, af))
    elif options['if_af']==0:
        vf = np.reshape(labels['vf'], (-1, 1))
        wu = np.reshape(labels['wu'], (-1, 1))
        speedYs = np.hstack((vf, wu))
    elif options['if_af']==2:
        vf = np.reshape(labels['vf'], (-1, 1))
        speedYs = np.hstack((vf,))
    elif options['if_af']==3:
        wu = np.reshape(labels['wu'], (-1, 1))
        speedYs = np.hstack((wu,))
    # print("speedXs.shape={} speedYs.shape={}".format(speedXs.shape, speedYs.shape))
    return ([speedXs, speedYs])

def polarflow(flow, **options):
    cplx = flow[:,:,0] + flow[:,:,1] * 1j
    H,W = cplx.shape
    mag = np.reshape(np.absolute(cplx), (H,W,1))
    ang = np.reshape(np.angle(cplx), (H,W,1))
    return np.concatenate((mag,ang), axis=-1)

def predSpeed(im, prev, cur, labels, restored_model, labelpath, **options):
    mode = options['mode']
    path = options['path']
    model = options['model']
    speedmode = options['speedmode']
    if prev is None:
        return im, {}
    X_test = loadInputX(prev, cur, **options)
    if model=='linear':
        vf, wu = linearRegressionModelTest(X_test, **options)
        wu = np.rad2deg(wu)
        gtvf = labels['vf'][-1]
        gtwu = np.rad2deg(labels['wu'][-1])
        res = dict(vf=(vf, gtvf), wu=(wu, gtwu))
    elif model=='conv':
        if options['if_af']==1:
            vf, wu, af = restored_model.test(X_test)
        elif options['if_af']==0:
            vf,wu = restored_model.test(X_test)
        elif options['if_af']==2:
            vf = restored_model.test(X_test)
        elif options['if_af']==3:
            wu = restored_model.test(X_test)
        if os.path.isdir(labelpath):
            if options['if_af']==1:
                gtvf = labels['vf'][-1]
                gtwu = labels['wu'][-1]
                gtaf = labels['af'][-1]
            elif options['if_af']==0:
                gtvf = labels['vf'][-1]
                gtwu = labels['wu'][-1]
            elif options['if_af']==2:
                gtvf = labels['vf'][-1]
            elif options['if_af']==3:
                gtwu = labels['wu'][-1]
        else :
            if options['if_af']==1:
                gtvf = 0
                gtwu = 0
                gtaf = 0
            elif options['if_af']==0:
                gtvf = 0
                gtwu = 0
            elif options['if_af']==2:
                gtvf = 0
            elif options['if_af']==3:
                gtwu = 0
        #if mode=='all' and not options['if_af']==2:
            #wu = np.rad2deg(wu)
        #if mode=='all' and not options['if_af']==2:
            #gtwu = np.rad2deg(gtwu)
        if options['if_af']==1:
            res = dict(vf=(vf, gtvf), wu=(wu, gtwu), af=(af, gtaf))
        elif options['if_af']==0:
            res = dict(vf=(vf, gtvf), wu=(wu, gtwu))
        elif options['if_af']==2:
            res = dict(vf=(vf, gtvf))
        elif options['if_af']==3:
            res = dict(wu=(wu, gtwu))
    return im, res

def trainSpeed(frameFns, **options):
    from convmodel import ConvModel
    pcttrain = options['pcttrain']
    model = options['model']
    valmode = options['valmode']
    print('Start training speed ...')

    frameFns = np.array(frameFns)
    N = frameFns.shape[0]
    numTrain = int(round(N*pcttrain))
    mask = np.zeros(N, dtype=bool)
    mask[:numTrain] = True
    if valmode==0:
        np.random.shuffle(mask)
    frameTrain = frameFns[mask]
    frameVal = frameFns[~mask]
    if model=='linear':
        pass
    elif model=='conv':
        conv_model = ConvModel(options)
        conv_model.train(frameTrain, frameVal)
        conv_model.close()

def trainSpeedOld(speedXs, labels, **options):
    """
    Train a linear regression model for speed detection

    :param speedXs: averaged dense flow of multiple videos. speedXs[video, frame, flowmag+flowang]
    :param labels: a dictionary of true labels of each frame
    :returns: this is a description of what is returned
    :raises keyError: raises an exception
    """
    pcttrain = 0.8
    model = options['model']
    print('Start training speed ...')

    numTrain = int(round(len(speedXs)*(pctTrain)))
    # Split the data into training/testing sets
    X_train = []
    X_test = []
    vly_train = []
    vly_test = []
    agy_train = []
    agy_test = []
    for speedX,lb in zip(speedXs, labels):
        mask = np.zeros(len(speedX), dtype=bool)
        mask[:numTrain] = True
        np.random.shuffle(mask)
        # mask = np.random.randint(10, size=len(speedX)) < pctTrain*10

        speedX = np.array(speedX)
        xtrain = speedX[mask]
        xtest = speedX[~mask]
        X_train += xtrain.tolist()
        X_test += xtest.tolist()
        lb['vf'] = np.array(lb['vf'])
        vly_train += lb['vf'][mask].tolist()
        vly_test += lb['vf'][~mask].tolist()
        lb['wu'] = np.array(lb['wu'])
        agy_train += lb['wu'][mask].tolist()
        agy_test += lb['wu'][~mask].tolist()

    X_train = np.array(X_train)
    X_test = np.array(X_test)
    print("X_train.shape={} X_test.shape={}".format(X_train.shape, X_test.shape))
    vly_train = np.array(vly_train)
    vly_test = np.array(vly_test)
    agy_train = np.array(agy_train)
    agy_test = np.array(agy_test)

    if model=='linear':
        vlmse, vlvar, agmse, agvar = linearRegressionModelTrain(
                X_train, X_test,
                vly_train, vly_test,
                agy_train, agy_test,
                **options)
    elif model=='conv':
        conv_model = ConvModel(options)
        vlmse, vlvar, agmse, agvar = conv_model.train(X_train, X_test,
                vly_train,vly_test, agy_train, agy_test)
        conv_model.close()
        # clear old variables
        # tf.reset_default_graph()
    # The mean squared error
    print("Speed mean squared error: {:.2f}, Speed variance score: {:.2f}, Angle mean squared error:{:.2e}, Angle variance score: {:.2f}".format(vlmse, vlvar, agmse, agvar))
    return (vlmse, vlvar, agmse, agvar)

# def main():

# if __name__ == "__main__":
    # main()
