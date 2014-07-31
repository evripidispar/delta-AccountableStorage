import argparse
import os
import math


def rewriteNames(filename):
    return 'blocks/'+filename

def getRunInfo(name):
    name = name.split("_")
    return (name[1], name[3])


def getTaskNumber(size):
    ideal = size / 8
    if ideal <= 10485760:
        return  1
    else:
        return (8*ideal)/10485760

def main():

    p = argparse.ArgumentParser(description='Experiment driver')
    
    p.add_argument('-b', dest='blkDir', action='store', default=None,
                   help='Filesystem directory')
    
    p.add_argument('-r', dest='runsPerFs', action='store', type=int,
                   default=5, help='Number of runs Per Filesystem')
    

    p.add_argument('-o', dest='outDir', action='store', help='OutputDirectory')

    args = p.parse_args()
    availableFS = os.listdir(args.blkDir)
    fsFiles = map(rewriteNames, availableFS)
    
    task = 100
    w = 8
    k = 5
    loss = 0
    
    runs  = {}
    print "#!/bin/bash"
    for fName,runId in zip(fsFiles,availableFS):
        
        blocks, size = getRunInfo(fName)
        blocks = int(blocks)
        size = int(size)
        
        totalSize = os.stat(fName)
        totalSize = totalSize.st_size
         
        tasksNum = getTaskNumber(totalSize)
        if blocks > 1000:
            k = 4
        else:
            k = 6
        loss = int(math.floor(math.log(blocks)))
        
        for r in xrange(args.runsPerFs):
            
            if size < 1024:
                continue
            
            if size > 8192:
                continue
            runName = "runs/"+str(blocks)+"__"+"__"+str(size)+".txt"
            tagName = "tags/tags_"+str(blocks)+"_"+str(size)+".dat"
            preprocName = "preproc/preproc_"+str(blocks)+"_"+str(size)+".data"
            cmd = "python driver.py -b %s -g generator.txt -k %d -n 1024 -w %d --task %d -r %s -l %d --tagload %s --preprocload %s;" % (fName, k, w, tasksNum, runName, loss, tagName, preprocName)
            if int(blocks) not in runs.keys():
                runs[int(blocks)] = []
            runs[int(blocks)].append(cmd)
            
    skeys = runs.keys()
    skeys.sort()
    for k in skeys:
        
        for i in runs[k]:
            print i
        
    

if __name__ == "__main__":
    main()