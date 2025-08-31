#!/usr/bin/python3
import time
import argparse

from . import studiolive
from .osc import SharedTCPServer, zc_register_osc_tcp
from .handler import SLClientHandler

def main():
    argp = argparse.ArgumentParser(prog='osclive', description='Python OSC server for remote control of the PreSonus StudioLive mixer')
    argp.add_argument("-u", "--uc", help="Connect to the host running Universal Control application", metavar='HOST')
    argp.add_argument("-c", "--config", help="Load YAML configuration file", metavar='CFG')
    argp.add_argument("-d", "--debug", help="Print debug informations", action='store_true')
    argp.add_argument("-m", "--midi", help="Use midi port instead of IEEE1394")
    args = argp.parse_args()

    if args.uc:
        from .studiolive.ucbackend import SLUcBackend
        slbackend = SLUcBackend(studiolive.StudioLive1602, args.uc)
    else:
        from .studiolive.rawbackend import SLRaw1394Backend
        slbackend = SLRaw1394Backend(studiolive.StudioLive1602, args.midi)

    slbackend.debug = args.debug
    sl = studiolive.SLRemote(slbackend, args.debug)
    sl.debug = args.debug
    sl.connect()

    SLClientHandler.sl = sl

    if args.config:
        import yaml
        cfg = yaml.safe_load(open(args.config).read())
        if cfg.get("studiolive"):
            cfg_sl = cfg.get("studiolive")
            if cfg_sl.get("input") and cfg_sl.get("input").get("names"):
                SLClientHandler.input_names = cfg_sl["input"]["names"]
            if cfg_sl.get("aux") and cfg_sl.get("aux").get("names"):
                SLClientHandler.aux_names = cfg_sl["aux"]["names"]

    osc_srv = SharedTCPServer(SLClientHandler)
    zc_svcs = zc_register_osc_tcp()

    try:
        while True:
            time.sleep(0.1)
    finally:
        osc_srv.shutdown()
        for zc, si in zc_svcs:
            zc.close()
        sl.disconnect()


if __name__ == "__main__":
    main()
