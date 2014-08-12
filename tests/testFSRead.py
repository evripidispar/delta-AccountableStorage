
import sys
import BlockEngine as be
import ExpTimer as et
import struct
import CloudPdrMessages_pb2


def main():
    
    fp = open(sys.argv[1],"rb")
    readAmount = int(sys.argv[2])
    fsSize = fp.read(4)
    fsSize, = struct.unpack("i", fsSize)
    fs = CloudPdrMessages_pb2.Filesystem()
    fs.ParseFromString(fp.read(int(fsSize)))
    
    readT = et.ExpTimer()
    readT.registerSession("read")
    readT.registerTimer("read", "blocks")
    
    indexSum = 0
    readT.startTimer("read", "blocks")
    while True:
        data = fp.read(readAmount)
        if len(data) == 0:
            readT.endTimer("read", "blocks")
            print "Total", readT.getTotalTimer("read", "blocks")
            break
        else:
            for blockPB in be.chunks(data, fs.pbSize):
                pass

    
    
if __name__ == "__main__":
    main()