import BlockEngine as BE
import MessageUtil as MU
from datetime import datetime
import random
from CryptoUtil import pickPseudoRandomTheta
from Crypto.Util import number
from Ibf import Ibf
import itertools
import numpy as np
import multiprocessing as mp
from math import floor, log
import CloudPdrMessages_pb2
import struct
from PdrManager import IbfManager, QSetManager
from ExpTimer import ExpTimer
import gmpy2
import psutil
import os

def proofWorkerTask(inputQueue, blkPbSz, blkDatSz, chlng, lost, T, lock, cVal, N, ibf, g, qSets, TT):
    
    
    
    pName = mp.current_process().name
    x = ExpTimer()
    x.registerSession(pName)
    x.registerTimer(pName, "qSet_proof")
    x.registerTimer(pName, "cSumKept")
    x.registerTimer(pName, "cTagKept")
    x.registerTimer(pName, "ibf_serv")
    
    
    while True:
        item = inputQueue.get()
        if item == "END":
            TT[pName+str("_qSet_proof")] = x.getTotalTimer(pName, "qSet_proof")
            TT[pName+str("_cSumKept")] = x.getTotalTimer(pName, "cSumKept") - x.getTotalTimer(pName, "ibf_serv")
            TT[pName+str("_cTagKept")] = x.getTotalTimer(pName, "cTagKept") - x.getTotalTimer(pName, "ibf_serv")
            TT[pName+str("_ibf_serv")] = x.getTotalTimer(pName, "ibf_serv")
            
            
            return
        for blockPbItem in BE.chunks(item,blkPbSz):
            block = BE.BlockDisk2Block(blockPbItem, blkDatSz)
            bIndex = block.getDecimalIndex()
            if bIndex in lost:
                x.startTimer(pName, "qSet_proof")
                binBlockIndex = block.getStringIndex()
                indices = ibf.getIndices(binBlockIndex, True)
                for i in indices:
                    with lock:
                        qSets.addValue(i, bIndex)
                
                x.endTimer(pName, "qSet_proof")    
                del block
                continue
            x.startTimer(pName, "cSumKept")
            x.startTimer(pName, "cTagKept")
            aI = pickPseudoRandomTheta(chlng, block.getStringIndex())
            aI = number.bytes_to_long(aI)
            bI = number.bytes_to_long(block.data.tobytes())
            
          
            
            
            with lock:
                x.startTimer(pName, "ibf_serv")
                ibf.insert(block, chlng, N, g, True)
                x.endTimer(pName, "ibf_serv")
                cVal["cSum"] += (aI*bI)
                x.endTimer(pName,"cSumKept")
                cVal["cTag"] *= gmpy2.powmod(T[bIndex], aI, N)
                cVal["cTag"] = gmpy2.powmod(cVal["cTag"],1,N)
                x.endTimer(pName,"cTagKept")
            del block    
                


class ClientSession(object):
    
    WORKERS = 4
    BLOCK_INDEX_LEN=32
    BLOCKS_PER_WORKER=20
    
    def __init__(self, N, g, tagMsg, delta, k, fs, blkNum, runId):
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
        
    def addClientChallenge(self, challenge):
        self.challenge = str(challenge)
     
    def chooseBlocksToLose(self, lossNum):
        self.lost = random.sample(xrange(self.fsBlocksNum), lossNum)
     
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
        pdrManager = IbfManager()
        qSetManager = QSetManager()
        blockBytesQueue = mp.Queue(self.WORKERS)
        TT = gManager.dict()
        combinedLock = mp.Lock()
        combinedValues = gManager.dict()
        combinedValues["cSum"] = 0L
        combinedValues["cTag"] = 1L
        
        
        pdrManager.start()
        qSetManager.start()
        
        ibf = pdrManager.Ibf(self.k, ibfLength)
        try:      
            ibf.zero(fsMsg.datSize)
        except OSError as e:
            p = psutil.Process(os.getpid())
            p.get_open_files()
            
        
        qSets = qSetManager.QSet()
        
        workerPool = []
        for i in xrange(self.WORKERS):
            p = mp.Process(target=proofWorkerTask,
                           args=(blockBytesQueue, fsMsg.pbSize, 
                                 fsMsg.datSize, self.challenge, self.lost,
                                 self.T, combinedLock, 
                                 combinedValues, self.clientKeyN, 
                                 ibf, self.clientKeyG, qSets,TT))
                           
            p.start()
            workerPool.append(p)
        
        while True:
            chunk = fp.read(bytesPerWorker)
            if chunk:
                blockBytesQueue.put(chunk)
            else:
                for j in xrange(self.WORKERS):
                    blockBytesQueue.put("END")
                break
        
        for p in workerPool:
            p.join()
        
        for p in workerPool:
            p.terminate()    
        
        fp.close()
        #print "combinedTag", combinedValues["cTag"]
        #print "combinedSum", combinedValues["cSum"]
     
        qS = qSets.qSets()
        et.startTimer(pName, "cmbLost")
        combinedLostTags = {}
        for k in qS.keys():
            print "Position:",  k
            val = qS[k]
            
            if k not in combinedLostTags.keys():
                combinedLostTags[k] = 1
                 
            for v in val:
                print "Indices in Qset", v
                binV  = ibf.binPadLostIndex(v)
                aBlk = pickPseudoRandomTheta(self.challenge, binV)
                aI = number.bytes_to_long(aBlk)
                lostTag=gmpy2.powmod(self.T[v], aI, self.clientKeyN)
                combinedLostTags[k] = gmpy2.powmod((combinedLostTags[k]*lostTag), 1, self.clientKeyN)
    

        et.endTimer(pName, "cmbLost")
        ibfCells = ibf.cells()
        proofMsg = MU.constructProofMessage(combinedValues["cSum"],
                                            combinedValues["cTag"],
                                            ibfCells, 
                                            self.lost ,
                                            combinedLostTags)

#         et, TT          
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
