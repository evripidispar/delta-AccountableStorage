from Crypto.Util import number 
from Crypto.Hash import HMAC



class CloudPDRObj(object):
	
	def __init__(self, Nbits, filename):
			
		self.p =  number.getPrime(Nbits/2)
		self.q =  number.getPrime(Nbits/2)
		self.N = self.p * self.q
		
		self.secret = self.generateSecret(Nbits)
		
		try:
			fp = open(filename, "r")
			self.g = fp.read()
			self.g = long(self.g)
			fp.close()
			
		except IOError as ioe:
			print "Generator file does not exist\n Creating new generator file:", ioe
			self.g = self.pickGeneratorG()
			fp = open(filename, "w")
			fp.write(str(self.g))
			fp.close()		
		
			
	def generateSecret(self,Nbits):
		tmpRand = number.getRandomInteger(Nbits)
		h = HMAC.new(str(self.N))
		h.update(str(tmpRand))
		return h.hexdigest()

	def pickGeneratorG(self):
		print "Entering pickGenerator"
		while True:
			a = number.getRandomRange(0,self.N)
			if a>self.N:
				return None
			r0 = number.GCD(a,self.N)
			if r0==1:
				continue
		
			r0 = a-1
			r1 = number.GCD(r0,self.N)
			if r1 == 1:
				continue

			r0 = a+1
			r1 = number.GCD(r0,self.N)
			if r1 == 1:
				continue
			break
		g = a**2
		print "Exiting pickGenerator"
		return g

