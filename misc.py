def getIPv4Addresses():
	import netifaces
	ret = []
	for i in netifaces.interfaces():
		if i == 'lo':
			continue
		try:
			ret += [netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr']]
		except KeyError:
			pass
	return ret

