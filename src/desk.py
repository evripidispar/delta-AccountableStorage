from os import listdir, stat


def task2(filename):
	s = stat(filename)
	ideal = s.st_size / 8
	reminder = s.st_size % 8
	#print filename, s.st_size, 4096*s.st_size
	#print reminder
	if ideal <= 10485760:
	        return  8
	else:
	        return (8*ideal)/10485760

f = listdir("blocks/")
for i in f:
	name = "blocks/"+i
	t = task2(name)
	print i, t
