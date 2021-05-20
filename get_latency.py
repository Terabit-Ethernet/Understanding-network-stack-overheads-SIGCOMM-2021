import numpy as np
window = [100, 200, 400, 800 , 1600, 3200, 6400, 12800]

def read_file(filename):
	output = []
	with open(filename) as f:
		lines = f.readlines()
		for line in lines:
			if "delta" not in line:
				continue	
			params = line.split()
			lat = float(params[8]) / 1000.0
			output.append(lat)
	print (filename)
	print ("avg latency", np.mean(output))
	print ("99 latency", np.percentile(output, 99))


for i in window:
	read_file("results/{}_latency".format(i))
