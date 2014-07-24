from time import time

class ExpTimer(object):
    
    def __init__(self):
        self.timers = {}
    
    def registerSession(self, session):
        self.timers[session] = {}
    
    def registerTimer(self, sId, tId):
        self.timers[sId][tId] = 0
        self.timers[sId][tId+str("_total")] = 0
    
    def startTimer(self, sId, tId):
        self.timers[sId][tId] = time()
    
    def endTimer(self, sId, tId):
        tEnd=time()
        self.timers[sId][tId] = tEnd - self.timers[sId][tId]
        self.timers[sId][tId+str("_total")]+= self.timers[sId][tId]
    
    def printTimer(self, sId, tId):
        print tId, ":", self.timers[sId][tId] , "sec"
    
    
    def printTotalTotal(self, sId, tId):
        print tId+str("_total"), self.timers[sId][tId+str("_total")]
    
    def printSessionTimers(self, sId):
        for k in self.timers[sId].keys():
            print k, ":", self.timers[sId][k], "sec"
            
    def getTotalTimer(self, sId, tId):
        return self.timers[sId][tId+str("_total")]
    
    def changeTimerLabel(self, sId, tId, newTid):
        self.timers[sId][newTid] = self.timers[sId][tId]
        self.timers[sId][newTid+str("_total")] = self.timers[sId][tId+str("_total")]
        del self.timers[sId][tId]