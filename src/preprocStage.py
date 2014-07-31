

import cPickle
import multiprocessing as mp
import zmq 
import threading 
import time
import BlockEngine as BE

from client import RpcPdrClient
from Ibf import Ibf
from Cell import Cell
from Queue import Empty
from Queue import Queue
from TagGenerator import singleTag
from TagGenerator import singleW
from HashFunc import *
from ExpTimer import ExpTimer


def preprocTask(taskQ, endQ, results, workerName, k, m, hashFunc, blockSz, 
                secret, public, hashProdOne, noTags, cells, blockAssignments, 
                threadId, taskLock, sharedTimer, pbSize):
    
    
    tName = workerName+"_"+str(threadId)
    with taskLock:
        results["timerNames"].append(tName)
    sharedTimer.registerSession(tName)
    sharedTimer.registerTimer(tName, "tag")
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

                if bIndex in blockAssignments:
                    results["w"][bIndex] = singleW(blk, secret["u"])
                
                if noTags == False:
                    sharedTimer.startTimer(tName, "tag")
                    results["tags"][bIndex] = singleTag(results["w"][bIndex],
                                                          blk,
                                                          public["g"],
                                                          secret["d"],
                                                          public["n"])
                    sharedTimer.endTimer(tName, "tag")
            
        except Empty:
            pass
            
def preprocWorker(publisherAddr, sinkAddr, cells, k, m,
                   blockSz, secret, public, hashProdOne,
                   blockAssignments, noTags, order, pbSize):
    
    
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

    
    print "PreprocWorker", workerName , "initiated"
    results = None
    if noTags == False:
        results = {"worker":workerName, "cells":{}, "w":{}, "tags":{}, "timers":None, "timerNames":[]}
    else:
        results = {"worker":workerName, "cells":{}, "w":{}, "timers":None, "timerNames":[]}
        
    
    for i in xrange(threadsNumber):
        taskThread = threading.Thread(target=preprocTask, 
                                  args=(taskQ, endQ, results, workerName, k, m, hashFunc, blockSz, 
                                secret, public, hashProdOne, noTags, 
                                cells, blockAssignments, i, taskLock,
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
                print "END"
                
                
                rpc = RpcPdrClient(context)
                inMsg = rpc.rpcAddress(sinkAddr, results)
                if inMsg == "ACK":
                    break
            else:
                taskQ.put_nowait(workItem[1])
                
        except zmq.ZMQError as e:
                print e
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)

