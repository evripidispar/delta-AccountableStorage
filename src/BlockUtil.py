from Crypto import Random
from Crypto.Random import random 
from Block import *
from bitarray import bitarray
import numpy as np


def npArray2bitArray(npArray):
	bit = bitarray()
	bit.pack(npArray.tostring())
	return bit



def createSingleBlock(dataSize, pseudoData=None, bits=None):
	data = pseudoData
	if data == None:
		data = np.random.randint(2, size=dataSize)
	else:
		
		smpl = np.random.random_integers(dataSize-1, size=bits)
		data[smpl]=~data[smpl]
	return data



def blockCreatorMemory(howMany, dataSize):
	blocks = []
	for i in xrange(0, howMany):
		newBlock = createSingleBlock(i, dataSize)
		blocks.append(newBlock)
	return blocks
	

def pickCommonBlocks(numOfBlocks, numOfCommon):
	common = random.sample(xrange(numOfBlocks), numOfCommon)
	return common


def pickDiffBlocks(numOfBlocks, common, totalBlocks):
	numDiff = numOfBlocks - len(common)
	
	blocks = range(totalBlocks)

	for block_index in xrange(numOfBlocks):
		if block_index in common:
			blocks.remove(block_index)

	a_diff = random.sample(blocks, numDiff)
	for block_index in a_diff:
		blocks.remove(block_index)


	b_diff = random.sample(blocks, numDiff)
	return (a_diff, b_diff)


