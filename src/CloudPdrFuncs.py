from HashFunc import Hash1, Hash2, Hash3, Hash4, Hash5, Hash6
from Ibf import *
from Block import *
import copy

hashFunList = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]



# lostIndeces a list of decimal lost indices

def recover(ibfLost, lostIndices, secret, N, g):
	L = []
	lostPureCells = ibfLost.getPureCells()
	pureCellsNum = len(lostPureCells)
	

	while pureCellsNum > 0:
		cIndex = lostPureCells.pop(0)
		blockIndex =  ibfLost.cells[cIndex].getDataSum().getDecimalIndex()
		
		#print "B-Block Index", blockIndex, len(lostIndices), lostIndices
		if blockIndex not in lostIndices:
			print "Failed: crazy reason"
			return None


		recoveredBlock = copy.deepcopy(ibfLost.cells[cIndex].getDataSum())
		L.append(recoveredBlock)
		
		ibfLost.delete(ibfLost.cells[cIndex].getDataSum(), secret, N, g, cIndex)
		
		
		lostIndices.remove(blockIndex)
		#print "A-Block Index", blockIndex, len(lostIndices), lostIndices
		
		lostPureCells = ibfLost.getPureCells()
		pureCellsNum = len(lostPureCells)
	
		
	print "Recovery Check..."
	for cIndex in xrange(ibfLost.m):
		if ibfLost.cells[cIndex].getCount() != 0:
			print "Failed to recover", "Reason: ", "Count", cIndex
			return None
			
			
		if ibfLost.cells[cIndex].getDataSum().isZeroDataSum() == False:
			print "Failed to recover", "Reason: ", "Datasum", cIndex
			return None
			
		if  ibfLost.cells[cIndex].getHashProd() !=1:
			print "Failed to recover", "Reason: ", "HashProd", cIndex
			print cIndex
			return None
					
		
	if len(lostIndices) != 0:
		print lostIndices
		return None
	
	return L
	
	




