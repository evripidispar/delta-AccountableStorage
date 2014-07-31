
import zmq
import gmpy2
import cPickle
import multiprocessing as mp
import threading
import BlockEngine as BE

from ExpTimer import ExpTimer
from Ibf import Ibf
from Queue import Queue
from Queue import Empty
from HashFunc import *
from client import RpcPdrClient
from CryptoUtil import pickPseudoRandomTheta

def validationTask(taskQ, endQ, results, workerName, k, m, hashFunc,
                   cells, blockAssignments, lostBlocks, cmbLock, cmbValue,
                   challenge, W, N, pbSize, blockSize, randomBlocksToTest=None):
    
    x = ExpTimer()
    
    x.registerSession(workerName)
    x.registerTimer(workerName, "cmbW")
    x.registerTimer(workerName, "qSet_check")
    startIndex = False
    while True:
        try:
            
            job = taskQ.get()
            if job == "end":
                results["timers"] = x
                endQ.put(results)
                break
            job = cPickle.loads(job)
            for blockPBItem in BE.chunks(job, pbSize):
                blk = BE.BlockDisk2Block(blockPBItem,blockSize)
                bIndex = blk.getDecimalIndex()
           
                if startIndex == False:
                    print "Worker-Task starts with block index", bIndex
                    startIndex = True
                
                if bIndex not in lostBlocks:
                    #if randomBlocksToTest != None and bIndex not in randomBlocksToTest:
                    #    continue
                   
                    if bIndex % 25000 == 0 and bIndex > 0:
                        print "Worker", workerName, bIndex
                    if bIndex in blockAssignments:
                        x.startTimer(workerName, "cmbW")
                        aI = pickPseudoRandomTheta(challenge, blk.getStringIndex())
                        aI = number.bytes_to_long(aI)
                        h = SHA256.new()
                        
                        wI = W[bIndex]
                        h.update(wI)
                        wI = number.bytes_to_long(h.digest())
                        wI = gmpy2.powmod(wI, aI, N)
                        
                        with cmbLock:
                            cmbValue["w"] *= wI
                            cmbValue["w"] = gmpy2.powmod(cmbValue["w"], 1, N)
                        x.endTimer(workerName, "cmbW")
                else:
                    if bIndex in blockAssignments:
                        x.startTimer(workerName, "qSet_check")
                        lostIndices = Ibf.getIndices(k, m, hashFunc, 
                                                     blk.getStringIndex(), isIndex=True)
                        
                        for lIndex in lostIndices:
                            if lIndex not in results["qSets"].keys():
                                results["qSets"][lIndex] = []
                            results["qSets"][lIndex].append(bIndex)
                        x.endTimer(workerName, "qSet_check")
                    
                       
        except Empty:
            pass

def worker(publisherAddr, sinkAddress, k, m, cells, blockAssignments,
           lostBlocks, cmbLock, cmbValue, challenge, W, N, pbSize, blockSize,
            randomBlocksToTest=None):
    
    workerName = mp.current_process().name
    
    taskQ = Queue()
    endQ = Queue()
    context = zmq.Context()
    subSocket = context.socket(zmq.SUB)
    subSocket.setsockopt(zmq.SUBSCRIBE, b'work')
    subSocket.setsockopt(zmq.SUBSCRIBE, b'end')
    subSocket.connect(publisherAddr)
    
    hashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]
    
    print "Validation worker", workerName , "initiated"
    print "blockAssignments", len(blockAssignments)
    
    results = {"worker":workerName, "qSets":{}, "timers":None}
    taskThread = threading.Thread(target=validationTask,
                                  args=(taskQ, endQ, results, workerName,
                                        k, m, hashFunc, cells, blockAssignments,
                                        lostBlocks, cmbLock, cmbValue, challenge,
                                        W, N, pbSize, blockSize, randomBlocksToTest))
    
    taskThread.daemon = True
    taskThread.start()
    
    while True:
        try:
            workItem = subSocket.recv_multipart()
            if workItem[0] == "end":
                taskQ.put("end")
                res = endQ.get(True)
                rpc = RpcPdrClient(context)
                inMsg = rpc.rpcAddress(sinkAddress, res)
                if inMsg == "ACK":
                    break
            else:
                taskQ.put(workItem[1])
                
        except zmq.ZMQError as e:
            print e
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)
