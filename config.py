import socket

args            = lambda: None
# Configure server parameters
args.zcip       = []
args.slip       = '127.0.0.1'
args.oscip      = '0.0.0.0'
args.oscport    = 12101
args.oscname    = "OSCServer_" + socket.gethostname()
args.debug      = True

args.active_channels = {
	"ch1" : "Ch 1",
	"ch2" : "Ch 2",
	"ch3" : "Ch 3",
	"ch4" : "Ch 4",
	"ch5" : "Ch 5",
	"ch6" : "Ch 6",
	"ch7" : "Ch 7",
	"ch8" : "Ch 8",
	"ch9" : "Ch 9/10",
	"ch10": "Ch 11/12",
	"ch11": "Ch 13/14",
	"ch12": "Ch 15/16",
}

args.active_auxs = {
	"aux1": "Aux1",
	"aux2": "Aux2",
	"aux3": "Aux3",
	"aux4": "Aux4",
	"fxa" : "FxA",
	"fxb" : "FxB",
}

args.transport_device = "ASIO PreSonus FireStudio"
args.transport_samplerate = 44100
args.transport_channels = range(16)
