from bitarray import bitarray
import time
BINDEX_LEN = 32

class Block(object):
	def __init__(self, blockId, dataBitSize, fromDisk=False):
		if fromDisk == False:
			util_id = self.idToBinary(blockId)
			id_len = BINDEX_LEN - len(util_id)
			self.data = bitarray(id_len*'0')
			self.data.extend(util_id)
			self.data.extend(dataBitSize*'0')
		self.dataBitsize = dataBitSize

	def buildBlockFromProtoBuf(self, index, data):
		self.data = bitarray()
		self.data.frombytes(index)
		self.data.frombytes(data)
			
	def buildBlockFromProtoBufDisk(self, data):
		self.data = bitarray()
		self.data.frombytes(data)


	def idToBinary(self, blockId):
		bit_id = "{0:b}".format(blockId)
		return bit_id

	def setBlockData(self, blockData):
		self.data = blockData.data
	
	def setRandomBlockData(self, blockData):
		self.data.extend(blockData)

	def addBlockData(self, otherBlock):
		assert self.data.length() == otherBlock.data.length()
		self.data = self.data ^ otherBlock.data

	def getIndex(self):
		return self.data[0:BINDEX_LEN]

	def getIndexBytes(self):
		return self.data[0:BINDEX_LEN].tobytes()

	def getData(self):
		return self.data[BINDEX_LEN:]

	def getWholeBlockBitArray(self):
		return self.data

	def getDecimalIndex(self):
		return int(self.getStringIndex(), 2)
	
	def getStringIndex(self):
		index = self.data[0:BINDEX_LEN]
		indexStr = index.to01()
		return indexStr
	
	def isZeroDataSum(self):
		zero = bitarray((BINDEX_LEN+self.dataBitsize)*'0')
		if zero == self.data:
			return True
		return False
	
