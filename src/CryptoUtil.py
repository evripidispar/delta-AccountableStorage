from Crypto.Util import number
from Crypto.Hash import HMAC
import gmpy2

def pickPseudoRandomTheta(secret_key, index):
	hmac = HMAC.new(secret_key)
	hmac.update(index)
	return hmac.hexdigest()

def apply_f(block, N, secret_key, g):
	index = block.getStringIndex()
	a = pickPseudoRandomTheta(secret_key, index)
	
	
	aLong = number.bytes_to_long(a)
	#print aLong
	bLong = number.bytes_to_long(block.data.tobytes())
	
	abExp = aLong*bLong
	return gmpy2.powmod(g, abExp, N)

def MessageAuthenticationCode(secret_key, block):
	hmac = HMAC.new(secret_key)
	hmac.update(str(number.bytes_to_long(block.data.tobytes())))
	return int(hmac.hexdigest(), 16)