from Ibf import Ibf
from multiprocessing.managers import BaseManager
from multiprocessing.managers import BaseProxy

class IbfProxy(BaseProxy):
    _exposed_=['insert', 'zero', 'getIndices', 'binPadLostIndex', 
               'getCells', 'subtractIbf', 'generateIbfFromProtobuf', 'getRangedCells']
    
    def insert(self,block, secret, N, g, isHashProdOne):
        self._callmethod('insert', (block, secret, N, g, isHashProdOne))
    
    def zero(self, dataBitSize):
        self._callmethod('zero', (dataBitSize,))
    
    def getIndices(self, block, isIndex):
        return self._callmethod('getIndices', (block, isIndex,))
    
    def binPadLostIndex(self, lostIndex):
        return self._callmethod('binPadLostIndex', (lostIndex,))

    def cells(self):
        return self._callmethod('getCells', ())
    
    def rangedCells(self, start, end):
        return self._callmethod('getRangedCells', (start,end))
    
    def subtractIbf(self, otherIbf, secret, N, dataByteSize, isHashProd):
        return self._callmethod('subtractIbf', (otherIbf, secret, N, dataByteSize, isHashProd))
    
    def generateIbfFromProtobuf(self, ibfPbuf, dataBitSize):
        return self._callmethod('generateIbfFromProtobuf', (ibfPbuf, dataBitSize))


class IbfManager(BaseManager):
    pass

IbfManager.register('Ibf', Ibf, proxytype=IbfProxy,)        




class QSet(object):
    def __init__(self):
        self.qSets = {}
    
    def addValue(self, key, value):
        if key not in self.qSets.keys():
            self.qSets[key]=[]
        self.qSets[key].append(value)
    
    def getQSets(self):
        return self.qSets
    
class QSetProxy(BaseProxy):
    _exposed_=['addValue', 'getQSets']
    
    def addValue(self, key, value):
        self._callmethod('addValue', (key, value))
    
    def qSets(self):
        return self._callmethod('getQSets', ())

class QSetManager(BaseManager):
    pass
QSetManager.register('QSet', QSet, proxytype=QSetProxy,)