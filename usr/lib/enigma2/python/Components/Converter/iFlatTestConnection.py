# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from enigma import eTimer
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
from os import system as os_system, path as os_path
import array
import struct
import fcntl

OFFLINE = "Offline"	# offline connection  text
ONLINE = "Online"	# online connection text
SIOCGIFCONF = 0x8912	# define SIOCGIFCONF
BYTES = 4096		# Simply define the byte size


class iFlatTestConnection(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.testOK = False
		self.testTime = 1.0		# 1 seconds
		self.testPause = 10		# 10 seconds
		self.testHost = "77.88.21.3"	# www.yandex.ru
		self.testPort = 80		# www port
		self.failCmd = None

		if len(type):
			p = type[:].find("://")
			if p != -1:
				type = type[p + 3:]
			type = type[:].split(":", 3)
			if len(type[0]) > 0:
				self.testHost = type[0]
			if len(type) > 1 and type[1].isdigit():
				self.testPort = int(type[1])
			if len(type) > 2 and type[2].isdigit():
				self.testPause = int(type[2])
			if len(type) > 3:
				self.failCmd = type[3]

		self.testThread = None
		self.testDisabled = False
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call=False)

		self.testTimer = eTimer()
		self.testTimer.callback.append(self.poll)
		self.testTimer.start(100, True)

	def poll(self):
		if self.testDisabled:
			return
		if self.testThread is None or not self.testThread.isAlive():
			self.testThread = Thread(target=self.test)
			self.testThread.start()
			if self.testPause > 0:
				self.testTimer.start(self.testPause * 1000, True)
		else:
			self.testTimer.start(1000, True)

	def get_iface_list(self):
		names = array.array('B', '\0' * BYTES)
		sck = socket(AF_INET, SOCK_DGRAM)
		bytelen = struct.unpack('iL', fcntl.ioctl(sck.fileno(), SIOCGIFCONF, struct.pack('iL', BYTES, names.buffer_info()[0])))[0]
		sck.close()
		namestr = names.tostring()
		return [namestr[i:i + 32].split('\0', 1)[0] for i in range(0, bytelen, 32)]

	def test(self):
		prevOK = self.testOK
		link = "down"
		for iface in self.get_iface_list():
			if "lo" in iface:
				continue
			if os_path.exists("/sys/class/net/%s/operstate" % (iface)):
				fd = open("/sys/class/net/%s/operstate" % (iface), "r")
				link = fd.read().strip()
				fd.close()
			if link != "down":
				break
		if link != "down":
			s = socket(AF_INET, SOCK_STREAM)
			s.settimeout(self.testTime)
			try:
				self.testOK = not bool(s.connect_ex((self.testHost, self.testPort)))
			except:
				self.testOK = False
			s.close()
		else:
			self.testOK = False
		if prevOK != self.testOK:
			self.downstream_elements.changed((self.CHANGED_POLL,))
			if prevOK and self.failCmd:
				os_system('/bin/sh -c "%s" &' % (self.failCmd))

	def enterStandby(self, ConfigElement=None):
		self.testDisabled = True
		from Screens.Standby import inStandby
		inStandby.onClose.insert(0, self.leaveStandby)

	def leaveStandby(self):
		self.testDisabled = False
		self.testTimer.start(50, True)

	def doSuspend(self, suspended):
		if not suspended and \
		   not self.testPause > 0 and \
		   not self.testTimer.isActive():
			self.testTimer.start(100, True)

	@cached
	def getText(self):
		if self.testOK:
			return ONLINE
		return OFFLINE

	@cached
	def getBoolean(self):
		return self.testOK

	text = property(getText)
	boolean = property(getBoolean)
