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
from ExpTimer import ExpTimer
import multiprocessing as mp
from TagGenerator import singleTag
from TagGenerator import singleW
import struct
from PdrManager import IbfManager, QSetManager
import gmpy2
import copy

import cPickle
import pprint
import validateServerProofStage
from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Queue import Queue
from Queue import Empty


LOST_BLOCKS = 6

W = {}
Tags = {}
ssss = time.time()
eeee = None

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
    cellsAssignments = BE.chunkAlmostEqual(range(session.fsInfo["ibfLength"]), session.fsInfo["workers"])
    blockAssignments = BE.chunkAlmostEqual(range(session.fsInfo["blockNum"]), session.fsInfo["workers"])
    
    for w,cellsPerW,blocksPerW in zip(xrange(session.fsInfo["workers"]),
                                      cellsAssignments, blockAssignments):
        p = mp.Process(target=validateServerProofStage.worker,
                       args=(session.pubAddr, session.sinkAddr,
                             session.fsInfo["k"], session.fsInfo["ibfLength"],
                             cellsPerW, blocksPerW, servLost, cmbWLock, cmbW,
                             session.challenge, session.W, session.sesKey.key.n ))
    
        p.start()
        workerPool.append(p)
    
    print "Waiting to establish workers"
    time.sleep(5)
    fp = open(session.fsInfo["fsName"], "rb")
    fp.read(4)
    fp.read(session.fsInfo["skip"])
    
    blockStep=0
    while True:
        dataChunk = fp.read(session.fsInfo["bytesPerWorker"])
        if dataChunk:
            for blockPBItem in BE.chunks(dataChunk, session.fsInfo["pbSize"]):
                    block = BE.BlockDisk2Block(blockPBItem, session.fsInfo["blkSz"])
                    bIndex = block.getDecimalIndex()
                    job = {'index':bIndex, 'block': block}
                    job = cPickle.dumps(job)
                    session.pubSocket.send_multipart(["work", job])
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
        eeee = time.time()
        print eeee-ssss
        
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
    
    
    #serverStateIbf = session.ibf.generateIbfFromProtobuf(cpdrProofMsg.proof.serverState,
    #                                         session.fsInfo["blkSz"])
    
    #print session.ibf.m()
    
    serverStateIbf = session.ibf.generateIbfFromProtobuf(cpdrProofMsg.proof.serverState,
                                                 session.fsInfo["blkSz"])
        
    et.registerTimer(pName, "subIbf")
    et.startTimer(pName,"subIbf")
    diffIbf = session.ibf.subtractIbf(serverStateIbf, session.challenge,
                                   session.sesKey.key.n, session.fsInfo["blkSz"], True)
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

def loadPreprocStage(ibfFile):
    fp = open(ibfFile, "rb")
    obj = cPickle.load(fp)
    fp.close()    
    return (obj["ibf"], obj["w"], obj["ibfTime"])

def savePrprocStageForLater(IbfTimes, W, ibf, blockNum, blockSize):
    print "Saving preproc stage for later"
    outputName = "preproc/preproc_%s_%s.data" % (str(blockNum), str(blockSize/8))
    maxIbfTime = 0
    for k,v in IbfTimes.items():
        if k.endswith("_ibf") and maxIbfTime < v:
            maxIbfTime = v
    
    fp = open(outputName,"wb")
    cPickle.dump({"w":W, "ibf":ibf, "ibfTime":maxIbfTime}, fp)
    fp.close()
    
   

    

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
    
    p.add_argument('--tagmode', dest="tagmode", action='store', help='Tag Mode', type=bool, default=False)
    p.add_argument('--tagload', dest="tagload", action='store', default=None, 
                   help='load tags/keys from location')
    
    p.add_argument('--dt', dest="dt", action='store', type=int, default=0, help='Type of delta')
    
    p.add_argument('--preprocmode', dest="preprocMode", action="store_true", help='store Preproc Mode', default=False)
    
    p.add_argument('--preprocload', dest="preprocLoad", action="store", default=None,
                   help='load ibf from ibf/w')
    
   
   
   
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
        print "LOADING Tags"
        loadedTags, loadedKey, loadedTagTime = loadTagsFromDisk(args.tagload)
        doNotComputeTags = True
        pdrSes.T = loadedTags
        
    if doNotComputeTags == True:
        pdrSes.sesKey = CloudPDRKey(args.n, g, loadedKey)
    else:
        pdrSes.sesKey = CloudPDRKey(args.n, g, RSA.generate(args.n))
    
    localIbf = None
    localW = None
    loadedIbfTime = None
    doNotPerformPreproc = False
    if args.preprocLoad != None:
        print "LOADING Stored preprocessing information"
        localIbf, localW, loadedIbfTimes = loadPreprocStage(args.preprocLoad)
        pdrSes.addState(localIbf)
        pdrSes.W = localW
        doNotPerformPreproc = True
    
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
    print args.dt  
    if args.dt == 1:
        delta = int(floor(sqrt(fs.numBlk)))
        args.lostNum = random.choice(range(delta))
    
    ibfLength = ((args.hashNum+1)*delta)
    ibfLength = int(ibfLength)
    pdrSes.addibfLength (ibfLength)
    
    
    
    #fs, fsFp = BlockEngine.getFsDetailsStream(args.blkFp)
    totalBlockBytes = fs.pbSize*fs.numBlk
    bytesPerWorker = (args.task*totalBlockBytes)/ fs.numBlk
    
    pdrSes.addFsInfo(fs.numBlk, fs.pbSize, fs.datSize, int(fsSize), 
                     bytesPerWorker, args.workers, args.blkFp, ibfLength, args.hashNum)
    
    
    #pdrManager = IbfManager()
    #pdrManager.start()
    
    zmqContext =  zmq.Context()
    publisherAddress = "tcp://127.0.0.1:9998"
    sinkAddress = "tcp://127.0.0.1:9999"
    
    publishSocket = zmqContext.socket(zmq.PUB)
    publishSocket.bind(publisherAddress)
    
    sinkSocket = zmqContext.socket(zmq.REP)
    sinkSocket.bind(sinkAddress)
    
    
    
    if doNotPerformPreproc == False:
        workersPool = []
        
        cellAssignments = BE.chunkAlmostEqual(range(ibfLength), args.workers)
        blocksAssignments = BE.chunkAlmostEqual(range(fs.numBlk), args.workers)
    
        for w,cellsPerW,blocksPerW in zip(xrange(args.workers), cellAssignments, blocksAssignments):
            p = mp.Process(target=preprocStage.preprocWorker,
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
                        time.sleep(3)     
            else:
                publishSocket.send_multipart(["end"])
                break
            
        fp.close()
        work = []
        print 'Waiting'
        while len(work) != args.workers:
                w = sinkSocket.recv_pyobj()
                sinkSocket.send("ACK")
                work.append(w)
           
        if doNotComputeTags == False:
            pdrSes.T= {}
    
        pdrSes.W = {}
    
        localIbf = Ibf(args.hashNum, ibfLength)    
        for i in work:
            pdrSes.W.update(i["w"])
            localIbf.cells.update(i["cells"])
            if "tags" in i.keys():
                pdrSes.T.update(i["tags"])
            pdrSes.TT[i["worker"]+str("_tag")] = i["timers"].getTotalTimer(i["worker"], "tag")
            pdrSes.TT[i["worker"]+str("_ibf")] = i["timers"].getTotalTimer(i["worker"], "ibf")
            #print i["worker"], i["blocksExamined"], i["w"].keys(), len(i["w"].keys()), len(pdrSes.W.keys()), len(localIbf.cells.keys()), ibfLength
            #x = i["timers"].getTotalTimer(i["worker"], "ibf")
        pdrSes.addState(localIbf)
        
        for worker in workersPool:
            worker.join()
            worker.terminate()
     
    
    
    pdrSes.addNetInfo(publisherAddress, sinkAddress, publishSocket, sinkSocket)
    
         
    if args.tagmode == True:
        saveTagsForLater(pdrSes.TT, pdrSes.T, pdrSes.sesKey.key, fs.numBlk, fs.datSize)
    
    if args.preprocMode == True:
        savePrprocStageForLater(pdrSes.TT, pdrSes.W, pdrSes.ibf, fs.numBlk, fs.datSize)
    
       
    
    pdrSes.addDelta(delta)
    sizeTag = getsizeofDictionary(pdrSes.T)
    initMsg = MU.constructInitMessage(pubPB, args.blkFp, pdrSes.T,
                                      cltId, args.hashNum, delta,
                                       fs.numBlk, args.runId)

    #ip = "10.109.173.162"
    #ip = '192.168.1.8'
    ip = "127.0.0.1"
   
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
    if doNotComputeTags == True:
        run_results["tag"] = loadedTagTime
    if doNotPerformPreproc == True:
        run_results["ibf"] = loadedIbfTimes
    
    fp = open(args.runId, "a+")
    for k,v in run_results.items():
        fp.write(k.ljust(20)+"\t"+str(v).ljust(20)+"\n")
    fp.close()
    
    
    
    
    
    
    
    
if __name__ == "__main__":
    
    main()
    
