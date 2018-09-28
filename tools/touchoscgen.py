#!/usr/bin/python
import base64
import zipfile
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree

cnt = {}

def getname(name, typ):
	if (name == None):
		if(typ not in cnt):
			cnt[typ] = 0
		name = "%s%d" % (typ, cnt[typ])
		cnt[typ] += 1
		return name
	else:
		return name

def b64(string):
	s = string.encode()
	s = base64.b64encode(s)
	s = s.decode()
	return s

def create_page(name, text, color = "gray"):
	p = ET.Element("tabpage")
	p.set("name", b64(name))
	p.set("scalef", "0.0")
	p.set("scalet", "0.0")
	p.set("li_t", b64(text))
	p.set("li_c", color)
	p.set("li_s", "14")
	p.set("li_o", "false")
	p.set("li_b", "false")
	p.set("la_t", b64(text))
	p.set("la_c", color)
	p.set("la_s", "14")
	p.set("la_o", "false")
	p.set("la_b", "false")
	return p

def create_led(name, color, ctrl, x, y, w, h, sf, st):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "led")))
	p.set("type", "led")
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", str(sf))
	p.set("scalet", str(st))
	return p

def create_push(name, color, ctrl, x, y, w, h, sf = 0.0, st = 1.1):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "push")))
	p.set("type", "push")
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", str(sf))
	p.set("scalet", str(st))
	p.set("local_off", "false")
	p.set("sp", "true")
	p.set("sr", "false")
	return p

def create_toggle(name, color, ctrl, x, y, w, h, sf = 0.0, st = 1.1):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "toggle")))
	p.set("type", "toggle")
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", str(sf))
	p.set("scalet", str(st))
	p.set("local_off", "true")
	return p

def create_label(name, color, ctrl, x, y, w, h, text = "", size=18):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "label")))
	p.set("type", "labelv")
	p.set("color", color)
	p.set("text", b64(text))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("size", str(size))
	p.set("background", "false")
	p.set("outline", "false")
	if (ctrl != None):
		p.set("osc_cs", b64(ctrl))
	return p

def create_fader(name, color, ctrl, x, y, w, h, d = 'h', c = False):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "fader")))
	p.set("type", "fader%s"%d)
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", "0.0")
	p.set("scalet", "1.0")
	p.set("size", "18")
	p.set("response", "absolute")
	p.set("inverted", "false")
	p.set("centered", "true" if c else "false")
	return p

def create_rotary(name, color, ctrl, x, y, w, h):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "fader")))
	p.set("type", "rotaryh")
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", "0.0")
	p.set("scalet", "1.0")
	p.set("size", "18")
	p.set("response", "absolute")
	p.set("inverted", "false")
	p.set("centered", "true")
	p.set("norollover", "true")
	return p

def create_multitoggle(name, color, ctrl, x, y, w, h, c):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "toggle")))
	p.set("type", "multitoggle")
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", "0.0")
	p.set("scalet", "1.0")
	p.set("number_x", "1")
	p.set("number_y", str(c))
	p.set("ex_mode", "false")
	p.set("local_off", "false")
	return p

def create_multifader(name, color, ctrl, x, y, w, h, n, d='h', c=False):
	p = ET.Element("control")
	p.set("name", b64(getname(name, "toggle")))
	p.set("type", "multifader%s" % d)
	p.set("color", color)
	p.set("osc_cs", b64(ctrl))
	p.set("x", str(y))
	p.set("y", str(x))
	p.set("w", str(h))
	p.set("h", str(w))
	p.set("scalef", "0.0")
	p.set("scalet", "1.0")
	p.set("number", str(n))
	p.set("inverted", "false")
	p.set("centered", "true" if c else "false")
	return p

def create_layout(width, height):
	root = ET.Element("layout")
	root.set("version", "16")
	root.set("mode", "3")
	root.set("w", str(height))
	root.set("h", str(width))
	root.set("orientation", "vertical")
	return root

def write_layout(layout, filename):
	tree = ElementTree()
	tree._setroot(layout)
	tree.write("index.xml")
	with zipfile.ZipFile('%s.touchosc' % filename, 'w') as myzip:
	 	myzip.write('index.xml')
