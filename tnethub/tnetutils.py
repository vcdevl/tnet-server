import logging
import os
import dbus

def gpio_enable(pin, pinLong):

	if os.path.exists('/sys/class/gpio/' + pinLong + '/direction'):
		logging.debug("GPIO %s already configured", pinLong)
		return
	else:
		with open('/sys/class/gpio/export', 'w') as the_file:
			the_file.write(pin + '\n')
		#Set direction
		with open('/sys/class/gpio/' + pinLong + '/direction', 'w') as the_file:
			the_file.write('out\n')
		logging.debug("GPIO %s configured", pinLong)
		return

def gpio_set_value(pinLong, value):
	logging.debug("Setting GPIO %s to %s", pinLong, value)
	with open('/sys/class/gpio/' + pinLong + '/value', 'w') as the_file:
		the_file.write(value + '\n')
	return

def gpio_get_value(pinLong):

	with open('/sys/class/gpio/' + pinLong + '/value', 'r') as the_file:
		return the_file.read().strip()


class Systemd():

	UNIT_INTERFACE = "org.freedesktop.systemd1.Unit"

	def __init__(self):

		self._bus = None
		self._interface = None
		try:
			self._bus = dbus.SystemBus()
			proxy = self._bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
			self._interface = dbus.Interface(proxy, "org.freedesktop.systemd1.Manager")
		except dbus.exceptions.DBusException as e:
			logging.error(e)

	def get_unit_properties(self, unit_name, unit_interface):

		if self._interface is None:
			return None

		try:
			unit_path = self._interface.LoadUnit(unit_name)

			proxy = self._bus.get_object("org.freedesktop.systemd1", unit_path)

			properties_interface = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")

			return properties_interface.GetAll(unit_interface)

		except dbus.exceptions.DBusException as e:
			logging.error(e)
			return None

	def unit_start(self, unit_name, mode="replace"):

		if self._interface is None:
			return False

		try:
			self._interface.StartUnit(unit_name, mode)
			return True
		except dbus.exceptions.DBusException as e:
			logging.error(e)
			return False

	def unit_stop(self, unit_name, mode="replace"):

		if self._interface is None:
			return False

		try:
			self._interface.StopUnit(unit_name, mode)
			return True
		except dbus.exceptions.DBusException as e:
			logging.error(e)
			return False

	def unit_active(self, unit_name):

		properties = self.get_unit_properties(unit_name, self.UNIT_INTERFACE)

		if properties is None:
			return False

		try:
			state = properties["ActiveState"].encode("utf-8")
			if state == "active":
				return True
			else:
				return False
		except KeyError:
			return False
