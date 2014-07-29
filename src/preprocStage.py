

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
                secret, public, hashProdOne, noTags, cells, blockAssignments):
    
    x = ExpTimer()
    x.registerSession(workerName)
    x.registerTimer(workerName, "tag")
    x.registerTimer(workerName, "ibf")
    
    
    while True:
        try:
            job = taskQ.get()
            if job == "end":
                results["timers"] = x 
                endQ.put(results)
                break
            job = cPickle.loads(job)
            blkIndex = job["index"]
            
            indices = Ibf.getIndices(k, m, hashFunc, job["block"], cellsAssignment=cells)
            x.startTimer(workerName, "ibf")
            for i in indices:
                    results["cells"][i].add(job["block"], secret, public["n"],
                                         public["g"], hashProdOne)
            x.endTimer(workerName, "ibf")
            if blkIndex % 25000 == 0 and blkIndex > 0:
                    print "worker", workerName, blkIndex
            
        
            if blkIndex in blockAssignments:
                    results["w"][blkIndex] = singleW(job["block"], secret["u"])
                    
                
                    if noTags == False:
                        x.startTimer(workerName, "tag")
                        results["tags"][blkIndex] = singleTag(results["w"][blkIndex],
                                                          job["block"],
                                                          public["g"],
                                                          secret["d"],
                                                          public["n"])
                    x.endTimer(workerName, "tag")
            taskQ.task_done()
        except Empty:
            pass
            
def preprocWorker(publisherAddr, sinkAddr, cells, k, m,
                   blockSz, secret, public, hashProdOne,
                   blockAssignments, noTags, order):
    
    
    workerName = mp.current_process().name
    context = zmq.Context()
    taskQ = Queue()
    endQ = Queue()
    preprocTaskLock = threading.Lock()


    subSocket = context.socket(zmq.SUB)
    subSocket.setsockopt(zmq.SUBSCRIBE, b'work')
    subSocket.setsockopt(zmq.SUBSCRIBE, b'end')
    subSocket.connect(publisherAddr)
    hashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]

    
    print "PreprocWorker", workerName , "initiated"
    results = None
    if noTags == False:
        results = {"worker":workerName, "cells":{}, "w":{}, "tags":{}, "timers":None}
    else:
        results = {"worker":workerName, "cells":{}, "w":{}, "timers":None}
        
    
    
    taskThread = threading.Thread(target=preprocTask, 
                                  args=(taskQ, endQ, results, workerName, k, m, hashFunc, blockSz, 
                                secret, public, hashProdOne,
                                 noTags, cells, blockAssignments))
    taskThread.daemon = True
    taskThread.start()
    
    for i in range(m):
        results["cells"][i] = Cell(0,blockSz)
    
    while True:
        try:
            workItem = subSocket.recv_multipart()
            if workItem[0] == 'end':
                taskQ.put_nowait("end")
                
                res = endQ.get(True)
                for i in range(m):
                    if res["cells"][i].count == 0:
                        del results["cells"][i]
                print "END"
                endQ.task_done()
                
                rpc = RpcPdrClient(context)
                inMsg = rpc.rpcAddress(sinkAddr, res)
                if inMsg == "ACK":
                    break
            else:
                taskQ.put_nowait(workItem[1])
                
                
        except zmq.ZMQError as e:
                print e
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)

