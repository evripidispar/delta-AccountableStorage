from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Cell import Cell
import sys

class Ibf(object):
	
	BLOCK_INDEX_LEN=32

	def __init__(self, k, m):
		self.k = k
		self.m = m
		self.cells = {}
		self.HashFunc = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]
		
	def setCells(self, cells):
		self.cells = cells

	#def setCellsFromList(self, cellList):
	#	counter = 0
	
	
	def binPadLostIndex(self, lostIndex):
		binLostIndex = "{0:b}".format(lostIndex)
		pad = self.BLOCK_INDEX_LEN-len(binLostIndex)
		binLostIndex = pad*'0'+binLostIndex
		return binLostIndex 

	@staticmethod
	def getIndices(k, m, hashFunc, block,isIndex=False, cellsAssignment=None):
		indices = []
		if isIndex == False:
			blockIndex = block.getStringIndex()
		else:
			blockIndex = block #Cases coming from the proof part of the algorithm
			
		for i in range(k):
			hashIndexVal = hashFunc[i](blockIndex)
			indices.append(hashIndexVal % m)
			
		if cellsAssignment != None:
			return [i for i in indices if i in set(cellsAssignment)]
		return indices

	def getCells(self):
		return self.cells

	def setSingleCell(self, index , cell):
		self.cells[index] = cell


	def getRangedCells(self, start, end):
		c = []
		for i in xrange(start,end):
			if i in self.cells.keys():
				c.append((i,self.cells[i]))
		return c
	
	def getK(self):
		return self.k
	
	def getM(self):
		return self.m

	def zero(self,  dataBitSize):
		for cellIndex in xrange(self.m):
			self.cells[cellIndex] = Cell(0, dataBitSize)

	def insert(self, block, secret, N, g, isHashProdOne=False):
		blockIndices = self.getIndices(self.k, self.m,  self.HashFunc, block)
		for i in blockIndices:
			self.cells[i].add(block, secret, N, g, isHashProdOne)
			

		
	def delete(self, block, secret, N, g, selfIndex=-1):
		blockIndices =  self.getIndices(self.k, self.m, self.HashFunc, block)
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
			try:
				newIbf.cells[cIndex]= self.cells[cIndex].subtract(otherIbf.cells[cIndex],dataByteSize, N, isHashProd)
			except KeyError:
				print "cIndex", cIndex, "m", self.m
				sys.exit(0)
		return newIbf

	def getPureCells(self):
		pureCells = []
		for key in self.cells.keys():
			if self.cells[key].isPure():
				pureCells.append(key)
		return pureCells


	def findBlock(self,block):
		indices = self.getIndices(self.k, self.m, self.HashFunc, block)
		for i in indices:
			if self.cells[i].isEmpty():
				return False
		return True

	def generateIbfFromProtobuf(self, ibfPbuf, dataBitSize, k=0, m=0):
		
		if k == 0:
			k = self.k
		if m == 0:
			m = self.m
			
		newIbf = Ibf(k, m)
		newIbf.zero(dataBitSize)
		for c in ibfPbuf.cells:
			realCell = Cell(0,0)
			realCell.cellFromProtobuf(c.count, c.hashprod, c.data)
			newIbf.cells[c.cellIndex] = realCell
		return newIbf
	
	
