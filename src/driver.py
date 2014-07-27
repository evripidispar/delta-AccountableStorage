import argparse
import sys
from BlockUtil import *
from Ibf import *
import zmq

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
from ExpTimer import ExpTimer
import multiprocessing as mp
from TagGenerator import singleTag
from TagGenerator import singleW
import struct
from PdrManager import IbfManager, QSetManager
import gmpy2
import copy

import cPickle
import psutil
from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Queue import Queue
from Queue import Empty
from preprocStage import preprocWorker

LOST_BLOCKS = 6

W = {}
Tags = {}

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




def workerTask(inputQueue,W,T,ibf,blockProtoBufSz,blockDataSz,secret,public, TT, noTags, lock):
    
    pName = mp.current_process().name
    x = ExpTimer()
    x.registerSession(pName)
    x.registerTimer(pName, "tag")
    x.registerTimer(pName, "ibf")
    
    while True:
        item = inputQueue.get()
        if item == "END":
            TT[pName+str("_tag")] = x.getTotalTimer(pName, "tag")
            TT[pName+str("_ibf")] = x.getTotalTimer(pName, "ibf")
            return
        
        for blockPBItem in BE.chunks(item, blockProtoBufSz):
            block = BE.BlockDisk2Block(blockPBItem, blockDataSz)
            bIndex = block.getDecimalIndex()
            x.startTimer(pName, "tag")
            w = singleW(block, secret["u"])
            if noTags == False:
                tag = singleTag(w, block, public["g"], secret["d"], public["n"])
                x.endTimer(pName, "tag")
                T[bIndex] = tag
                
            W[bIndex] = w
            
            
            x.startTimer(pName, "ibf")
            with lock:
                ibf.insert(block, None, public["n"], public["g"], True)
            x.endTimer(pName, "ibf")
            del block




def clientWorkerProof(inputQueue, blockProtoBufSz, blockDataSz, lost, chlng, W, N, comb, lock, qSets, ibf, manager, TT):
    
    
    pName = mp.current_process().name
    x = ExpTimer()
    x.registerSession(pName)
    x.registerTimer(pName, "cmbW")
    x.registerTimer(pName, "qSet_check")
    
    while True:
        item = inputQueue.get()
        if item == "END":
            TT[pName+str("_cmbW")] = x.getTotalTimer(pName, "cmbW")
            TT[pName+str("_qSet_check")] = x.getTotalTimer(pName, "qSet_check")
            return
        
        for blockPBItem in BE.chunks(item, blockProtoBufSz):
            block = BE.BlockDisk2Block(blockPBItem, blockDataSz)
            bIndex = block.getDecimalIndex()
            if bIndex in lost:
                x.startTimer(pName, "qSet_check")
                binBlockIndex = block.getStringIndex()
                indices = ibf.getIndices(binBlockIndex, True)
                for i in indices:
                    with lock:
                        qSets.addValue(i, bIndex)
                        
                x.endTimer(pName, "qSet_check")
                del block
                continue
            
            x.startTimer(pName, "cmbW")
            aI = pickPseudoRandomTheta(chlng, block.getStringIndex())
            aI = number.bytes_to_long(aI)
            h = SHA256.new()
            wI = W[bIndex]
            h.update(wI)
            wI = number.bytes_to_long(h.digest())
            wI = gmpy2.powmod(wI, aI, N)
            with lock:
                comb["w"] *= wI
                comb["w"] = gmpy2.powmod(comb["w"], 1, N)
            x.endTimer(pName, "cmbW")
            del block

    
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
    
#     inputQueue, blockProtoBufSz, blockDataSz, lost, chlng, W, N, combW, lock
    
    gManager = mp.Manager()
    combRes = gManager.dict()
    TT = gManager.dict()
    combRes["w"] = 1
    
    
    qSetManager = QSetManager()
    qSetManager.start()
    qSets = qSetManager.QSet()
    
    combLock = mp.Lock()
    print session.fsInfo["workers"]
    bytesPerWorker = mp.Queue(session.fsInfo["workers"])
    
    workerPool = []
    for i in xrange(session.fsInfo["workers"]):
        p = mp.Process(target=clientWorkerProof,
                       args=(bytesPerWorker, session.fsInfo["pbSize"],
                             session.fsInfo["blkSz"], servLost, 
                             session.challenge, session.W, session.sesKey.key.n,
                             combRes, combLock, qSets, session.ibf, gManager, TT))
        p.start()
        
        workerPool.append(p)
    
    fp = open(session.fsInfo["fsName"], "rb")
    fp.read(4)
    fp.read(session.fsInfo["skip"])
    
    while True:
        chunk = fp.read(session.fsInfo["bytesPerWorker"])
        if chunk:
            bytesPerWorker.put(chunk)
        else:
            for j in xrange(session.fsInfo["workers"]):
                bytesPerWorker.put("END")
            break
    
    for p in workerPool:
        p.join()
        
    for p in workerPool:
        p.terminate()
    
    
    fp.close()
   
   
   
    et.registerTimer(pName, "cmbW-last")
    et.startTimer(pName, "cmbW-last")
    combinedWInv = number.inverse(combRes["w"], session.sesKey.key.n)  #TODO: Not sure this is true
    RatioCheck1=Te*combinedWInv
    RatioCheck1 = gmpy2.powmod(RatioCheck1, 1, session.sesKey.key.n)
    
   
    if RatioCheck1 != gS:
        print "FAIL#3: The Proof did not pass the first check to go to recover"
        return False

    et.endTimer(pName, "cmbW-last")

    print "# # # # # # # ##  # # # # # # # # # # # # # ##"
    
   
    qS = qSets.qSets()
    
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
    
    
    #serverStateIbf = session.ibf.generateIbfFromProtobuf(cpdrProofMsg.proof.serverState,
    #                                         session.fsInfo["blkSz"])
    
    print session.ibf.m()
    ibf = Ibf(session.ibf.k(), session.ibf.m())
    
    serverStateIbf = ibf.generateIbfFromProtobuf(cpdrProofMsg.proof.serverState,
                                                 session.fsInfo["blkSz"])
        
    
    
    localIbf = Ibf(session.fsInfo["k"], session.fsInfo["ibfLength"])
    localIbf.zero(session.fsInfo["blkSz"])
    
    start = 0
    step = 100
    lc = []
    while True:
        res = session.ibf.rangedCells(start,step)
        if len(res) == 0:
            break
        lc+= res
        start+=step
        
    for entry in lc:
        k,c = entry
        localIbf.setSingleCell(k, c)
    
    #lc = session.ibf.cells()
    print "-----"
    #localIbf.setCells(lc)
    et.registerTimer(pName, "subIbf")
    et.startTimer(pName,"subIbf")
    diffIbf = localIbf.subtractIbf(serverStateIbf, session.challenge,
                                    session.sesKey.key.n, session.fsInfo["blkSz"], True)
    #diffIbf = session.ibf.subtractIbf(serverStateIbf, session.challenge,
    #                               session.sesKey.key.n, session.fsInfo["blkSz"], True)

    et.endTimer(pName,"subIbf")
    
    for k in lostSum.keys():  
        diffIbf.cells[k].hashProd = copy.deepcopy(lostSum[k])
        assert diffIbf.cells[k].hashProd == lostSum[k]
    
    et.registerTimer(pName, "recover")
    et.startTimer(pName, "recover")
    L=CloudPdrFuncs.recover(diffIbf, servLost, session.challenge, session.sesKey.key.n, session.g)
    et.endTimer(pName, "recover")
        
    if L== None:
        et.changeTimerLabel(pName, "recover", "recover-fail")
        print "Failed to recover"
        return ("Exiting Failed Recovery...", TT, et) 
        
    for blk in L:
        print blk.getDecimalIndex()
      
    print "check"
    return ("Exiting Recovery...", TT, et)

def processClientMessages(incoming, session, lostNum=None):
    
    cpdrMsg = MU.constructCloudPdrMessageNet(incoming)
    
    if cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.INIT_ACK:
        print "Processing INIT-ACK"
        lostMsg = MU.constructLossMessage(lostNum, session.cltId)
        return lostMsg
        
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.LOSS_ACK:
        print "Processing LOSS_ACK"
        
        session.challenge = session.sesKey.generateChallenge()
        challengeMsg = MU.constructChallengeMessage(session.challenge, session.cltId)
        return challengeMsg    
    
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.PROOF:
        print "Received Proof"
        res = processServerProof(cpdrMsg, session)
        return res



def saveTagsForLater(TagTimes, Tags, sKey, bNum, bSz):
    
    stfl = CloudPdrMessages_pb2.SaveTagsForLater()
    stfl.key = "toAFile"
    stfl.bNum = bNum
    bSz = bSz/8
    stfl.bSz = bSz
    maxTime = 0
    for k,v in TagTimes.items():
        if k.endswith("_tag") and maxTime < v:
            maxTime = TagTimes[k]
    stfl.ctime = maxTime
    for i,t in Tags.items():
        stfl.index.append(i)
        stfl.tags.append(str(t))
        if i == 0:
            print t
    stfl = stfl.SerializeToString()
    fName = "tags/tags_%s_%s.dat" % (str(bNum),str(bSz))
    f = open(fName, "w")
    f.write(stfl)
    f.close()
    fName = "tags/key_%s_%s.dat" % (str(bNum),str(bSz))
    f = open(fName, "w")
    cPickle.dump(sKey, f)
    f.close()


def loadTagsFromDisk(tagFile):
    storedTags = CloudPdrMessages_pb2.SaveTagsForLater()
    f = open(tagFile)
    storedTags.ParseFromString(f.read())
    f.close()
    
    #storedKey = cPickle.loads(str(storedTags.key))
    taggingTime = float(storedTags.ctime)
    
    tags = {}
    for i in storedTags.index:
        tags[int(i)] = str(storedTags.tags[int(i)])
        if i == 0:
            print tags[i]
    diskKeyName = tagFile.replace("/tags","/key")
    f=open(diskKeyName)
    storedKey = cPickle.load(f)
    return (tags, storedKey, taggingTime)
    


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
    p.add_argument('--tagmode', dest="tagMode", action='store', help='Tag Mode', type=bool, default=False)
    p.add_argument('--tagload', dest="tagload", action='store', default=None, 
                   help='load tags/keys from location')
    p.add_argument('--dt', dest="dt", action='store', type=int, default=0, help='Type of delta')
   
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
        
    #Generate client id
    cltId = produceClientId()
       
   
    #Create current session
    pdrSes = PdrSession(cltId)
    
    #Read the generator from File
    fp = open(args.genFile, "r")
    g = fp.read()
    g = long(g)
    fp.close() 
    pdrSes.addG(g)
    
    
    loadedTags = None
    loadedKey = None
    loadedTagTime = None
    doNotComputeTags = False
    
    if args.tagload != None:
        print "LOADING"
        loadedTags, loadedKey, loadedTagTime = loadTagsFromDisk(args.tagload)
        doNotComputeTags = True
    #Generate key class
    if doNotComputeTags == True:
        pdrSes.sesKey = CloudPDRKey(args.n, g, loadedKey)
    else:
        pdrSes.sesKey = CloudPDRKey(args.n, g, RSA.generate(args.n))
    
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
    
#     ibfLength =  floor(log(fs.numBlk,2))
    log2Blocks = log(fs.numBlk, 2)
    log2Blocks = floor(log2Blocks)
    delta = int(log2Blocks) 
    if args.dt == 1:
        delta = int(floor(sqrt(fs.numBlk))) 
    
    ibfLength = ((args.hashNum+1)*delta)
    ibfLength = int(ibfLength)
    pdrSes.addibfLength (ibfLength)
    
    
    
    #fs, fsFp = BlockEngine.getFsDetailsStream(args.blkFp)
    totalBlockBytes = fs.pbSize*fs.numBlk
    bytesPerWorker = (args.task*totalBlockBytes)/ fs.numBlk
    
    pdrSes.addFsInfo(fs.numBlk, fs.pbSize, fs.datSize, int(fsSize), 
                     bytesPerWorker, args.workers, args.blkFp, ibfLength, args.hashNum)
    
    genericManager = mp.Manager()
    pdrManager = IbfManager()
    InsertLock = mp.Lock()
    
    blockByteChunks = genericManager.Queue(args.workers)
    W = genericManager.dict()
    T = genericManager.dict()
    TT = genericManager.dict()
    
    pdrManager.start()
    ibf = pdrManager.Ibf(args.hashNum, ibfLength)
    try:      
        ibf.zero(fs.datSize)
    except OSError:
        p = psutil.Process(os.getpid())
        p.get_open_files()
    
    zmqContext =  zmq.Context()
    publisherAddress = "tcp://127.0.0.1:9998"
    sinkAddress = "tcp://127.0.0.1:9999"
    
    publishSocket = zmqContext.socket(zmq.PUB)
    publishSocket.bind(publisherAddress)
    
    sinkSocket = zmqContext.socket(zmq.REP)
    sinkSocket.bind(sinkAddress)
    

    workersPool = []
    
    cellAssignments = BE.chunkAlmostEqual(range(ibfLength), args.workers)
    blocksAssignments = BE.chunkAlmostEqual(range(fs.numBlk), args.workers)

    
    
    for w,cellsPerW,blocksPerW in zip(xrange(args.workers), cellAssignments, blocksAssignments):
        print "worker",  w, "cells", len(cellsPerW), "Blocks", len(blocksPerW)
        p = mp.Process(target=preprocWorker,
                       args=(publisherAddress, sinkAddress, cellsPerW, 
                             args.hashNum, ibfLength, fs.datSize,
                             secret, public, True, 
                             blocksPerW, True, w))
        p.start()
        workersPool.append(p)
    
        
    print "Waiting to establish workers"
    time.sleep(5)
    
    blockStep = 0
    while True:
        dataChunk = fp.read(bytesPerWorker)
        if dataChunk:
            for blockPBItem in BE.chunks(dataChunk, fs.pbSize):
                block = BE.BlockDisk2Block(blockPBItem, fs.datSize)
                bIndex = block.getDecimalIndex()
                job = {'index':bIndex, 'block':block}
                job = cPickle.dumps(job)
                publishSocket.send_multipart(['work', job])
                blockStep+=1
                if (blockStep  % 100000) == 0:
                    print "Dispatched ", blockStep, "out of", fs.numBlk
                #    time.sleep(10)
                
                
                
        else:
            publishSocket.send_multipart(["end"])
            break
        
    
    work = []
    print 'Waiting'
    while len(work) != args.workers:
            w = sinkSocket.recv_pyobj()
            sinkSocket.send("ACK")
            work.append(w)
            if len(work) == len(workersPool):
                print 'Break'
                   
        
    
    for i in work:
        
        print i["worker"], i["blocksExamined"]
        #i = cPickle.loads(i[1])
        #x = i["timers"].getTotalTimer(i["worker"], "ibf")
        #if maxIbf < x:
        #    maxIbf = x
        
    for worker in workersPool:
        worker.join()
        worker.terminate()
        
    
    sys.exit(0)
    ##################
    pool = []
    for i in xrange(args.workers):
        p = mp.Process(target=workerTask, args=(blockByteChunks,W,T,ibf,fs.pbSize,fs.datSize,secret,public, TT, doNotComputeTags, InsertLock))
        p.start()
        pool.append(p)
    
    while True:
        chunk = fp.read(bytesPerWorker)
        if chunk:
            blockByteChunks.put(chunk)
        else:
            for j in xrange(args.workers):
                blockByteChunks.put("END")
            break
    
    for p in pool:
        p.join()
        
    for p in pool:
        p.terminate()
        
        
    fp.close()
    if doNotComputeTags == True:
        T =  loadedTags
     
    
    if args.tagMode == True:
        print "TAGMODE TRUE"
        saveTagsForLater(TT, T, pdrSes.sesKey.key, fs.numBlk, fs.datSize)
    
    pdrSes.addState(ibf)
    pdrSes.W = W
    
    
        
    pdrSes.addDelta(delta)

    sizeTag = getsizeofDictionary(T)

    initMsg = MU.constructInitMessage(pubPB, args.blkFp,
                                               T, cltId, args.hashNum, delta, fs.numBlk, args.runId)

    #ip = "10.109.173.162"
    ip = "127.0.0.1"
   # ip = '192.168.1.8'
   
    
    clt = RpcPdrClient(zmqContext)    
    print "Sending Initialization message"
    initAck = clt.rpc(ip, 9090, initMsg) 
    print "Received Initialization ACK"
    
    
    lostMsg = processClientMessages(initAck, pdrSes, args.lostNum)
    print "Sending Lost message"
    lostAck = clt.rpc(ip, 9090, lostMsg)
    print "Received Lost-Ack message"
    
    
    challengeMsg = processClientMessages(lostAck, pdrSes)
    print "Sending Challenge message"
    proofMsg = clt.rpc(ip, 9090, challengeMsg)
    print "Received Proof message"
    result, proofParallelTimers, proofSequentialTimer  = processClientMessages(proofMsg, pdrSes)
    
    zmqContext.term()
    
    run_results = {}
    
    for k in TT.keys():
        key = k[k.index("_")+1:]
        if key not in run_results.keys():
            run_results[key] = 0
        if TT[k] >  run_results[key]:
            run_results[key] = TT[k]
        
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
    if doNotComputeTags == True:
        run_results["tag"] = loadedTagTime
    
    fp = open(args.runId, "a+")
    for k,v in run_results.items():
        fp.write(k.ljust(20)+"\t"+str(v).ljust(20)+"\n")
    fp.close()
    
    
    
    
    
    
    
    
if __name__ == "__main__":
    main()
