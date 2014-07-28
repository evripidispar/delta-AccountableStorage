import CloudPdrMessages_pb2
from TagGenerator import tagDict2ProtoBuf
from Ibf import Ibf
'''
    @var pub: public key in protocol buffer format
    @var blks: block collection in protocol buffer format
    @var tags: tag collection in protocol buffer format
'''
def constructInitMessage(pub, filesystem, T, cltId, k, delta, blocksNum, runId):
    initMsg = CloudPdrMessages_pb2.Init()
    initMsg.pk.CopyFrom(pub)
    initMsg.filesystem = filesystem
    for i,t in T.items():
        initMsg.tc.index.append(i)
        initMsg.tc.tags.append(str(t))
        
    initMsg.k = k
    initMsg.delta = delta
    initMsg.fsNumBlocks = blocksNum
    initMsg.runId = runId
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.INIT,
                                       initMsg, None, None, None, cltId)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg


def constructCloudPdrMessage(msgType, init=None, ack=None, 
                             chlng=None, proof=None,
                            cId=None, loss=None, lossAck=None):
    cpdrMsg = CloudPdrMessages_pb2.CloudPdrMsg()
    cpdrMsg.type = msgType
    
    if init != None:
        cpdrMsg.init.CopyFrom(init)
    if ack != None:
        cpdrMsg.ack.CopyFrom(ack)
    if chlng != None:
        cpdrMsg.chlng.CopyFrom(chlng)
    if proof != None:
        cpdrMsg.proof.CopyFrom(proof)
    if cId != None:
        cpdrMsg.cltId = cId
    if loss != None:
        cpdrMsg.lost.CopyFrom(loss)
    if lossAck != None:
        cpdrMsg.lack.CopyFrom(lossAck)
    
    return cpdrMsg
    

def constructCloudPdrMessageNet(data):
    cpdrMsg = CloudPdrMessages_pb2.CloudPdrMsg()
    cpdrMsg.ParseFromString(data)
    return cpdrMsg


def constructInitAckMessage():
    initAck = CloudPdrMessages_pb2.InitAck()
    initAck.ack = True
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.INIT_ACK,
                                     None, initAck)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg

def constructChallengeMessage(challenge, cltId):
    chlng = CloudPdrMessages_pb2.Challenge()
    chlng.challenge = str(challenge)
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.CHALLENGE,
                                       None, None, chlng, None, cltId)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg

def constructLossMessage(lossNum, cId):
    lost= CloudPdrMessages_pb2.Lost()
    lost.lossNum = lossNum
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.LOSS,
                                       None, None, None, None, cId, lost)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg
    

def constructLostAckMessage():
    lostAck = CloudPdrMessages_pb2.LostAck()
    lostAck.ack = True
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.LOSS_ACK,
                                       None, None, None, None, None, None, lostAck)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg


def constructIbfMessage(ibfCells):
    ibfMsg = CloudPdrMessages_pb2.Ibf()
    
    for index,cell in ibfCells.items():
        
        c = ibfMsg.cells.add()
        c.count = cell.count
        c.hashprod = cell.hashProd
        c.data = cell.dataSum.data.to01()
        c.cellIndex = index
    return ibfMsg


def constructLostTagPairsMessage(combinedLostTags):
    lostTagsPairMsg = CloudPdrMessages_pb2.LostTagPairs()
    for k,v in combinedLostTags.items():
        lpair = lostTagsPairMsg.pairs.add()
        lpair.k = k
        lpair.v = str(v)
    return lostTagsPairMsg

def constructProofMessage(combinedSum, combinedTag, ibfCells, lostIndeces, combinedLostTags):
    proof = CloudPdrMessages_pb2.Proof()
    proof.combinedSum = str(combinedSum)
    proof.combinedTag = str(combinedTag)
    
    ibfMsg = constructIbfMessage(ibfCells)
    proof.serverState.CopyFrom(ibfMsg)
    
    for lIndex in lostIndeces:
        proof.lostIndeces.append(lIndex)
    
    lostTagPairs = constructLostTagPairsMessage(combinedLostTags)
    proof.lostTags.CopyFrom(lostTagPairs)
    
    cpdrMsg = constructCloudPdrMessage(CloudPdrMessages_pb2.CloudPdrMsg.PROOF,
                                       None, None, None, proof)
    cpdrMsg = cpdrMsg.SerializeToString()
    return cpdrMsg
