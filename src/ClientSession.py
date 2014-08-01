import BlockEngine as BE
import MessageUtil as MU
from datetime import datetime
import random
from CryptoUtil import pickPseudoRandomTheta
from Crypto.Util import number
from Ibf import Ibf
import itertools
import multiprocessing as mp
import CloudPdrMessages_pb2
import struct
from ExpTimer import ExpTimer
import gmpy2
import zmq
import serverProofStage
import time
import cPickle
import pprint

class ClientSession(object):
    
    WORKERS = 4
    BLOCK_INDEX_LEN=32
    BLOCKS_PER_WORKER=20
    
    def __init__(self, N, g, tagMsg, delta, k, fs, 
                 blkNum, runId, context, numWorkers):
        self.clientKeyN = N
        self.clientKeyG = g
        self.T = {}
        self.challenge=None
        self.blocks = None
        self.blkLocalDrive=""
        self.lost=None
        self.delta = delta
        self.k = k
        self.filesystem = fs
        self.fsBlocksNum = blkNum
        self.populateTags(tagMsg)
        self.runId = str(runId)
        self.context = context
        self.numWorkers = numWorkers
        
        
    def populateTags(self, tagMsg):
        
        iters = itertools.izip(tagMsg.index,tagMsg.tags)
        for index,tag in iters:
            self.T[index]=long(tag)
        
    
    def storeBlocksInMemory(self, blocks, blockBitSize):
        self.blocks = blocks
        self.ibfLength = int(self.delta *(self.k+1)) 
        self.blockBitSize = blockBitSize
    
    def storeBlocksInDisk(self, blockCollection):
        self.blkLocalDrive="cblk"+str(datetime.now())
        self.blkLocalDrive = self.blkLocalDrive.replace(" ", "_")
        BE.writeBlockCollectionToFile(self.blkLocalDrive, blockCollection)
    
    def storeBlocksS3(self, blockCollection):
        print "S3"
        
    def addClientChallenge(self, challenge, testIndicies=None):
        self.challenge = str(challenge)
        if testIndicies != None:
            self.randomBlocksToTest = set(testIndicies)
        else:
            self.randomBlocksToTest  = None
        #if len(self.randomBlocksToTest) > 0:
        #    self.lost=self.lost.intersection(self.randomBlocksToTest)
     
    def chooseBlocksToLose(self, lossNum):
        self.lost = set(random.sample(xrange(self.fsBlocksNum), lossNum))
     
    def produceProof(self, cltId):
        
        pName = self.runId
        et = ExpTimer()
        et.registerSession(pName)
        et.registerTimer(pName, "cmbLost")
        
        fp = open(self.filesystem, "rb")
        fsSize = fp.read(4)
        fsSize,  = struct.unpack("i", fsSize)
        fsMsg = CloudPdrMessages_pb2.Filesystem()
        fsMsg.ParseFromString(fp.read(int(fsSize)))
        
        ibfLength = ((self.k+1)*self.delta)
        ibfLength = int(ibfLength)

        totalBlockBytes = fsMsg.numBlk * fsMsg.pbSize
        bytesPerWorker = (self.BLOCKS_PER_WORKER*totalBlockBytes) / fsMsg.numBlk
                
        gManager = mp.Manager()
        
        combinedLock = mp.Lock()
        combinedValues = gManager.dict()
        combinedValues["cSum"] = 0L
        combinedValues["alive"] = 0L
        combinedValues["alive_count"] = 0L
        combinedValues["all"] = 0L
        combinedValues["all_count"] = 0L
        combinedValues["cTag"] = 1L
        
        TT = {}
        
        publisherAddress = "tcp://127.0.0.1:7878"
        sinkAddress = "tcp://127.0.0.1:7979"
        

        publishSocket = self.context.socket(zmq.PUB)
        publishSocket.bind(publisherAddress)
        
        sinkSocket = self.context.socket(zmq.REP)
        sinkSocket.bind(sinkAddress)
        
        cellAssignments = list(BE.chunkAlmostEqual(range(ibfLength), self.numWorkers))
        blockAssignments = list(BE.chunkAlmostEqual(range(fsMsg.numBlk), self.numWorkers))
        workersPool = []
        
        print self.numWorkers
        for w,cellsPerW,blocksPerW in zip(xrange(self.numWorkers),
                                          cellAssignments, blockAssignments):
            p = mp.Process(target=serverProofStage.serverProofWorker,
                           args=(publisherAddress, sinkAddress,
                                  cellsPerW, blocksPerW, self.challenge,
                                  self.lost, self.T, combinedLock, 
                                  combinedValues, self.clientKeyN,
                                  self.clientKeyG, self.k, ibfLength,
                                  fsMsg.datSize, self.randomBlocksToTest))
            p.start()
            workersPool.append(p)
        
        print "Waiting to establish workers"
        time.sleep(5)
        blockStep = 0
        while True:
            dataChunk = fp.read(bytesPerWorker)
            if dataChunk:
                for blockPBItem in BE.chunks(dataChunk, fsMsg.pbSize):
                    block = BE.BlockDisk2Block(blockPBItem, fsMsg.datSize)
                    bIndex = block.getDecimalIndex()
                    job = {'index':bIndex, 'block':block}
                    job = cPickle.dumps(job)
                    publishSocket.send_multipart(['work', job])
                    blockStep+=1
                    
                    if blockStep % 100000 == 0:
                        print "Dispatched ", blockStep, "out of", fsMsg.numBlk
                        time.sleep(2)
            else:
                publishSocket.send_multipart(['end'])
                break
        
        fp.close()
        work = []
        print "Waiting to gather results from ", self.numWorkers
        while len(work) != self.numWorkers:
            w = sinkSocket.recv_pyobj()
            sinkSocket.send("ACK")
            work.append(w)
            
         
        serverIbf = Ibf(self.k, ibfLength)
        qS = {}
        for i in work:
            serverIbf.cells.update(i["cells"])
            for k,v in i["qSets"].items():
                if k not in qS.keys():
                    qS[k] = []
                qS[k] += v
                
            TT[i["worker"]+str("_qSet_proof")] = i["timers"].getTotalTimer(i["worker"], "qSet_proof")                         
            TT[i["worker"]+str("_ibf_serv")] = i["timers"].getTotalTimer(i["worker"], "ibf_serv")
            TT[i["worker"]+str("_cSumKept")] = i["timers"].getTotalTimer(i["worker"], "cSumKept") 
            TT[i["worker"]+str("_cTagKept")] = i["timers"].getTotalTimer(i["worker"], "cTagKept") 
            
        #print "combinedTag", combinedValues["cTag"]
        pprint.pprint(['All', combinedValues["all"]])
        pprint.pprint(['All count', combinedValues["all_count"]])
        pprint.pprint(['Alive', combinedValues["alive"]])
        pprint.pprint(['Alive_count', combinedValues["alive_count"]])
    
        
        pprint.pprint(["Lost", len(self.lost)])
        pprint.pprint(self.lost)
        for w in workersPool:
            w.join()
            w.terminate()
      
        et.startTimer(pName, "cmbLost")
        combinedLostTags = {}
        for k in qS.keys():
            #print "Position:",  k
            val = qS[k]
            
            if k not in combinedLostTags.keys():
                combinedLostTags[k] = 1
                 
            for v in val:
                #print "Indices in Qset", v
                binV  = serverIbf.binPadLostIndex(v)
                aBlk = pickPseudoRandomTheta(self.challenge, binV)
                aI = number.bytes_to_long(aBlk)
                lostTag=gmpy2.powmod(self.T[v], aI, self.clientKeyN)
                combinedLostTags[k] = gmpy2.powmod((combinedLostTags[k]*lostTag), 1, self.clientKeyN)
    

        
        et.endTimer(pName, "cmbLost")
        
        proofMsg = MU.constructProofMessage(combinedValues["cSum"],
                                            combinedValues["cTag"],
                                            serverIbf.cells, 
                                            self.lost ,
                                            combinedLostTags)
 
        run_results = {}
        run_results['proof-size'] = len(proofMsg)
        for k in TT.keys():
            key = k[k.index("_")+1:]
            if key not in run_results.keys():
                run_results[key] = 0
            if TT[k] >  run_results[key]:
                run_results[key] = TT[k]
         
    
        
        pName = et.timers.keys()[0]
        for k in et.timers[pName].keys():
            if 'total' in k:
                s = k[0:k.index('total')-1]
                run_results[s] = et.timers[pName][k]
    
        fp = open(self.runId+str(".serv"), "a+")
        for k,v in run_results.items():
            #fp.write(k.ljust(20)+"\t"+str(v).ljust(20)+"\n")
            fp.write(k.ljust(20)+"\t"+str(v).ljust(30)+"\n")
        fp.close()
    
        return proofMsg
