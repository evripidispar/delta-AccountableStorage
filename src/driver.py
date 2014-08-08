import argparse
import sys
from BlockUtil import *
from Ibf import *
import zmq
import preprocStage

import CloudPdrFuncs
import os
import BlockEngine as BE
from CloudPDRKey import CloudPDRKey
from Crypto.PublicKey import  RSA
from TagGenerator import TagGenerator
from Crypto.Hash import SHA256
from datetime import datetime
import MessageUtil as MU
import CloudPdrMessages_pb2
from client import RpcPdrClient
from PdrSession import PdrSession
from math import floor
from math import log, sqrt
from CryptoUtil import pickPseudoRandomTheta
from Crypto.Util import number
from Crypto.Random import random

from ExpTimer import ExpTimer
import multiprocessing as mp
from TagGenerator import singleTag
from TagGenerator import singleW
import struct
from PdrManager import IbfManager, QSetManager
import gmpy2
import copy
import ibfcomputation
import tagcomputation

import cPickle
import pprint
import validateServerProofStage
from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Queue import Queue
from Queue import Empty
import time
from copy import deepcopy

LOST_BLOCKS = 6

W = {}
Tags = {}

    
def processServerProof(cpdrProofMsg, session):
    et = ExpTimer()
    pName = mp.current_process().name
    et.registerSession(pName)
    
    
    et.registerTimer(pName, "subset-check")
    et.startTimer(pName, "subset-check")
    if len(cpdrProofMsg.proof.lostIndeces) > 0:
        res, reason = subsetAndLessThanDelta(session.fsInfo["blockNum"],
                                             cpdrProofMsg.proof.lostIndeces,
                                             session.delta)
        if res == False:
            print reason
            return False
     
    et.endTimer(pName, "subset-check")
    
    et.registerTimer(pName, "cmbW-start")
    et.startTimer(pName, "cmbW-start")
   
    sesSecret = session.sesKey.getSecretKeyFields() 
    
    
    servLost = cpdrProofMsg.proof.lostIndeces
    
    
    serCombinedSum = long(cpdrProofMsg.proof.combinedSum)
    gS = gmpy2.powmod(session.g, serCombinedSum, session.sesKey.key.n)
    serCombinedTag = long(cpdrProofMsg.proof.combinedTag)
   
    Te =gmpy2.powmod(serCombinedTag, sesSecret["e"], session.sesKey.key.n)
    et.endTimer(pName, "cmbW-start")
    
    gManager = mp.Manager()
    cmbW = gManager.dict()
    cmbW["w"] = 1L
    cmbW["cSum"] = 0L
    cmbW["all"] = 0L
    cmbW["all_count"] = 0L
    cmbW["alive"] = 0L
    cmbW["alive_count"] = 0L
    cmbWLock = mp.Lock()
    
    workerPool = []
    cellsAssignments = list(BE.chunkAlmostEqual(range(session.fsInfo["ibfLength"]), session.fsInfo["workers"]))
    blockAssignments = list(BE.chunkAlmostEqual(range(session.fsInfo["blockNum"]), session.fsInfo["workers"]))
    
    for w,cellsPerW,blocksPerW in zip(xrange(session.fsInfo["workers"]),
                                      cellsAssignments, blockAssignments):
        p = mp.Process(target=validateServerProofStage.worker,
                       args=(session.pubAddr, session.sinkAddr,
                             session.fsInfo["k"], session.fsInfo["ibfLength"],
                             cellsPerW, blocksPerW, servLost, cmbWLock, cmbW,
                             session.challenge, session.W, session.sesKey.key.n,
                             session.fsInfo["pbSize"], session.fsInfo["blkSz"], session.randomBlocks))
    
        p.start()
        workerPool.append(p)
    
    print "Waiting to initiate workers"
    time.sleep(5)
    fp = open(session.fsInfo["fsName"], "rb")
    fp.read(4)
    fp.read(session.fsInfo["skip"])
    
    blockStep=0
    while True:
        dataChunk = fp.read(session.fsInfo["bytesPerWorker"])
        if dataChunk:
            dat = cPickle.dumps(dataChunk)
            session.pubSocket.send_multipart(["work", dat])
            blockStep +=1
            if blockStep % 100000 == 0:
                print "Dispatched ", blockStep, "out of", session.fsInfo["blockNum"]
        else:
            session.pubSocket.send_multipart(["end"])
            break
    
    fp.close()
    work = []
    print "Waiting to gather results"
    while len(work) != session.fsInfo["workers"]:
        w = session.sinkSocket.recv_pyobj()
        session.sinkSocket.send("ACK")
        work.append(w)
    
    
    for w in workerPool:
        w.join()
        w.terminate()
    
    
    qS = {}
    for i in work:
        for k,v in i["qSets"].items():
            if k not in qS.keys():
                qS[k] = []
            qS[k] +=v
        session.TT[i["worker"]+str("_cmbW")] = i["timers"].getTotalTimer(i["worker"], "cmbW")
        session.TT[i["worker"]+str("_qSet_check")] = i["timers"].getTotalTimer(i["worker"], "qSet_check")
         
            
    
    et.registerTimer(pName, "cmbW-last")
    et.startTimer(pName, "cmbW-last")
    combinedWInv = number.inverse(cmbW["w"], session.sesKey.key.n)  #TODO: Not sure this is true
    RatioCheck1=Te*combinedWInv
    RatioCheck1 = gmpy2.powmod(RatioCheck1, 1, session.sesKey.key.n)
    
    pprint.pprint(["Lost in the server", len(servLost)])
    pprint.pprint(['All', cmbW["all"]])
    pprint.pprint(['All count', cmbW["all_count"]])
    pprint.pprint(['Alive', cmbW["alive"]])
    pprint.pprint(['Alive_count', cmbW["alive_count"]])
    pprint.pprint(['Result', cmbW["cSum"] == serCombinedSum])
   
    if RatioCheck1 != gS:
        
        print "FAIL#3: The Proof did not pass the first check to go to recover"
        
        print "ratioCheck1", RatioCheck1
        print "gS", gS
        sys.exit(0)
        return False

    et.endTimer(pName, "cmbW-last")

    print "# # # # # # # ##  # # # # # # # # # # # # # ##"
    
    et.registerTimer(pName, "lostSum")
    et.startTimer(pName, "lostSum")
    lostSum = {}
    for p in cpdrProofMsg.proof.lostTags.pairs:
        lostCombinedTag = long(p.v)
        Lre =gmpy2.powmod(lostCombinedTag, sesSecret["e"], session.sesKey.key.n)
        
        Qi = qS[p.k]
        combinedWL = 1
        for vQi in Qi:
            h = SHA256.new()
            aLBlk = pickPseudoRandomTheta(session.challenge, session.ibf.binPadLostIndex(vQi))
            aLI = number.bytes_to_long(aLBlk)
            wL = session.W[vQi]
            h.update(str(wL))
            wLHash = number.bytes_to_long(h.digest())
            waL = gmpy2.powmod(wLHash, aLI, session.sesKey.key.n)
            combinedWL = gmpy2.powmod((combinedWL*waL), 1, session.sesKey.key.n)
        
        combinedWLInv = number.inverse(combinedWL, session.sesKey.key.n)
        lostSum[p.k] = Lre*combinedWLInv
        lostSum[p.k] = gmpy2.powmod(lostSum[p.k], 1, session.sesKey.key.n)
    et.endTimer(pName, "lostSum")
    
    
    
    serverStateIbf = session.ibf.generateIbfFromProtobuf(cpdrProofMsg.proof.serverState,
                                                 session.fsInfo["blkSz"])
    #for i in range(serverStateIbf.m):
    #    if serverStateIbf.cells[i].count == 0:
    #        del serverStateIbf.cells[i]
        
    et.registerTimer(pName, "subIbf")
    et.startTimer(pName,"subIbf")
    diffIbf = session.ibf.subtractIbf(serverStateIbf, session.challenge,
                                   session.sesKey.key.n, session.fsInfo["blkSz"], True)
    et.endTimer(pName,"subIbf")
    
    for k in lostSum.keys():  
        print k
        
        assert k in serverStateIbf.cells.keys()
        assert k in session.ibf.cells.keys()
        assert k in diffIbf.cells.keys()
        
        diffIbf.cells[k].hashProd = copy.deepcopy(lostSum[k])
        assert diffIbf.cells[k].hashProd == lostSum[k]
    
    et.registerTimer(pName, "recover")
    et.startTimer(pName, "recover")
    L=CloudPdrFuncs.recover(diffIbf, servLost, session.challenge, session.sesKey.key.n, session.g)
    et.endTimer(pName, "recover")
        
    if L== None:
        et.changeTimerLabel(pName, "recover", "recover-fail")
        print "Failed to recover"
        return ("Exiting Failed Recovery...", session.TT, et) 
        
    for blk in L:
        print blk.getDecimalIndex()
      
    print "check"
    return ("Exiting Recovery...", session.TT, et)



def produceClientId():
    h = SHA256.new()
    h.update(str(datetime.now()))
    return h.hexdigest()




def subsetAndLessThanDelta(clientMaxBlockId, serverLost, delta):
    
    lossLen = len(serverLost)
    if lossLen >= clientMaxBlockId:
        return (False, "Fail#1: LostSet from the server is not subset of the client blocks ")
    
    for i in serverLost:
        if i>= 0 and i <= clientMaxBlockId:
            continue
    if lossLen > delta:
        print lossLen , delta
        return (False, "FAIL#2: Server has lost more than DELTA blocks")
    return (True, "")


def processClientMessages(incoming, session, lostNum=None):
    
    cpdrMsg = MU.constructCloudPdrMessageNet(incoming)
    
    if cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.INIT_ACK:
        print "Processing INIT-ACK"
        lostMsg = MU.constructLossMessage(lostNum, session.cltId)
        return lostMsg
        
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.LOSS_ACK:
        print "Processing LOSS_ACK"
        
        session.challenge = session.sesKey.generateChallenge()
        if session.isRandomChallenge == True:
            return MU.constructChallengeMessage(session.challenge, session.cltId, session.randomBlocks)
        else:
            return MU.constructChallengeMessage(session.challenge, session.cltId)
    
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.PROOF:
        print "Received Proof"
        res = processServerProof(cpdrMsg, session)
        return res

   
def chooseRandomBlocksForRandomChallenge(totalBlocks, precentage):
    if totalBlocks <= 10000:
        return xrange(totalBlocks)
    else:
        k = random.sample(xrange(totalBlocks), int(totalBlocks*precentage))
        return set(k)
    
def getsizeofDictionary(dictionary):
    size = sys.getsizeof(dictionary)
    for k,v in dictionary.items():
        size+=sys.getsizeof(k)
        size+=sys.getsizeof(v)
    return size

def main():
    
    p = argparse.ArgumentParser(description='Driver for IBF')

    
    p.add_argument('-b', dest='blkFp', action='store', default=None,
                   help='Serialized block filename as generated from BlockEngine')
    
    p.add_argument('-k', dest='hashNum', action='store', type=int,
                   default=5, help='Number of hash arguments')
    
    p.add_argument('-g', dest="genFile", action="store", default=None,
                 help="static generator file")
    
    p.add_argument('-n', dest='n', action='store', type=int,
                   default=1024, help='RSA modulus size')
    
    p.add_argument('-s', dest='size', action='store', type=int, default=512,
                   help='Data Bit Size')
    
    p.add_argument('-l', dest='lostNum', action='store', type=int, default=5,
                   help='Number of Lost Packets')
    
    p.add_argument('--task', dest='task', action='store', type=int, default=100,
                   help='Number of blocks per worker for the W,Tag calculation')
   
    p.add_argument('-w', dest="workers", action='store', type=int, default=4,
                  help='Number of worker processes ')
    
   
    p.add_argument('-r', dest="runId", action='store', help='Current running id')
    
    p.add_argument('--tagmode', dest="tagMode", action='store_true', help='Tag Mode',  default=False)
    p.add_argument('--tagload', dest="tagLoad", action='store', default=None, 
                   help='load tags/keys from location')
    
    p.add_argument('--dt', dest="dt", action='store', type=int, default=0, help='Type of delta')
    
    p.add_argument('--ibfmode', dest="ibfMode", action="store_true", help='store Preproc Mode', default=False)
    
    p.add_argument('--ibfload', dest="ibfLoad", action="store", default=None,
                   help='load ibf from ibf/w')
    
    p.add_argument("--randomMode", dest="randomMode", action="store_true", default=False,
                  help="Enable random blocks selection for the challenge")
   
   
    args = p.parse_args()
    if args.hashNum > 10: 
        print "Number of hashFunctions should be less than 10"
        sys.exit(-1)
        
    if args.blkFp == None:
        print 'Please specify a file that stores the block collection'
        sys.exit(-2)
    
    if args.genFile == None:
        print 'Please specify a generator file'
        sys.exit(-3)
        
    if args.runId == None:
        print 'Please specify run ID'
        sys.exit(-4)
        
    cltId = produceClientId()
    pdrSes = PdrSession(cltId)
    
    
    fp = open(args.genFile, "r")
    g = fp.read()
    g = long(g)
    fp.close() 
    pdrSes.addG(g)
    
    T, W, sesKey, wtTimes = (None,None,None,None)
    if args.tagLoad != None:
        print "Loading (tags,W) from disk"
        T, W, sesKey, wtTimes = tagcomputation.loadSavedTags(args.tagLoad)
        pdrSes.T = T
        pdrSes.W = W
        pdrSes.sesKey = CloudPDRKey(args.n, g, sesKey)
    else:
        pdrSes.sesKey = CloudPDRKey(args.n, g, RSA.generate(args.n))
    
    
    ibf, ibfTime = (None,None)
    if args.ibfLoad != None:
        print "Loading (ibf) from disk"
        ibf, ibfTime = ibfcomputation.loadIbfFromDisk(args.ibfLoad) 
        pdrSes.addState(ibf)
            
    #Generate key class
    secret = pdrSes.sesKey.getSecretKeyFields()
    public = pdrSes.sesKey.getPublicKeyFields()
    pdrSes.addSecret(secret)
    pubPB = pdrSes.sesKey.getProtoBufPubKey()
    
    
    fp=open(args.blkFp,"rb")
    fsSize = fp.read(4)
    fsSize, = struct.unpack("i", fsSize)
    fs = CloudPdrMessages_pb2.Filesystem()
    fs.ParseFromString(fp.read(int(fsSize)))
    
    import pprint
    pprint.pprint(fs.datSize)
    
#     ibfLength =  floor(log(fs.numBlk,2))
    log2Blocks = log(fs.numBlk, 2)
    log2Blocks = floor(log2Blocks)
    delta = int(log2Blocks)
    
    if args.dt == 1:
        delta = int(floor(sqrt(fs.numBlk)))
        
    args.lostNum = delta-1
    ibfLength = ((args.hashNum+1)*delta)
    ibfLength = int(ibfLength)
    pdrSes.addibfLength (ibfLength)
    
    totalBlockBytes = fs.pbSize*fs.numBlk
    bytesPerWorker = (args.task*totalBlockBytes)/ fs.numBlk
    
    pdrSes.addFsInfo(fs.numBlk, fs.pbSize, fs.datSize, int(fsSize), 
                     bytesPerWorker, args.workers, args.blkFp, ibfLength, args.hashNum)
    
    
    zmqContext =  zmq.Context()
    
    if args.ibfMode == True:
        ibfcomputation.driver(ibfLength, args.workers, fs.numBlk,
                              zmqContext, args.hashNum, fs.datSize,
                              secret, public, fs.pbSize, fp, bytesPerWorker)
        return
    
    if args.tagMode == True:
        tagcomputation.driver(zmqContext, args.workers,
                              fp, fs.pbSize, fs.datSize,
                              secret, public, pdrSes.sesKey.key,
                              fs.numBlk)
        return


#TODO update ibf, tag timeres        
       
    
    pdrSes.addDelta(delta)
    sizeTag = getsizeofDictionary(pdrSes.T)
    initMsg = MU.constructInitMessage(pubPB, args.blkFp, pdrSes.T,
                                      cltId, args.hashNum, delta,
                                       fs.numBlk, args.runId)
    ip = "newvpn14.cs.umd.edu"
#ip = '192.168.1.13'
    #ip = "127.0.0.1"
   
    clt = RpcPdrClient(zmqContext)    
    print "Sending Initialization message"
    initAck = clt.rpc(ip, 9090, initMsg) 
    print "Received Initialization ACK"
    
    lostMsg = processClientMessages(initAck, pdrSes, args.lostNum)
    print "Sending Lost message"
    lostAck = clt.rpc(ip, 9090, lostMsg)
    print "Received Lost-Ack message"
    
    
    challengeMsg = None
    if args.randomMode == True:
    
        randomBlocks = chooseRandomBlocksForRandomChallenge(fs.numBlk, 0.15)
    
        pdrSes.makeItRandomChallengeSession(randomBlocks)
        challengeMsg = processClientMessages(lostAck, pdrSes)
    else:
        challengeMsg = processClientMessages(lostAck, pdrSes)
    print "Sending Challenge message"
    proofMsg = clt.rpc(ip, 9090, challengeMsg)
    print "Received Proof message"
    
    result, proofParallelTimers, proofSequentialTimer  = processClientMessages(proofMsg, pdrSes)
    
    #zmqContext.term()
    
    run_results = {}
    
    for k in pdrSes.TT.keys():
        key = k[k.index("_")+1:]
        if key not in run_results.keys():
            run_results[key] = 0
        if pdrSes.TT[k] >  run_results[key]:
            run_results[key] = pdrSes.TT[k]
        
    for k in proofParallelTimers.keys():
        key = k[k.index("_")+1:]
        if key not in run_results.keys():
            run_results[key] = 0
        if proofParallelTimers[k] >  run_results[key]:
            run_results[key] = proofParallelTimers[k]
    
    pName = proofSequentialTimer.timers.keys()[0]
    for k in proofSequentialTimer.timers[pName].keys():
        if 'total' in k:
            s = k[0:k.index('total')-1]
            run_results[s] = proofSequentialTimer.timers[pName][k]
    
    run_results["tag-size"] = sizeTag
   # if doNotComputeTags == True:
   #     run_results["tag"] = loadedTagTime
   # if doNotComputIbf == True:
   #     run_results["ibf"] = loadedIbfTimes
    
    fp = open(args.runId, "a+")
    for k,v in run_results.items():
        fp.write(k.ljust(20)+"\t"+str(v).ljust(20)+"\n")
    fp.close()
    
    
    
    
    
    
    
    
if __name__ == "__main__":
    
    main()
    
