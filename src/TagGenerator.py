from Crypto.Util import number
from Crypto.Hash import SHA256
from CloudPdrMessages_pb2 import TagCollection
import gmpy2

class TagGenerator(object):
    '''
    Class to generate tags from blocks
    '''
    
    def __init__(self):
        print ""
    
    def getW(self, blocks, u):
        w_collection = []
        for blk in blocks:
            index = blk.getStringIndex()
            wBlk = str(u) + index
            w_collection.append(wBlk)
        return w_collection

    def getTags(self, w_collection, g, blocks, d, n):
        tags = []
        fp = open("BEFORE","w")
        for (w, b) in zip(w_collection, blocks):
            h = SHA256.new()
            bLong =  number.bytes_to_long(b.data.tobytes())
            powG = gmpy2.powmod(g,bLong, n)
            h.update(str(w))
            wHash = number.bytes_to_long(h.digest())
            fp.write(str(wHash)+"\n")
            
            wGmodN = gmpy2.powmod((wHash*powG),1, n)
            res = gmpy2.powmod(wGmodN, d, n)
            tags.append(res)
        fp.close()
        return tags
        
    
    def createTagProtoBuf(self, tags):
        tc = TagCollection()
        for tag in tags:
            tc.tags.append(str(tag))
        return tc
    
    
def singleW(block, u):
    wBlk = str(u)+block.getStringIndex()
    return wBlk

def singleTag(w, block, g, d, n):
        h = SHA256.new()
        bLong = number.bytes_to_long(block.data.tobytes())
        powG = gmpy2.powmod(g,bLong,n)
        h.update(str(w))
        wHash = number.bytes_to_long(h.digest())
        wGmodN = gmpy2.powmod((wHash*powG),1, n)
        tag = gmpy2.powmod(wGmodN, d, n)
        return tag
    


def tagDict2ProtoBuf(T):
    tc = TagCollection()
    for k,v in T.items():
        tc.index.append(k)
        tc.tags.append(str(v))
    return tc
