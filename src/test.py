import pickle
import marshal

from Cell import Cell
from SharedCounter import SharedCounter

f=open("test.cell","wb")
c=Cell(10,10)
for i in range(10):
    c.count+=1

print 'before pickle',  c.count

marshal.dump(c,f)

f = open("test.cell", "rb")
lCell = marshal.load(f)

print 'after pickle', lCell.count
