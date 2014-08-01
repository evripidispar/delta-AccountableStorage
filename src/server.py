import argparse
import MessageUtil as MU
import zmq
import CloudPdrMessages_pb2
from ClientSession import ClientSession
from multiprocessing import cpu_count
clients = {}

def processInitMessage(cpdrMsg, context, workersNum, storeBlocks=None):
    
    print "Processing Init Message"
    cltName = cpdrMsg.cltId
    if cltName not in clients.keys():
        N = long(cpdrMsg.init.pk.n)
        g = long(cpdrMsg.init.pk.g)
        delta = cpdrMsg.init.delta
        k = cpdrMsg.init.k
        fs = cpdrMsg.init.filesystem
        blkNum = cpdrMsg.init.fsNumBlocks
        runId = cpdrMsg.init.runId
        clients[cltName] = ClientSession(N, g, cpdrMsg.init.tc, delta, k, fs, blkNum, runId, context, workersNum)
        
    initAck = MU.constructInitAckMessage()
    return initAck

def processChallenge(cpdrMsg):
     
    if cpdrMsg.cltId in clients.keys():
        chlng = cpdrMsg.chlng.challenge
        if len(cpdrMsg.chlng.testIndices):
            clients[cpdrMsg.cltId].addClientChallenge(chlng, cpdrMsg.chlng.testIndices)
        else:
            clients[cpdrMsg.cltId].addClientChallenge(chlng)
        proofMsg  = clients[cpdrMsg.cltId].produceProof(cpdrMsg.cltId)
        return proofMsg

def processLostMessage(cpdrMsg):
    
    print "Processing Lost Message"
    lossNum = cpdrMsg.lost.lossNum
    if cpdrMsg.cltId in clients.keys():
        clients[cpdrMsg.cltId].chooseBlocksToLose(lossNum)
    
    #Just generate a loss ack
    lossAck = MU.constructLostAckMessage()
    return lossAck

def procMessage(incoming, context, workersNum):
    
    print "Processing incoming message..."
    
    cpdrMsg = MU.constructCloudPdrMessageNet(incoming)
    
    
    if cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.INIT:
        initAck = processInitMessage(cpdrMsg, context, workersNum)
        return initAck
    
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.LOSS:
        lossAck = processLostMessage(cpdrMsg)
        return lossAck
    
    elif cpdrMsg.type == CloudPdrMessages_pb2.CloudPdrMsg.CHALLENGE:
        print "Incoming challenge"
        proof = processChallenge(cpdrMsg)
        return proof
    
    
        
        
def serve(port, workersNum):
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:"+str(port))

    while True:
        msg = socket.recv()
        outMessage = procMessage(msg, context, workersNum)
        socket.send(outMessage)

def main():
    
    p = argparse.ArgumentParser(description='CloudPDR Server')

    p.add_argument('-p', dest='port', action='store', default=9090,
                   help='CloudPdr server port')

    
    p.add_argument('-w', dest='workersNum', action='store', default=2, type=int,
                   help='Number of workers')

    
    args = p.parse_args()
    args.workersNum = cpu_count()-1
    serve(args.port, args.workersNum)

if __name__ == "__main__":
    main()


        
    
