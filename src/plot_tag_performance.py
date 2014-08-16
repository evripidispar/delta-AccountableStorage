import os
import cPickle
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt


def gather_data(dataDir, filePrefix):
    os.chdir(dataDir)
    files = os.listdir(".")
    dataDict = {}
    for fname in files:
        if fname.startswith(filePrefix):
            blkNum, size = (fname.split("_"))[1:4]
            size = size[0:size.index(".txt")]
            fp = open(fname, "rb")
            data = []
            while True:
                try:
                    tmp = cPickle.load(fp)
                    for i in tmp:
                        data.append(i)
                    if len(data) == 0:
                        break
                except EOFError:
                    break
            blkNum = int(blkNum)
            size = int(size)
            
            if blkNum not in dataDict.keys():
                dataDict[blkNum] = {}
            dataDict[blkNum][size] = {}
            dataDict[blkNum][size]["avg"] = np.mean(data)
            dataDict[blkNum][size]["med"] = np.median(data)
            dataDict[blkNum][size]["std"] = np.std(data)


    return dataDict



    
     

def main():
    p = argparse.ArgumentParser(description="Tag plotting script")
    
    p.add_argument('-d', dest='dataDir', action="store",
                   default=None, help="Data directory")
    
    p.add_argument('-o', dest='outDir', action="store",
                   default=None, help="Plot output directory")
    
    p.add_argument('-p', dest='filePrefix', action="store",
                   default='tagperf', help="data file prefix")
    
    args = p.parse_args()
    
    if args.dataDir == None:
        print "Please specify the tag data directory"
        return;
    
    if args.outDir == None:
        print "Please specify the output directory"
        return
    
    d = gather_data(args.dataDir, args.filePrefix)
    blocks = sorted(d.keys())
    sizes = sorted(d[blocks[0]].keys())
    #print "blocks", "size", "mean", "median", "std"
    for i in blocks:
        sizeStr = ""
        for j in sizes:
            sizeStr += "%30f" % (d[i][j]["avg"]) 
        #print i,"\t", j,"\t", d[i][j]["avg"],"\t", d[i][j]["med"],"\t", d[i][j]["std"] 
        print i, sizeStr
    
if __name__ == "__main__":
    main()