from HashFunc import *
from Block import Block

s = [Hash1, Hash2, Hash3, Hash4, Hash5, Hash6]

def fakeIbf(cellNum, k, objNum):
    for i in xrange(objNum):
        b = Block(i)
        