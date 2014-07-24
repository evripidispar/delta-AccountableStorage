from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Cell import Cell


class Ibf(object):
	
	BLOCK_INDEX_LEN=32

	def __init__(self, k, m):
		self.k = k
		self.m = m
		self.cells = {}
		self.HashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]
		
	def setCells(self, cells):
		self.cells = cells

	def binPadLostIndex(self, lostIndex):
		binLostIndex = "{0:b}".format(lostIndex)
		pad = self.BLOCK_INDEX_LEN-len(binLostIndex)
		binLostIndex = pad*'0'+binLostIndex
		return binLostIndex 

	def getIndices(self, block, isIndex=False):
		indices = []
		if isIndex == False:
			blockIndex = block.getStringIndex()
		else:
			blockIndex = block #Cases coming from the proof part of the algorithm
			
			
		for i in range(self.k):
			hashIndexVal = self.HashFunc[i](blockIndex)
			indices.append(hashIndexVal % self.m)
			
		
		return indices

	def getCells(self):
		return self.cells

	def zero(self,  dataBitSize):
		for cellIndex in xrange(self.m):
			self.cells[cellIndex] = Cell(0, dataBitSize)

	def insert(self, block, secret, N, g, isHashProdOne=False):
		blockIndices = self.getIndices(block)
		for i in blockIndices:
				self.cells[i].add(block, secret, N, g, isHashProdOne)
			

		
	def delete(self, block, secret, N, g, selfIndex=-1):
		blockIndices =  self.getIndices(block)
		for i in blockIndices:
			if i == selfIndex:
				continue
				
			if self.cells[i].isEmpty() == False:
				self.cells[i].remove(block, secret, N, g)
		
		#TODO: super scary
		if selfIndex != -1:
			self.cells[selfIndex].zeroCell()

	def subtractIbf(self, otherIbf, secret, N, dataByteSize, isHashProd=False):
		if self.m != otherIbf.m:
			print "IBFs different sizes"
			return None

		newIbf = Ibf(self.k, self.m)
		for cIndex in range(self.m):
			newIbf.cells[cIndex]= self.cells[cIndex].subtract(otherIbf.cells[cIndex],
															 dataByteSize,
															  N,
															  isHashProd)
		return newIbf

	def getPureCells(self):
		pureCells = []
		for key in self.cells.keys():
			if self.cells[key].isPure():
				pureCells.append(key)
		return pureCells


	def findBlock(self,block):
		indices = self.getIndices(block)
		for i in indices:
			if self.cells[i].isEmpty():
				return False
		return True

	def generateIbfFromProtobuf(self, ibfPbuf, dataBitSize):
		newIbf = Ibf(self.k, self.m)
		newIbf.zero(dataBitSize)
		for c in ibfPbuf.cells:
			realCell = Cell(0,0)
			realCell.cellFromProtobuf(c.count, c.hashprod, c.data)
			newIbf.cells[c.cellIndex] = realCell
		return newIbf
	
	
