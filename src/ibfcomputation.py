
import zmq
import time
import cPickle
import threading
import BlockEngine as BE
import multiprocessing as mp
from Ibf import Ibf
from Queue import Queue
from Queue import Empty
from ExpTimer import ExpTimer
from HashFunc import *
from client import RpcPdrClient
from Cell import Cell


def loadIbfFromDisk(ibfFile):
    fp = open(ibfFile, "rb")
    obj = cPickle.load(fp)
    fp.close()    
    
    for i in obj["ibfTime"]:
        print i
    return (obj["ibf"],  obj["ibfTime"])



def saveIbf2Disk(IbfTimes, ibf, blockNum, blockSize):
    outputName = "preproc/preproc_%s_%s.data" % (str(blockNum), str(blockSize/8))
    ibfTimesPerWorker = []
    for k,v in IbfTimes.items():
        ibfTimesPerWorker.append(v)
    
    fp = open(outputName,"wb")
    cPickle.dump({"ibf":ibf, "ibfTime":ibfTimesPerWorker}, fp)
    fp.close()
    return outputName

 
def ibfTask(taskQ, endQ, results, workerName, k, m, hashFunc, blockSz, 
                secret, public, cells, threadId, taskLock,
                sharedTimer, pbSize, hashProdOne=True):
    
    tName = workerName+"_"+str(threadId)
    with taskLock:
        results["timerNames"].append(tName)
    sharedTimer.registerSession(tName)
    sharedTimer.registerTimer(tName, "ibf")
    
    while True:
        try:
            job = taskQ.get()
            taskQ.task_done()
            
            if job == "end":
                endQ.put(tName)
                break
            job = cPickle.loads(job)
            for blockPBItem in BE.chunks(job, pbSize):
                
                blk = BE.BlockDisk2Block(blockPBItem, blockSz)
                bIndex = blk.getDecimalIndex()
                indices = Ibf.getIndices(k, m, hashFunc, blk, cellsAssignment=cells)    
                
                sharedTimer.startTimer(tName, "ibf")
                for i in indices:
                        results["cells"][i].add(blk, secret, public["n"],public["g"], hashProdOne)
                sharedTimer.endTimer(tName, "ibf")     
        except Empty:
            pass
    

 
                                 
                
def ibfWorker(publisherAddr, sinkAddr, cells, k, m,
                   blockSz, secret, public, w, pbSize,
                   hashProdOne=True):
                
    
    workerName = mp.current_process().name
    context = zmq.Context()
    taskQ = Queue()
    endQ = Queue()
    taskLock = threading.Lock()
    sharedTimer = ExpTimer()
    threadsNumber = 1 #ALWAYS 1! This is here not to slow down the subscriber
    
    subSocket = context.socket(zmq.SUB)
    subSocket.setsockopt(zmq.SUBSCRIBE, b'work')
    subSocket.setsockopt(zmq.SUBSCRIBE, b'end')
    subSocket.connect(publisherAddr)
    hashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]
    cells = set(cells)
    
    print "PreprocWorker", workerName , "initiated"
    results = {"worker":workerName, "cells":{}, "w":{}, "timers":None, "timerNames":[]}
        
    for i in xrange(threadsNumber):
        taskThread = threading.Thread(target=ibfTask, 
                                  args=(taskQ, endQ, results, 
                                        workerName, k, m, hashFunc, blockSz, 
                                        secret, public, cells, i, taskLock,
                                        sharedTimer, pbSize))
        
        taskThread.daemon = True
        taskThread.start()
    
    for i in range(m):
        results["cells"][i] = Cell(0,blockSz)
    
    while True:
        try:
            workItem = subSocket.recv_multipart()
            if workItem[0] == 'end':
                for i in xrange(threadsNumber):
                    taskQ.put_nowait("end")
                
                finishedTaskThreads = set()
                while len(finishedTaskThreads) != threadsNumber:
                    tName = endQ.get(True)
                    endQ.task_done()
                    finishedTaskThreads.add(tName)
                
                
                results["timers"] = sharedTimer
                for i in range(m):
                    if results["cells"][i].count == 0:        
                        del results["cells"][i]
                rpc = RpcPdrClient(context)
                inMsg = rpc.rpcAddress(sinkAddr, results)
                if inMsg == "ACK":
                    break
            else:
                taskQ.put_nowait(workItem[1])
                
        except zmq.ZMQError as e:
                print "ZMQ Exception", str(e)
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)


def driver(ibfLength, workersNum, blocksNum, zmqContext, k, dataSize,
           secret, public, protobufSize, dataFP, bytesPerWorker):
    
    publisherAddress = "tcp://127.0.0.1:9998"
    sinkAddress = "tcp://127.0.0.1:9999"
    
    publishSocket = zmqContext.socket(zmq.PUB)
    publishSocket.bind(publisherAddress)
    
    sinkSocket = zmqContext.socket(zmq.REP)
    sinkSocket.bind(sinkAddress)
    
    cellAssignments = list(BE.chunkAlmostEqual(range(ibfLength), workersNum))
    
    
    workersPool = []
    for w, cellsPerW in zip(xrange(workersNum), cellAssignments):
        p = mp.Process(target=ibfWorker,
                       args=(publisherAddress, sinkAddress, cellsPerW, 
                             k, ibfLength, dataSize,
                             secret, public, w,protobufSize))
        p.start()
        workersPool.append(p)

    time.sleep(5)
    while True:
        dataChunk = dataFP.read(50*protobufSize)
        if len(dataChunk) ==0:
            publishSocket.send_multipart(["end"])
            break
        else: 
            dat = cPickle.dumps(dataChunk)
            publishSocket.send_multipart(['work', dat])     

            

    dataFP.close()
    work = []
    print 'Waiting'
    while len(work) != workersNum:
        w = sinkSocket.recv_pyobj()
        sinkSocket.send("ACK")
        work.append(w)
                 
    localIbf = Ibf(k, ibfLength)    
    TT = {}
    for i in work:
        localIbf.cells.update(i["cells"])
        for tName in i["timerNames"]:
            TT[tName+str("_ibf")] = i["timers"].getTotalTimer(tName, "ibf")
            print tName, TT[tName+str("_ibf")]
            
    for worker in workersPool:
            worker.join()
            worker.terminate()
    
    saveIbf2Disk(TT, localIbf, blocksNum, dataSize)
    
