import pickle
from Cell import Cell
from SharedCounter import SharedCounter
f=open("test.cell","wb")
c=Cell(10,10)
for i in range(10):
    c.count.increment()

print 'before pickle',  c.count.getValue()

pickle.dump(c,f)

f = open("test.cell", "rb")
lCell = pickle.load(f)

print 'after pickle', lCell.count.getValue()
