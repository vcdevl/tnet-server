''' @file : tgModem
'''

import logging
import time
import sys
import os
import signal
import json
import dbus

import tggateway.tgUtils as tgutils
import tggateway.tgConnman as tgconman

MODEM_GPIO_PIN = "13"
MODEM_GPIO_PIN_LONG = "gpio13_pi14"

no_ofono_dbus_counter = 0
ofono = None

class Ofono():

	UNIT_NAME = "ofono.service"

	def __init__(self):
		self._properties = {"Name":"",
			"Manufacturer": "",
			"Model": "",
			"Imei":"",
			"Revision":"",
			"Serial": "",
			"Powered": 0,
			"Online": 0,
			"Lockdown": 0,
			"Emergency": 0}

	def power_on(self):
		tgutils.gpio_enable(MODEM_GPIO_PIN, MODEM_GPIO_PIN_LONG)
		tgutils.gpio_set_value(MODEM_GPIO_PIN_LONG, '1')
		logging.debug("Turning modem on")

	def power_off(self):
		tgutils.gpio_enable(MODEM_GPIO_PIN, MODEM_GPIO_PIN_LONG)
		tgutils.gpio_set_value(MODEM_GPIO_PIN_LONG, '0')
		logging.debug("Turning modem off")

	def modem_is_powered(self):
		''' Check modem is powered '''

		if tgutils.gpio_get_value(MODEM_GPIO_PIN_LONG) == '1':
			return True
		else:
			return False

	def get_properties(self):
		try:
			bus = dbus.SystemBus()
			mgr = dbus.Interface(bus.get_object('org.ofono', '/'),'org.ofono.Manager')
			modems = mgr.GetModems()
			modem = dbus.Interface(bus.get_object('org.ofono', modems[0][0]),'org.ofono.Modem')

			#modem.connect_to_signal("PropertyChanged", property_changed)

			properties = modem.GetProperties()

			if 'Name' in properties:
				self._properties["Name"] = properties['Name']

			if 'Manufacturer' in properties:
				self._properties["Manufacturer"] = properties['Manufacturer']

			if 'Model' in properties:
				self._properties["Model"] = properties['Model']

			if 'Revision' in properties:
				self._properties["Revision"] = properties['Revision']

			if 'Serial' in properties:
				self._properties["Serial"] = properties['Serial']

			if 'Powered' in properties:
				self._properties["Powered"] = properties['Powered']

			if 'Online' in properties:
				self._properties["Online"] = properties['Online']

			if 'Lockdown' in properties:
				self._properties["Lockdown"] = properties['Lockdown']

			if 'Emergency' in properties:
				self._properties["Emergency"] = properties['Emergency']

			'''if 'Features' in properties:
				logging.debug("Features:")
				for feature in properties["Features"]:
					logging.debug("    [ {} ]".format(feature))

			if 'Interfaces' in properties:
				logging.debug("Interfaces:")
				for interface in properties["Interfaces"]:
					logging.debug("    [ {} ]".format(interface))'''

		except Exception as e:
			logging.error(e)

	def modem_info(self):
		self.get_properties()

		for key in self._properties:
			logging.debug("{} = {}".format(key, self._properties[key]))

	def modem_is_online(self):
		self.get_properties()
		if self._properties["Online"]:
			logging.debug("Modem online")
			return True
		else:
			logging.debug("Modem offline")
			return False

	def service_on(self):
		sysd = tgutils.Systemd()
		if not sysd.unit_active(self.UNIT_NAME):
			sysd.unit_start(self.UNIT_NAME)

	def service_off(self):
		sysd = tgutils.Systemd()
		if sysd.unit_active(self.UNIT_NAME):
			sysd.unit_stop(self.UNIT_NAME)

	def service_state(self):
		sysd = tgutils.Systemd()
		if sysd.unit_active(self.UNIT_NAME):
			logging.debug('Service active')
			return True
		else:
			logging.debug('Service not active')
			return False

	def set_apn(self, apn):
		logging.debug("Setting APN to {}".format(apn))
		try:
			bus = dbus.SystemBus()
			manager = dbus.Interface(bus.get_object('org.ofono', '/'),'org.ofono.Manager')
			modems = manager.GetModems()

			for path, properties in modems:
				if "org.ofono.ConnectionManager" not in properties["Interfaces"]:
					continue

				connman = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.ConnectionManager')
				contexts = connman.GetContexts()
				path = "";

				for i, properties in contexts:
					if properties["Type"] == "internet":
						path = i
						break

				if path == "":
					path = connman.AddContext("internet")
					logging.debug("Created new context {}".format(path))
				else:
					logging.debug("Found context {}".format(path))

				context = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.ConnectionContext')

				get_apn = context.GetProperties()["AccessPointName"]

				if get_apn == apn:
					logging.debug("APN already set to {}".format(apn))
					return

				context.SetProperty("AccessPointName", apn)
				logging.info("Setting APN to {}".format(apn))

		except Exception as e:
			logging.error(e)

	def data_connect(self):
		try:
			bus = dbus.SystemBus()
			manager = dbus.Interface(bus.get_object('org.ofono', '/'),'org.ofono.Manager')
			modems = manager.GetModems()
			path = modems[0][0]
			modem = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.Modem')
			modem.SetProperty("Online", dbus.Boolean(1), timeout = 120)
		except Exception as e:
			logging.error(e)

	def data_disconnect(self):
		try:
			bus = dbus.SystemBus()
			manager = dbus.Interface(bus.get_object('org.ofono', '/'),'org.ofono.Manager')
			modems = manager.GetModems()
			path = modems[0][0]
			modem = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.Modem')
			modem.SetProperty("Online", dbus.Boolean(0), timeout = 120)
		except Exception as e:
			logging.error(e)

	def send_sms(self, recipient, message):
		logging.debug('Sending message {} to {}'.format(message, recipient))
		bus = dbus.SystemBus()
		manager = dbus.Interface(bus.get_object('org.ofono', '/'),'org.ofono.Manager')
		modems = manager.GetModems()
		path = modems[0][0]
		mm = dbus.Interface(bus.get_object('org.ofono', path), 'org.ofono.MessageManager')

		#if len(sys.argv) == 5:
		#	mm.SetProperty("UseDeliveryReports", dbus.Boolean(int(sys.argv[4])))
		#	path = mm.SendMessage(sys.argv[2], sys.argv[3])
		#else:
		#mm.SetProperty("UseDeliveryReports", dbus.Boolean(int(sys.argv[3])))
		path = mm.SendMessage(recipient, message)



def _connect():

	global ofono
	if ofono is None:
		ofono = Ofono()

	# enable power to modem
	if not ofono.modem_is_powered():
		ofono.power_on()

	# start the ofono service
	if not ofono.service_state():
		ofono.service_on()

	# set the APN
	# TODO: change for other sim providers
	ofono.set_apn('telstra.internet')

	# connect data
	ofono.data_connect()

	# get connman cellular service path
	cell_service_path = tgconman.get_cellular_service_path()

	if cell_service_path is None:
		# Added this counter due to some unknown reason cellular service missing in connman service list
		# If happens 5 consecutive times, power off modem and restart again
		no_ofono_dbus_counter += 1
		logging.warning('No cellular service path in connman, no ofono dbus count ={}'.format(no_ofono_dbus_counter))
		if no_ofono_dbus_counter >= 5:
			no_ofono_dbus_counter = 0
			ofono.service_off()
			ofono.power_off()

		return
	else:
		no_ofono_dbus_counter = 0

	# connect connman cellular service
	tgconman.connect_service(cell_service_path)

	# check connman state
	if tgconman.is_online():
		logging.info('Connman is online')
	else:
		logging.warning('Connman is not online')


def _disconnect():

	global ofono
	if ofono is None:
		ofono = Ofono()

	ofono.data_disconnect()

	if ofono.service_state():
		ofono.service_off()

	if ofono.modem_is_powered():
		ofono.power_off()

def loop():

	if not tgconman.wifi_or_ethernet_online():
		_connect()
	else:
		_disconnect()





def signalHandler(signal,frame):
	logging.info("Exiting")

if __name__ == "__main__":

	# signal handlers
	signal.signal( signal.SIGINT, signalHandler )
	signal.signal( signal.SIGTERM, signalHandler )

	# root logger
	logger = logging.getLogger('')
	logger.setLevel(logging.DEBUG)

	# format for logging
	format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

	# output to file
	stdouth = logging.StreamHandler(sys.stdout)
	stdouth.setFormatter(format)
	logger.addHandler(stdouth)

	# create Ofono
	ofono = Ofono()

	# argument handling
	'''parser = argparse.ArgumentParser(prog='Modem manager')
	parser.add_argument('--modem-on', action='store_false', dest='modem-on', default=False, help='Power on modem')
	parser.add_argument('--modem-off', action='store_false', dest='modem-off', default=False, help='Power off modem')
	parser.add_argument('--modem-powered', action='store_false', dest='modem-powered', default=False, help='Check if modem powered')
	parser.add_argument('--modem-info', action='store_false', dest='modem-info', default=False, help='List modem information')
	parser.add_argument('--ofono-service-on', action='store_false', dest='ofono-on', default=False, help='Start Ofono systemd service')
	parser.add_argument('--ofono-service-off', action='store_false', dest='ofono-off', default=False, help='Stop Ofono systemd service')
	parser.add_argument('--ofono-service-state', action='store_false', dest='ofono-state', default=False, help='Check Ofono systemd service state')
	args = parser.parse_args()
	print(args)'''

	arg_action = {'--modem-on': ofono.power_on,
				'--modem-off': ofono.power_off,
				'--modem-powered': ofono.modem_is_powered,
				'--modem-info': ofono.modem_info,
				'--ofono-on': ofono.service_on,
				'--ofono-off': ofono.service_off,
				'--ofono-state': ofono.service_state,
				'--internet-set-apn': ofono.set_apn,
				'--internet-connect': ofono.data_connect,
				'--internet-disconect': ofono.data_disconnect,
				'--sim-send-sms': ofono.send_sms}

	for arg in sys.argv:
		for opt in arg_action:
			if opt in arg:
				if arg.__contains__('='):
					kv = arg.split('=')
					arg_action[kv[0]](kv[1])
				else:
					arg_action[arg]()
