import sys
import CloudPdrMessages_pb2
import BlockUtil
import argparse
import datetime
from Block import Block
from bitarray import bitarray
import struct
from ExpTimer import ExpTimer
import copy


TEST = False

def getReadFactor(blockNum):
    
    if blockNum > 10000:
        return blockNum*0.02
    else:
        return blockNum

def createBlocks(blocksNum, blockSize):
    blocks = BlockUtil.blockCreatorMemory(blocksNum, blockSize)
    return blocks

def createBlockProtoBufs(blocks, blockSize):
    print "Creating protocol buffers...."
    blockCollection = CloudPdrMessages_pb2.BlockCollection()
    blockCollection.blockBitSize = blockSize*8
    for b in blocks:
        pbufBlock = blockCollection.blocks.add()
        pbufBlock.index = b.getStringIndex()
        pbufBlock.data = b.getData().to01()

    return blockCollection


def createBlockProtoBufsDisk(blocks, blockSize):
    blockCollection = CloudPdrMessages_pb2.BlockCollectionDisk()
    blockCollection.blockBitSize = blockSize*8
    for b in blocks:
        pbfBlk = blockCollection.collection.add()
        pbfBlk.blk = b.data.tobytes()
        
    return blockCollection


def readBlockCollectionFromDisk(filename):
    print "Reading block collection from disk (", filename, ")"
    bc = CloudPdrMessages_pb2.BlockCollectionDisk()
    fp = open(filename,"rb")
    bc.ParseFromString(fp.read())
    fp.close()
    return bc

def writeBlockCollectionToFile(filename, blkCollection):
    print "Writing Block Collection to File"
    fp = open(filename, "wb")
    fp.write(blkCollection.SerializeToString())
    fp.close()

def readBlockCollectionFromFile(filename):
    print "Reading Block collection from File"
    blockCollection = CloudPdrMessages_pb2.BlockCollection()
    fp = open(filename, "rb")
    blockCollection.ParseFromString(fp.read())
    fp.close()
    return blockCollection

def listBlocksInCollection(blocks):
    for blk in blocks:
        print blk.getDecimalIndex()

def blockCollectionDisk2BlockObject(blockCollection):
    b = []
    bSize = blockCollection.blockBitSize
    for i in blockCollection.collection:
        bObj = Block(0,bSize, True)
        bObj.buildBlockFromProtoBufDisk(i.blk)
        b.append(bObj)
    return b

def blockCollection2BlockObject(blockCollection):
    b = []
    bSize = blockCollection.blockBitSize
    for blk in blockCollection.blocks:
        bObj = Block(0,0)
        bObj.buildBlockFromProtoBuf(blk.index, blk.data, bSize) 
        b.append(bObj)
    return b


### # # # # # Filesystem functions  ## # # # # # # # # ##  ## 
BINDEX_LEN = 32

def getPaddedBlockId(blockId):
        bit_id = "{0:b}".format(blockId)
        id_len = BINDEX_LEN - len(bit_id)
        bit_id ='0'*id_len+bit_id
        index=bitarray()
        index.extend(bit_id)
        return index.tobytes()
        

def createWriteFilesystem2Disk(blkNum, blkSz, indexSize, filename):
   
    fs = CloudPdrMessages_pb2.Filesystem()
    fs.numBlk = blkNum
    fs.index = indexSize
    fs.datSize = blkSz*8
    
    fp = open(filename, "wb")
    for i in xrange(blkNum):
        if i == 0:
            blk = BlockUtil.createSingleBlock(blkSz)
            pseudoData = copy.deepcopy(blk)
        else:
            blk = BlockUtil.createSingleBlock(blkSz, pseudoData, 8)
            
        blkPbf = CloudPdrMessages_pb2.BlockDisk()
        
        blkPbf.index= getPaddedBlockId(i)
        blkPbf.dat= (BlockUtil.npArray2bitArray(blk)).tobytes()
        blkPbf = blkPbf.SerializeToString()
        if i == 0:
            fs.pbSize=len(blkPbf)
            fs = fs.SerializeToString()
            fsLen = len(fs)
            fsLen = struct.pack("i",fsLen)
            fp.write(fsLen)
            fp.write(fs)
            
        fp.write(blkPbf)
        
    fp.close()
    
def getFsDetailsStream(fsFilename):
    fp=open(fsFilename,"rb")
    fsSize = fp.read(4)
    fsSize, = struct.unpack("i", fsSize)
    fs = CloudPdrMessages_pb2.Filesystem()
    fs.ParseFromString(fp.read(int(fsSize)))
    return (fs, fp)

    
def readFileSystem(fsFilename):
    #DEBUG function
    fp = open(fsFilename, "rb")
    fsSize = fp.read(4)
    fsSize, = struct.unpack("i", fsSize)
    
    fs = CloudPdrMessages_pb2.Filesystem()
    fs.ParseFromString(fp.read(int(fsSize)))
    
    print "pbSize", fs.pbSize
    print "numBlk", fs.numBlk
    print "index", fs.index
    print "dataSize", fs.datSize
    
    for i in range(fs.numBlk):
        c = CloudPdrMessages_pb2.BlockDisk()
        
        c.ParseFromString(fp.read(fs.pbSize))
        bb = bitarray()
        bb.frombytes(c.index)
        print bb[0:32]
        
    fp.close()
    
    
def BlockDisk2Block(serialized, blkSz):
    bPbf = CloudPdrMessages_pb2.BlockDisk()
    bPbf.ParseFromString(serialized)
    block = Block(0,blkSz,True)
    block.buildBlockFromProtoBuf(bPbf.index, bPbf.dat)
    return block


def chunks(s, n):
    for start in xrange(0, len(s), n):
        yield s[start:start+n]
        
def chunkAlmostEqual(items, maxbaskets=3, item_count=None):
    item_count = item_count or len(items)
    baskets = min(item_count, maxbaskets)
    items = iter(items)
    floor = item_count // baskets 
    ceiling = floor + 1
    stepdown = item_count % baskets
    for x_i in xrange(baskets):
        length = ceiling if x_i < stepdown else floor
        yield [items.next() for _ in xrange(length)]

def main():
    p = argparse.ArgumentParser(description='Driver')
    p.add_argument('-r', dest='fpR', action='store', default=None,
                   help='File to read Block collection')


    args = p.parse_args()
    readFileSystem(args.fpR)
            
        

if __name__ == "__main__":
    main()
        
