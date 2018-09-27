import threading
import struct
from socket import *

class SLRemote(object):
    # SL Remote server 
    # Code is based on implementation of vsl1818

    def __init__(self, magic, debug = False, virtual = False):
        self.magic = magic
        self.debug = debug
        self.virtual = virtual
        self.loaded = False
        self.killed = False
        self.connection = None
        self.levels = {}
        self.update_thread = None
        self.channel_names = {}
        self.update_callbacks = []
        self.level_callbacks = []

        self.mapchannel = {}
        self.mapcontrol = {}
        self.revchannel = {}
        self.revcontrol = {}

        # channel_id -> control_id -> value
        self.channels = {}
        self.channel_max = 0

    # Low-level send & receive functions
    def parsestr(self, s, n=None):
        assert b'\x00' in s
        if n is not None:
            assert len(s) == n
        return (s[:s.find(b'\x00')]).decode()

    def recv(self, n):
        s = b""
        def remaining():
            return n-len(s)
        while remaining() > 0:
            s += self.connection.recv(remaining())
        return s

    def readmsg(self):
        signature, l = struct.unpack("II", self.recv(8))
        assert signature == 0xaa550011
        return self.recv(l)

    def sendmsg(self, message):
        self.connection.send(struct.pack("II", 0xaa550011, len(message)) + message)

    # Main functions
    def connect(self, host, port, name="SL-Remote", ident="1BE8DC6BF62EA577B"):
        if(self.virtual):
            return
        assert not self.connection
        self.connection = socket(AF_INET, SOCK_STREAM)
        self.connection.connect((host, port))
        self.sendmsg(struct.pack("IIHH32s32s", self.magic[0], self.magic[1], 3, self.magic[2], ident.encode(), name.encode()))

    def start(self):
        if(self.virtual):
            self.loaded = True
            return
        print("SLRemote: starting update thread")
        self.update_thread = threading.Thread(target=self.update_process)
        self.update_thread.start()

    def update(self, message_header, message_body):
        unknown1, unknown2, category, unknown3 = struct.unpack("IIHH", message_header)
        assert unknown1 == self.magic[0]
        assert unknown2 == self.magic[1]
        assert unknown3 == self.magic[2]

        if category == 5:
            self.loaded = True
            levels = struct.unpack("128B", message_body)
            #print(levels)
            for i in range(0, 8):
                self.levels["in%d,0" % i] = levels[i]
            for i in range(0, 4):
                self.levels["in%d,0" % (i+8)] = levels[i*2 + 8]
            # Master
            self.levels["in16,0"] = levels[20]
            #i = 0
            #for channel in self.revchannel:
            #    self.levels[channel] = levels[i]
            #    i += 1
            for callback in self.level_callbacks:
                callback()

        elif category == 4:
            unknown4, channel_id, channel_name = struct.unpack("HH48s", message_body)
            channel_name = self.parsestr(channel_name)

            assert unknown4 == 0
            self.channel_names[channel_id] = channel_name
            if(self.debug):
                print("SLRemote: recv channel ID %02d name: '%s'" % (channel_id, self.channel_names[channel_id]))

        elif category == 2:
            control_id, value, channel_id = struct.unpack("=Hd32s", message_body)
            channel_id = self.parsestr(channel_id)
            if(channel_id not in self.revchannel):
                print("SLRemote: recv control update for unknown channel %s" % channel_id)
                return

            channel = self.revchannel[channel_id]
            if(control_id not in self.revcontrol[channel]):
                print("SLRemote: recv unknown control update %d for channel %s with value %.2f" % (control_id, channel, value))
                return

            control = self.revcontrol[channel][control_id]
            self.channels[channel][control] = value
            if(self.debug):
                print("SLRemote: recv control update for %s: %s = %.2f" % (channel, control, value))

            for callback in self.update_callbacks:
                callback(channel, control, value)
        elif category == 7:
            # Connected clients?
            pass
        elif category == 13:
            # Number of presets from the disk?
            pass
        elif category == 14:
            # Presets from the disk
            pass
        elif category == 17:
            # Unknown
            pass
        else:
            if(self.debug):
                print("SLRemote: recv unknown category %s, message size %d" % (category, len(message_body)))
                #print(message_body)
            pass

    def update_process(self):
        assert self.connection
        while not self.killed:
            message = self.readmsg()
            self.update(message[:12], message[12:])

    def add_update_callback(self, callback):
        self.update_callbacks.append(callback)

    def rename_channel(self, old, new):
        assert old     in self.mapchannel
        assert new not in self.mapchannel
        rev = self.mapchannel[old]
        self.revchannel[rev] = new
        self.channels[new] = self.channels.pop(old)
        self.revcontrol[new] = self.revcontrol.pop(old)
        self.mapcontrol[new] = self.mapcontrol.pop(old)
        self.mapchannel[new] = rev
        self.mapchannel.pop(old)

    def get_level(self, channel):
        assert channel in self.mapchannel
        return self.levels[self.mapchannel[channel]]

    def get_control(self, channel, control):
        if(self.debug):
            print("SLRemote: Get control %s on channel %s" % (control, channel))
        assert channel in self.mapchannel
        assert control in self.channels[channel]
        return self.channels[channel][control]

    def set_control(self, channel, control, value):
        if(self.debug):
            print("SLRemote: Set control %s on channel %s" % (control, channel))
        assert channel in self.mapchannel
        assert control in self.channels[channel]

        if value > 1:
            value = 1
        if value < 0:
            value = 0

        self.channels[channel][control] = value
        if(self.virtual):
            for callback in self.update_callbacks:
                callback(channel, control, value)
            return

        header = struct.pack("IIHH", self.magic[0], self.magic[1], 2, self.magic[2])
        body = struct.pack("=Hd32s", self.mapcontrol[channel][control], value, self.mapchannel[channel].encode())
        self.sendmsg(header + body)
