


class PdrSession(object):
    
    INIT=0
    INIT_ACK=1
    CHALLENGE=2
    PROOF=3

    def __init__(self, cltId,key=None, W=None, blocks=None, challenge=None, T=None):
        self.sesKey = key
        self.W = W
        self.blocks = blocks
        self.challenge = challenge
        self.state = self.INIT
        self.cltId = cltId
        self.T = T
        self.TT = {}
        
    def addSecret(self, secret):
        self.secret = secret
    
    def addState(self, ibf):
        self.ibf = ibf
    
    def addDelta(self, delta):
        self.delta = delta
        
    def addG(self, g):
        self.g = g
    
    def addTags(self, T):
        self.T = T
        
    def addDataBitSize(self, dataBitSize):
        self.dataBitSize =  dataBitSize
        
    def addibfLength(self, ibfLength):
        self.ibfLength =  ibfLength
    
    def addFsInfo(self, blockNum, pbSize, blkSz, skip, bPerWorker,
                  workers, filesystem, ibfLength, hashNum):
        self.fsInfo = {}
        self.fsInfo["blockNum"] = blockNum
        self.fsInfo["pbSize"] = pbSize
        self.fsInfo["blkSz"] = blkSz
        self.fsInfo["skip"] = skip
        self.fsInfo["bytesPerWorker"] = bPerWorker
        self.fsInfo["workers"] = workers
        self.fsInfo["fsName"] = filesystem
        self.fsInfo["ibfLength"] = ibfLength
        self.fsInfo["k"] = hashNum
        
        