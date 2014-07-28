
import zmq
import gmpy2
import cPickle
import time
import threading
import multiprocessing as mp
import pprint

from ExpTimer import ExpTimer
from Queue import Queue
from Queue import Empty
from HashFunc import *
from client import RpcPdrClient
from Ibf import Ibf
from Cell import Cell
from CryptoUtil import pickPseudoRandomTheta


def serverProofTask(taskQ, endQ, results, workerName, cells, blockAssignments,
                    challenge, lostBlocks, tags, cmbLock, cmbVal, N, g, k, 
                    m, hashFunc, blkSize):
    
    x = ExpTimer()
    x.registerSession(workerName)
    x.registerTimer(workerName, "qSet_proof")
    x.registerTimer(workerName, "cSumKept")
    x.registerTimer(workerName, "cTagKept")
    x.registerTimer(workerName, "ibf_serv")
    
    while True:
        try:
            job = taskQ.get()
            taskQ.task_done()
            if job == "end":
                results["timers"] = x
                endQ.put(results)
                break
            
            job = cPickle.loads(job)
            bIndex = job['index']
            
            if bIndex not in lostBlocks:
                x.startTimer(workerName, "ibf_serv")
                indices = Ibf.getIndices(k, m, hashFunc, job["block"], cellsAssignment=cells)
                for i in indices:
                    if i not in results["cells"].keys():
                        results["cells"][i] = Cell(0, blkSize)
                    results["cells"][i].add(job["block"], challenge, N, g, True)
                x.endTimer(workerName, "ibf_serv")
                
                if bIndex in blockAssignments:
                
                    with cmbLock:
                        x.startTimer(workerName, "cSumKept")
                        x.startTimer(workerName, "cTagKept")
                        aI = pickPseudoRandomTheta(challenge, job['block'].getStringIndex())
                        aI = number.bytes_to_long(aI)
                        bI = number.bytes_to_long(job['block'].data.tobytes())
                        cmbVal["cSum"] += aI*bI
                        x.endTimer(workerName, "cSumKept")
                        cmbVal["cTag"] *= gmpy2.powmod(tags[bIndex], aI, N)
                        cmbVal["cTag"] = gmpy2.powmod(cmbVal["cTag"],1,N)
                        x.endTimer(workerName,"cTagKept")
                        
            else:
                if bIndex in blockAssignments:
                    x.startTimer(workerName, "qSet_proof")
                    lostIndices = Ibf.getIndices(k, m, hashFunc, 
                                                 job['block'].getStringIndex(), isIndex=True)
                    
                    for lIndex in lostIndices:
                        if lIndex not in results["qSets"].keys():
                            results["qSets"][lIndex] = []
                        results["qSets"][lIndex].append(bIndex)
                    x.endTimer(workerName, "qSet_proof")
                
        except Empty:
            pass
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)   


def serverProofWorker(publisherAddress, sinkAddress, cells,
                blocks, challenge, lostBlocks, tags, cmbLock, 
                cmbVal, N, g, k, m, blockSize):
    
    taskQ = Queue()
    endQ = Queue()
    
    context =  zmq.Context()
    subSocket = context.socket(zmq.SUB)
    subSocket.setsockopt(zmq.SUBSCRIBE, b"work")
    subSocket.setsockopt(zmq.SUBSCRIBE, b"end")
    subSocket.connect(publisherAddress)
    sinkSocket = context.socket(zmq.REQ)
    sinkSocket.connect(sinkAddress)
    
    workerName = mp.current_process().name
    hashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]
    results = {"worker":workerName, "cells":{}, "timers":{}, "qSets":{}}
    
    
    taskThread = threading.Thread(target=serverProofTask,
                                  args=(taskQ, endQ, results, workerName,
                                        cells, blocks, challenge, lostBlocks, tags, cmbLock, 
                                        cmbVal, N, g, k, m, hashFunc, blockSize))
    taskThread.daemon = True
    taskThread.start()
    
    print "Proof Worker", workerName, "initiated"
    while True:
        try:
            workItem = subSocket.recv_multipart()
            if workItem[0] == "end":
                time.sleep(1)
                taskQ.put_nowait("end")
                res = endQ.get(True)
                endQ.task_done()
                rpcClt = RpcPdrClient(context)
                inMsg = rpcClt.rpcAddress(sinkAddress, res)
                if inMsg == "ACK":
                    print "got ack, time to die"
                    break
            else:
                taskQ.put_nowait(workItem[1])
        except zmq.ZMQError as e:
                print e
        except (RuntimeError, TypeError, NameError) as e:
            print "Error", str(e)     
            