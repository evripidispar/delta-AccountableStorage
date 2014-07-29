import cPickle
import time
import msgpack

class Test():
    def __init__(self):
        self.s = range(1000000)
        self.d = {"t":range(100), "tt":range(9000000, 10000000)}

obj = Test()
s = [range(1000000), obj]
sp = time.time()
a=msgpack.dumps(s)
a=msgpack.loads(a)
ep = time.time()



s = time.time()
a=cPickle.dumps(s)
a=cPickle.loads(a)
e = time.time() 
print ep-sp, e-s
