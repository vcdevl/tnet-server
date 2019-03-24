#!/usr/bin/env python

''' @file : tgNetwork.py
	@brief : Network manager.
'''

import logging
import time
import sys
import os
import subprocess
import json
import string

import ConfigParser
import dbus
import dbus.service
import dbus.mainloop.glib
import gobject

from tggateway.tgModel import Model
import tggateway.tgEvent as tgEvent
import tggateway.tgModem as tgmodem
import tggateway.tgConnman as tgconnman
import tggateway.tgHamachi as tghamachi

INTERFACE_UNKNOWN 	= 0
INTERFACE_ETHERNET 	= 1
INTERFACE_WIFI		= 2
INTERFACE_MOBILE 	= 3

hrInterface = ['None', 'Ethernet', 'Wifi', '3G']

TECHNOLOGY_ETH = '/net/connman/technology/ethernet'
TECHNOLOGY_WIFI = '/net/connman/technology/wifi'
TECHNOLOGY_CELL = '/net/connman/technology/cellular'



class Agent(dbus.service.Object):
	'''	@brief  : Dbus object wrapped by connman simple aganet. '''

	name = None
	ssid = None
	identity = None
	passphrase = None
	wpspin = None
	username = None
	password = None

	@dbus.service.method("net.connman.Agent",
		in_signature='', out_signature='')
	def Release(self):
		loop.quit()

	def input_passphrase(self):
		response = {}

		if self.identity:
			response["Identity"] = self.identity
		if self.passphrase:
			response["Passphrase"] = self.passphrase
		if self.wpspin:
			response["WPS"] = self.wpspin

		return response

	def input_username(self):
		response = {}

		if self.username:
			response["Username"] = self.username
		if self.password:
			response["Password"] = self.password

		return response

	def input_hidden(self):
		response = {}

		if self.name:
			response["Name"] = self.name
		if self.ssid:
			response["SSID"] = self.ssid

		logging.debug('Connman: Input hidden = {}.'.format(response))
		return response

	@dbus.service.method("net.connman.Agent",
		in_signature='oa{sv}', out_signature='a{sv}')
	def RequestInput(self, path, fields):
		response = {}

		if fields.has_key("Name"):
			response.update(self.input_hidden())
		if fields.has_key("Passphrase"):
			response.update(self.input_passphrase())
		if fields.has_key("Username"):
			response.update(self.input_username())

		logging.debug('Connman: Request input = {}.'.format(response))
		return response

	@dbus.service.method("net.connman.Agent",
			in_signature='', out_signature='')
	def Cancel(self):
		pass

def property_changed(name, value):
	"""
	Signal handler for property chaned
	"""
	if name == "State":
		val = str(value)
		if val in ('ready', 'online'):
			loop.quit()
			logging.debug("Connman: Autoconnect callback.")

class ConnmanClient:
	''' @brief  : Connman client class.'''

	def __init__(self, autoconnect_timeout):

		# Setting up bus
		dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

		self.bus = dbus.SystemBus()
		self.manager = dbus.Interface(self.bus.get_object("net.connman", "/"),
			"net.connman.Manager")
		self.technology = dbus.Interface(self.bus.get_object("net.connman",
			"/net/connman/technology/wifi"), "net.connman.Technology")

		self.agent = None

		# Variables
		self.connected = False
		self.autoconnect_timeout = autoconnect_timeout
		self.error = None

	def handle_connect_error(self, error):
		loop.quit()
		self.error = error
		self.connected = False
		logging.debug("Connman: Connect error = {}.".format(error))

	def handle_connect_reply(self):
		loop.quit()
		self.error = None
		self.connected = True
		logging.debug("Connman: Connected.")

	def autoconnect_timeout_handler(self):
		loop.quit()
		self.connected = False
		logging.debug("Connman: Autoconnect timeout.")

	def scan(self):
		scanList = []
		try:
			self.technology.Scan()

			services = self.manager.GetServices()
			logging.debug('Connman: Get wifi networks.')

			for service in services:
				(path, params) = service
				if params['Type'] == 'wifi':
					if 'Name' in params:
						d = {}
						logging.debug('     Found {}'.format(params['Name']))
						d['State'] = params['State']
						d['Name'] = params['Name']
						if 'psk' in params['Security']:
						    d['Security'] = 'WPA-PSK'
						else:
						    d['Security'] = 'Open'

						d['Strength'] = '{:d}'.format(params['Strength'])
						d['Ipv4'] = params['IPv4']
						d['Ipv6'] = params['IPv6']
						logging.debug('			State {}'.format(d['State']))
						logging.debug('         Security {}'.format(d['Security']))
						logging.debug('         RSSI     {}'.format(d['Strength']))
						scanList.append(d)

		except Exception as e:
			logging.error('Connman: Scan error = {}.'.format(e))

		return scanList

	def connect(self, ServiceId, **credentials):
		path = "/net/connman/service/" + ServiceId

		service = dbus.Interface(self.bus.get_object("net.connman", path),"net.connman.Service")

		agentpath = "/test/agent"
		# try unregister first
		try:
			self.manager.UnregisterAgent(agentpath)
		except Exception as e:
			logging.warning("Agent: Registering exception e={}".format(e))

		# ensure agent not already registered
		self.agent = Agent(self.bus, agentpath)
		try:
			self.manager.RegisterAgent(agentpath)
		except Exception as e:
			logging.warning("Agent: Unregister agent exception e={}".format(e))

		if credentials.has_key("name"):
			self.agent.name = credentials["name"]
			logging.debug('Agent: Name given = {}.'.format(credentials["name"]))
		if credentials.has_key("passphrase"):
			#logging.debug('Agent: Passphrase given = {}.'.format(credentials["passphrase"]))
			self.agent.passphrase = credentials["passphrase"]
		if credentials.has_key("identity"):
			logging.debug('Agent: Identity given = {}.'.format(credentials["identity"]))
			self.agent.identity = credentials["identity"]

		service.Connect(timeout=60000,
			reply_handler=self.handle_connect_reply,
			error_handler=self.handle_connect_error)

		global loop
		loop = gobject.MainLoop()
		loop.run()

	def autoconnect(self):
		timeout = gobject.timeout_add(1000*self.autoconnect_timeout, self.autoconnect_timeout_handler)

		signal = self.bus.add_signal_receiver(property_changed,
			bus_name="net.connman",
			dbus_interface="net.connman.Service",
			signal_name="PropertyChanged")

		global loop
		loop = gobject.MainLoop()
		loop.run()

		gobject.source_remove(timeout)
		signal.remove()

	def disconnect(self, ServiceId):

		path = "/net/connman/service/" + ServiceId

		service = dbus.Interface(self.bus.get_object("net.connman", path), "net.connman.Service")

		try:
			service.Disconnect(timeout=60000)
		except Exception as e:
			logging.error("Connman: Remove service error = {}.".format(e))

	def remove(self, ServiceId):

		path = "/net/connman/service/" + ServiceId

		service = dbus.Interface(self.bus.get_object("net.connman", path),
			"net.connman.Service")

		try:
			service.Remove()
		except Exception as e:
			logging.error("Connman: Remove service error = {}.".format(e))

	def getState(self, ServiceId):
		for path,properties in self.manager.GetServices():
			if path == "/net/connman/service/" + ServiceId:
				return properties["State"]

	#def getServiceId(self, name, technology, security, mac_address):
	def getServiceId(self, name):
		'''for path,properties in self.manager.GetServices():
			if properties.get("Name") == name and properties.get("Type") == technology and security in properties.get("Security") and properties.get("Ethernet").get('Address') == mac_address:
				serviceId = path[path.rfind("/") + 1:]
				return serviceId
		logging.error('Connman: Get service id, service not found.')'''
		try:
			servicePath = ''
			services = self.manager.GetServices()

			for service in services:
				(path,params) = service
				if 'Name' in params:
					if params['Name'] == name:
						servicePath = path

			if servicePath == '':
				logging.warning('Connman: Get service id for {} not found.'.format(name))
				return ''

			tokens = servicePath.split('/')

			if len(tokens) != 5 or 'wifi' not in tokens[4]:
				logging.warning('Connman: Get service id for {} is not wifi service.'.format(name))
				return ''

			logging.info('Connman: Get service id for {} = {}.'.format(name, tokens[4]))
			return tokens[4]

		except Exception as e:
			logging.warning('Connman: Get service id for {} error = {}.'.format(name, e))
			return ''


	def setConfig(self, **param):
		config = ConfigParser.RawConfigParser()
		config.optionxform = str
		config.read(CONF_FILE)

		section = "service_"+param['Name']
		config.remove_section(section)
		config.add_section(section)
		config.set(section, "Type", "wifi")
		for item in param:
			if param.has_key(item):
				config.set(section, item, param[item])

		with open(CONF_FILE, 'w') as configfile:
			config.write(configfile)

	def clearConfig(self, name):
		config = ConfigParser.RawConfigParser()
		config.read(CONF_FILE)

		section = "service_"+name
		config.remove_section(section)

		with open(CONF_FILE, 'w') as configfile:
			config.write(configfile)


def getIpAddress(iface):
	''' @fn getIpAddress
	    @brief : Get active interface IP address
	'''

	for i in range(3):
		ifname = "{}{}".format(iface,i)
		try:
			ipaddr = os.popen('ifconfig {} | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1'.format(ifname)).read().strip()
			if string.count(ipaddr, '.') == 3:
				logging.debug('Network: IP address for {} = {}.'.format(ifname, ipaddr))
				return ipaddr
		except Exception as e:
			logging.warning('Network: Get ip addr error {}.'.format(e))

def getDefaultRoute():
	''' @brief : Try determine default route.'''
	try:
		return os.popen('route -n | grep UG | tr -s [:blank:] | cut -d" " -f8').read().strip()
	except:
		logging.debug('Network: Unable to determine default route.')
		return ''

def routeToInterface(route):
	''' @brief : Change gw route to interface. '''

	if 'wlan' in route:
		return INTERFACE_WIFI
	elif 'eth' in route:
		return INTERFACE_ETHERNET
	elif 'wwan' in route:
		return INTERFACE_MOBILE
	else:
		return INTERFACE_UNKNOWN


def httpReply(httpObj=None, responseData={}):
	''' @brief : Return http response '''
	httpObj.setHeader('Content-Type', 'application/json')
	httpObj.setResponseCode(200, 'OK')
	httpObj.write(json.dumps(responseData).encode('UTF-8'))
	httpObj.finish()







class Network(Model):
	''' Network adapter to manage network interfaces '''

	def __init__(self, eventMgr=None):
		super(Network, self).__init__('Network')
		self.eventMgr = eventMgr
		# can report metrics at different configurable frequency
		self.currentInterface = INTERFACE_UNKNOWN
		self.ipAddress = ''

		logging.info('Network: Initialised.')

	def getLiveState(self):
		''' Get live state. '''

		status = '{},{}'.format(hrInterface[self.currentInterface], self.ipAddress)
		return status

	def run(self):
		''' Checks network metrics '''

		lasttime = 0
		while True:

			time.sleep(1)

			if self.stopThread:
				break

			if time.time() - lasttime < 10:
				continue

			# run modem loop
			tgmodem.loop()

			# get default Internet route
			route_iface, ip_addr = tgconnman.get_route()

			logging.debug('Network: Default Internet route={}, ip_address={}.'.format(route_iface, ip_addr))

			if any(x in route_iface for x in ['eth', 'wlan', 'wwan']):
				newInterface = routeToInterface(route_iface)
				if newInterface != self.currentInterface:
					self.eventMgr.raiseEvent(tgEvent.EVCLASS_NETWORK,
											tgEvent.EVTOPIC_NET_IFACECHANGE,
											'{},{}'.format(hrInterface[ self.currentInterface ], hrInterface[ newInterface ]),
											tgEvent.EVENT_PRIORITY_HIGH,
											[tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])

				# if changing from no interface to an interface, do hamachi logout/login
				if self.currentInterface == INTERFACE_UNKNOWN:
					tghamachi.logout()
					tghamachi.login()

				self.currentInterface = newInterface

				# cut the number off
				if ip_addr:
					self.ipAddress = ip_addr
				else:
					self.ipAddress = ''

			else:
				# from some interface to no interface
				if self.currentInterface != INTERFACE_UNKNOWN:

					# Probably can't stream this event due to network being down
					self.eventMgr.raiseEvent(tgEvent.EVCLASS_NETWORK,
											tgEvent.EVTOPIC_NET_IFACECHANGE,
											'{},{}'.format(hrInterface[ self.currentInterface ], hrInterface[ INTERFACE_UNKNOWN ]),
											tgEvent.EVENT_PRIORITY_HIGH,
											[tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])

					# logout from hamachi too as it just reports as still logged in
					tghamachi.logout()

				self.currentInterface = INTERFACE_UNKNOWN
				self.ipAddress = ''


			lasttime = time.time()
