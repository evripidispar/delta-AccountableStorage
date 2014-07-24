import argparse
import sys
import numpy as np
import matplotlib
matplotlib.use('PDF')
import matplotlib.pyplot as plt


def average_comp(filename, numBlocks, blocksize, version, plot_type):
    timesStatsFile = open(filename, "r")
    
    setup=['ibf','tag']
    proof_check=['subset-check', 'cmbW-start', 'cmbW-last','lostSum','subIbf','recover','qSet_check', 'cmbW']
    proof_generation=['cmbLost','cSumKept','cTagKept','ibf_serv','qSet_proof']
    
    times_stats={}
    for line in timesStatsFile:
        values = line.split()
        if values[0] not in times_stats.keys():
            times_stats[values[0]]= []
        times_stats[values[0]].append(float(values[1]))    
    timesStatsFile.close()
    
    metrics=[]
    
    average_setup=0.0
    average_proof_check=0.0
    average_proof_generation=0.0
    
    if plot_type==0:
        for k in times_stats.keys():
            average=0.0
            average = sum(times_stats[k]) / (len(times_stats[k]))
            fp = open("./outputs/"+k+"_blocksize_"+str(blocksize)+"_"+version+".dat", "a+")
            fp.write(str(numBlocks)+"\t"+ str(average)+"\n")
            fp.close()
        
            if k in setup:
                average_setup+=average
            elif k in proof_check:
                average_proof_check+=average
            elif k in proof_generation:
                average_proof_generation+=average
        
            if ((k=="tag") or (k=="cTagKept")):
                metrics.append(k)
 
        if (average_setup!=0.0):   
            metrics.append('setup')
        if (average_proof_check!=0.0):  
            metrics.append('proof_check')
        if (average_proof_generation!=0.0):
            metrics.append('proof_generation')
        
        timesStatsFile.close()
    
        if (average_setup!=0.0):
            fp = open("./outputs/setup_blocksize_"+str(blocksize)+"_"+version+".dat", "a+")
            fp.write(str(numBlocks)+"\t"+ str(average_setup)+"\n")
            fp.close()
        if (average_proof_check!=0.0):   
            fp = open("./outputs/proof_check_blocksize_"+str(blocksize)+"_"+version+".dat", "a+")
            fp.write(str(numBlocks)+"\t"+ str(average_proof_check)+"\n")
            fp.close()
        if (average_proof_generation!=0.0):    
            fp = open("./outputs/proof_generation_blocksize_"+str(blocksize)+"_"+version+".dat", "a+")
            fp.write(str(numBlocks)+"\t"+ str(average_proof_generation)+"\n")
            fp.close()
        return metrics
    
    elif (plot_type!=0):
        for k in times_stats.keys():
            average=0.0
            average = sum(times_stats[k]) / (len(times_stats[k]))
            fp = open("./outputs/"+k+"_numBlocks_"+str(numBlocks)+"_"+version+".dat", "a+")
            fp.write(str(blocksize)+"\t"+ str(average)+"\n")
            fp.close()
        
            if k in setup:
                average_setup+=average
            elif k in proof_check:
                average_proof_check+=average
            elif k in proof_generation:
                average_proof_generation+=average
        
            if ((k=="tag") or (k=="cTagKept")):
                metrics.append(k)
 
        if (average_setup!=0.0):   
            metrics.append('setup')
        if (average_proof_check!=0.0):  
            metrics.append('proof_check')
        if (average_proof_generation!=0.0):
            metrics.append('proof_generation')
        
        timesStatsFile.close()
    
        if (average_setup!=0.0):
            fp = open("./outputs/setup_numBlocks_"+str(numBlocks)+"_"+version+".dat", "a+")
            fp.write(str(blocksize)+"\t"+ str(average_setup)+"\n")
            fp.close()
        if (average_proof_check!=0.0):   
            fp = open("./outputs/proof_check_numBlocks_"+str(numBlocks)+"_"+version+".dat", "a+")
            fp.write(str(blocksize)+"\t"+ str(average_proof_check)+"\n")
            fp.close()
        if (average_proof_generation!=0.0):    
            fp = open("./outputs/proof_generation_numBlocks_"+str(numBlocks)+"_"+version+".dat", "a+")
            fp.write(str(blocksize)+"\t"+ str(average_proof_generation)+"\n")
            fp.close()
        return metrics

def combine_files(fileList, Output_file):
    index_file=0
    #index_line=0
    lines=[]
    for file in fileList:
        with open(file, 'r') as infile:
            index_line=0
            for line in infile:
                values = line.split()
                if index_file==0:
                    #print index_line
                    #print len(values)
                    lines.append(values[0]+'\t'+values[1]+'\t')
                elif (index_file != 0):
                    lines[index_line]= lines[index_line]+values[1]+"\t"
                index_line+=1
            index_file+=1
    #for line in lines:
        #line=line+"\n"
    
    outfile=open(Output_file,'a+')
    if len(lines) > 0:
        for line_id in lines:
            outfile.write(line_id+"\n")
    outfile.close()
   
        

def readStatsFromFile(filename):
    statsFile = open(filename, "r")
    
    times_set={}
    numBlocks_list=[]
    for line in statsFile:
        index = 0
        values = line.split()
        print values[0]
        numBlocks_list.append(values[0])
        while (index < len(values)-1):
            if index not in times_set.keys():
                times_set[index]= []
            times_set[index].append(float(values[index+1]))
            index+=1
    
    #numdiffplots = len(values)-1
    statsFile.close()
    
    return (times_set, numBlocks_list)
                  
    
def plotlines(filename, labels, filename_output, xlabel='numBlocks', ylabel='time (in sec)', title=''):
    colors = ['r','g','b']
    markers = ['x','.','+']
    index = 0
    plt.figure(1)
    times_set, numBlocks_list = readStatsFromFile (filename)
    #plt.axis([0, 10000, 0, 5])
    while (index < len(times_set)):
        line, = plt.plot(numBlocks_list, times_set[index], label = labels[index])
        line.set_antialiased(False) # turn off antialising
        plt.setp(line, color = colors[index], marker = markers[index], markeredgewidth = 2.0)
        index+=1
  
    plt.legend()
    plt.xlabel(xlabel)    
    plt.ylabel(ylabel)
    plt.title(title)
    #plt.show()
    plt.savefig(filename_output)
    plt.clf()
        
def plotbar(filename, numdiffplots, labels, filename_output,xlabel='', ylabel='', title=''):
    colors = ['r','g','b']
    markers = ['x','.','+']
    index = 0
    plt.figure(2)
    times_set, numBlocks_list = readStatsFromFile (filename)
    print times_set
    ind = np.arange(len(numBlocks_list))    # the x locations for the groups
    width = 0.25       # the width of the bars: can also be len(x) sequence
    bottom = np.array([0.0] * len(times_set[index]))
    while (index<len(times_set)):
        if index == 0:
            p = plt.bar(ind, times_set[index], width, color = colors[index], label = labels[index])
        else:
            #print "check"
            bottom = bottom + times_set[index-1]
            p = plt.bar(ind, times_set[index], width, bottom, color = colors[index], label = labels[index])  
        index+=1
  
    plt.xlabel(xlabel)    
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(ind+width/2., numBlocks_list )
    #plt.yticks(np.arange(0,81,10))
    plt.legend()
    #plt.show()  
    plt.savefig(filename_output)
    plt.close()
     



def main():
    
    p = argparse.ArgumentParser(description='Plotting Parser')

    
    p.add_argument('-s', dest='blkSize', action='store', default=512,
                   help='Size of Block')
    
    p.add_argument('-server', dest = 'isServer', action = 'store', default=0,
                   help='Recognize if it is server plotting')
    
    p.add_argument('-plot', dest = 'plot_type', action = 'store', default=0,
                   help='Recognize what plot we want')
    
    
    args = p.parse_args()
    #print args.isServer
    if args.blkSize < 512: 
        print "Size of Block is larger than 512 bytes"
        sys.exit(1)
        
    if int(args.isServer) >2:
        print 'Please specify whether the plot is for client or server'
        sys.exit(1)
        
    if int(args.plot_type) >2:
        print 'Please specify what type of plot you want'
        sys.exit(1)  
    
    numBlocksList=[100,1000,10000]
    
    #if (int(args.isServer)==0): #client plots
    #    for nBlk in numBlocksList:  
    #        metrics = average_comp("./runs/"+str(nBlk)+"____"+str(args.blkSize)+".txt", nBlk, args.blkSize,'base', args.plot_type)     
    #        for metric in metrics:
    #            plotlines('./outputs/'+metric+'_blocksize_'+str(args.blkSize)+'_base.dat', ['baseline'],'../plots/test_'+metric , xlabel='numBlocks', ylabel='time (in sec)', title= metric)
    #elif(int(args.isServer)==1): #server plots
    #    for nBlk in numBlocksList:  
    #        metrics = average_comp("./runs/"+str(nBlk)+"____"+str(args.blkSize)+".txt.serv", nBlk, args.blkSize,'base', args.plot_type)
    #        for metric in metrics:
    #            plotlines('./outputs/'+metric+'_blocksize_'+str(args.blkSize)+'_base.dat', ['baseline'],'../plots/test_'+metric , xlabel='numBlocks', ylabel='time (in sec)', title= metric)
    
    #    fileList=['./outputs/proof_generation_blocksize_512_base.dat','./outputs/ibf_serv_blocksize_512_base.dat']
    
    #    combine_files(fileList, './outputs/test_combined.dat')
    
    #    plotlines('./outputs/test_combined.dat', ['baseline','test'],'../plots/test_combined' , xlabel='numBlocks', ylabel='time (in sec)', title= 'output')
        
   # metrics = average_comp("./runs/"+str(nBlk)+"____"+str(args.blkSize)+".txt", nBlk, args.blkSize,'base', 1)
   
    plotbar("./setup_time_test_1000.dat", 2 ,['tag_time','ibf_time'],'../plots/test_bar_setup_fixnBlk','Block Size (in bytes)','Setup Time (in sec)','Setup Time for different Block sizes')
    plotbar("./setup_time_test_4096.dat", 2 ,['tag_time','ibf_time'],'../plots/test_bar_setup_fixSizeBlk','Number of Blocks','Setup Time (in sec)','Setup Time for different number of Blocks of Size 4KB')
    plotbar("./proof_generation_test_4096.dat", 3 ,['csum_time','ctag_time','ibf_time'],'../plots/test_bar_proof_fixSizeBlk','Number of Blocks','Proof Generation Time (in sec)','Proof Generation Time for different number of Blocks of Size 4KB')
    plotbar("./proof_generation_test_1000.dat", 3 ,['csum_time','ctag_time','ibf_time'],'../plots/test_bar_proof_fixnBlk','Block Size (in bytes)','Proof Generation Time (in sec)','Proof Generation Time for different Block Size')
    
if __name__ == "__main__":
    main()  
    