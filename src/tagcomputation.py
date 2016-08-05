
import zmq
import zhelpers
import time
import cPickle
import BlockEngine as be
import multiprocessing as mp
from ExpTimer import ExpTimer
from Queue import Queue
from TagGenerator import singleW
import threading
from TagGenerator import singleTag


def loadSavedTags(tagFile):
    fp = open(tagFile,"rb")
    d = cPickle.load(file(tagFile))
    fp.close()
    return (d["tags"], d["w"], d["key"], d["times"])

def saveTagsW2Disk(tagTimes, tags, w, blockNum, blockSize, sessionKey):
    
    message = {"tags":tags,
               "w":w,
               "times":tagTimes,
               "key":sessionKey}
    fname = "tags/wtagskey_%d_%d.dat" % (blockNum, blockSize/8)
    fp=open(fname,"wb")
    cPickle.dump(message,fp)
    fp.close()
    
    fname = "tags/tagperf_%d_%d.txt" % (blockNum, blockSize/8)
    fp = open(fname,"ab+")
    cPickle.dump(message["times"],fp)
    fp.close()

    return



def tagWorker(workerID, routerAddr,
              resQ, secret, public, blockSize):
    
    bW = {}
    bT = {}
    bTimer = ExpTimer()
    
    workerName = mp.current_process().name
    bTimer.registerSession(workerName)
    bTimer.registerTimer(workerName, "tag")
    
    reqSocket = zmq.Context().socket(zmq.REQ)
    zhelpers.set_id(reqSocket)
    reqSocket.connect(routerAddr)
    
    print "Worker" , workerName, "initiated"
    total = 0
    
    while True:
        reqSocket.send(b"ready")
        blockPB = reqSocket.recv()
        if blockPB == b"END":
            totalTagTime = bTimer.getTotalTimer(workerName, "tag")
            workerResults = cPickle.dumps([workerName, bW,bT,totalTagTime,total])
            resQ.put(workerResults)
            break
        else:
            total += 1
            block = be.BlockDisk2Block(blockPB, blockSize)
            bIndex = block.getDecimalIndex() 
            bTimer.startTimer(workerName, "tag")
            bW[bIndex] = singleW(block, secret["u"])
            bT[bIndex] = singleTag(
                                   bW[bIndex],
                                   block,
                                   public["g"],
                                   secret["d"],
                                   public["n"])
            bTimer.endTimer(workerName, "tag")
            



def driver(zmqContext, workersNum, dataFP, 
           protobufSize, blockSize, secret, public, key, blockNum):
    try:
    
        resQ = mp.Queue()
        routerAddress = "tcp://127.0.0.1:8888"
        routerSocket = zmqContext.socket(zmq.ROUTER)
        routerSocket.bind("tcp://*:8888")
        
        
        workersPool = []
        for w in xrange(workersNum):
            p = mp.Process(target=tagWorker,
                           args=(w,routerAddress, 
                                 resQ, secret, public, blockSize))
          
            p.start()
            workersPool.append(p)
        
        
        time.sleep(1)
        
        
        readfactor = be.getReadFactor(blockNum)
        readAmount = readfactor * protobufSize
        while True:
            dataChunk = dataFP.read(readAmount)
            if len(dataChunk) == 0:
                break
            else:
                for blockPB in be.chunks(dataChunk, protobufSize):
                    
                    address, empty, ready = routerSocket.recv_multipart()
                    routerSocket.send_multipart([
                                                 address,
                                                 b'',
                                                 blockPB])

        work = []
        readyNum = 0
        while readyNum != workersNum:
            address, empty, workerData = routerSocket.recv_multipart()
            if workerData == b'ready':
                routerSocket.send_multipart([
                                         address,
                                         b'',
                                         b'END'])
                readyNum+=1
        
            
        time.sleep(5)
        while True:
            jobRes = resQ.get()
            jobRes = cPickle.loads(jobRes)
            work.append(jobRes)
            if len(work) == workersNum:
                break
            
        resQ.close()
        for worker in workersPool:
            worker.join()
            worker.terminate()
            
        
        T = {}
        W = {}
        tagTimes = []
        for w in work:
            wName, wW, wT, wTime, wTotal = w
            for k,v in wW.items():
                W[k] = v
            for k,v in wT.items():
                T[k] = v
                
            tagTimes.append(wTime)
            print "Worker:", wName, "tasks:", wTotal, "time:", wTime
                
        
        saveTagsW2Disk(tagTimes, T, W, blockNum, blockSize, key)
    except zmq.ZMQError as e:
        print str(e)
        
            
