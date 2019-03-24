import cmd
import sys
import logging
import dbus
import signal

ConnmanServiceStates = ('idle', 'failure', 'disconnect', 'association', 'configuration', 'ready', 'online')

def get_services():
	''' List all services '''

	services = {}
	try:
		bus = dbus.SystemBus()
		manager = dbus.Interface(bus.get_object("net.connman", "/"), "net.connman.Manager")
		for path, properties in manager.GetServices():
			services[path] = properties
	except Exception as e:
		logging.error(e)

	return services

def get_cellular_service_path():
	''' Get full path for a cellular service if there is one '''

	services = get_services()
	for service in services.keys():
		if 'cellular' in service:
			return service

	return None

def get_online_services():
	''' Get online services. Online services are determined by thier State flag.
		NOTE: A "ready" service is connected but may not have the default Internet route
			  An "online" service has been verified using a small HTTP GET request
		NOTE: EnableOnlineCheck=true (default setting) in configuration file that will use
				HTTP GET to test for Internet connectivity via the interface
	'''

	services = get_services()
	online_services = {}
	for path in services.keys():
		if 'Type' in services[path] and 'State' in services[path]:
			for type in ['wifi', 'ethernet', 'cellular']:
				if services[path]['Type'] == type and services[path]['State'] == 'online':
					online_services[path] = {'Type':type, 'Name':None, 'IPv4':None}
					if 'Name' in services[path]:
						online_services[path]['Name'] = services[path]['Name']
					if 'IPv4' in services[path] and 'Address' in services[path]['IPv4']:
						online_services[path]['IPv4'] = services[path]['IPv4']['Address']

	return online_services

def wifi_or_ethernet_online():
	''' From online services list, are any wifi or ethernet '''

	online_services = get_online_services()
	for path in online_services.keys():
		if online_services[path]['Type'] in 'wifi' or online_services[path]['Type'] in 'ethernet':
			return True

	return False

def wifi_online():
	''' From online services list, are any wifi '''

	online_services = get_online_services()
	for path in online_services.keys():
		if online_services[path]['Type'] in 'wifi':
			return True

	return False

def ethernet_online():
	''' From online services list, are any ethernet '''

	online_services = get_online_services()
	for path in online_services.keys():
		if online_services[path]['Type'] in 'ethernet':
			return True

	return False

def get_route():
	''' Get Internet route '''

	online_services = get_online_services()
	for path in online_services.keys():
		if online_services[path]['Type'] in 'ethernet':
			return ('eth', online_services[path]['IPv4'])
		elif online_services[path]['Type'] in 'wifi':
			return ('wlan', online_services[path]['IPv4'])
		elif online_services[path]['Type'] in 'cellular':
			return ('wwan', online_services[path]['IPv4'])

	return (None,None)

def wifi_scan():
	''' Scan for surrounding wifi networks '''

	wifi_scan_results = {}
	try:
		bus = dbus.SystemBus()
		wifi_tech = dbus.Interface(bus.get_object("net.connman", "/net/connman/technology/wifi"), "net.connman.Technology")
		wifi_tech.Scan()
	except Exception as e:
		logging.error(e)

	# filter the wifi services from get_services() call
	services = get_services()
	for path in services.keys():
		if 'Type' in services[path] and services[path]['Type'] == 'wifi':
			wifi_scan_results[path] = {'Name':None, 'State': None, 'Security': None, 'AutoConnect': None, 'IPv4': None, 'Strength': None }
			if 'Name' in services[path]:
				wifi_scan_results[path]['Name'] = services[path]['Name']
			if 'State' in services[path]:
				wifi_scan_results[path]['State'] = services[path]['State']
			if 'Security' in services[path]:
				wifi_scan_results[path]['Security'] = services[path]['Security']
			if 'Strength' in services[path]:
				wifi_scan_results[path]['Strength'] = services[path]['Strength']
			if 'AutoConnect' in services[path]:
				wifi_scan_results[path]['AutoConnect'] = services[path]['AutoConnect']
			if 'IPv4' in services[path] and 'Address' in services[path]['IPv4']:
				wifi_scan_results[path]['IPv4'] = services[path]['IPv4']['Address']

	return wifi_scan_results

def connect_service(service_path):
	''' Connect to a service given by the service path
		Service path examples
			/net/connman/service/wifi_5cf3701a9bdc_43686f77506f6f_managed_psk
			/net/connman/service/ethernet_36e6481dbd73_cable
	'''

	services = get_services()

	for path in services.keys():
		if 'State' in services[path] and 'online' in services[path]['State'] and service_path == path:
			logging.debug("Service {} already online".format(service_path))
			return True

	try:
		bus = dbus.SystemBus()
		connman_service = dbus.Interface(bus.get_object("net.connman", service_path),"net.connman.Service")
		connman_service.Connect()
		return True

	except Exception as e:
		logging.error(e)
		return False

def disconnect_service(service_path):
	''' Disconnect a service given by the service path '''

	try:
		bus = dbus.SystemBus()
		connman_service = dbus.Interface(bus.get_object("net.connman", service_path),"net.connman.Service")
		connman_service.Disconnect()
		return True

	except Exception as e:
		logging.error(e)
		return False

def service_state(service_path):
	''' Check if the state of service given by service path '''

	services = get_services()

	state = 'unknown'
	for path in services.keys():
		if path == service_path and 'State' in services[path] and services[path]['State'] in ConnmanServiceStates:
			logging.debug('Service {} state = {}'.format(service_path, services[path]['State']))
			state = services[path]['State']

	return state

def is_online():
	''' Check if there is Internet connectivity '''

	online = False
	try:

		bus = dbus.SystemBus()
		connman_manager = manager = dbus.Interface(bus.get_object("net.connman", "/"),"net.connman.Manager")
		properties = connman_manager.GetProperties()
		if 'State' in properties:
			if properties['State'] == 'online':
				online = True
	except Exception as e:
		logging.error(e)

	return online


class Cli(cmd.Cmd):

	intro = 'Welcome to the Connman cli. Type help or ? to list commands.\n'
	prompt = '(Connman) '
	file = None

	def do_list_technologies(self, arg):
		''' List technologies '''

	def do_enable_technology(self, arg):
		''' Enable a technology '''

	def do_disable_technology(self, arg):
		''' Disable a technology '''

	def do_show_services(self, arg):
		''' List connman services and their properties '''

		services = get_services()
		print('Found {} services'.format(len(services)))
		print('')
		for path in services.keys():
			print(path)
			print('---------------------------------------------------------------------------')
			for pty in services[path].keys():
				print('{} = {}'.format(pty, services[path][pty]))
			print('')

	def do_show_service_paths(self, arg):
		''' List only the connman service paths '''

		services = get_services()
		for path in services:
			print(path)

	def do_show_online_services(self, arg):
		''' Show online services '''

		online_services = get_online_services()
		print('Found {} online services'.format(len(online_services)))
		for path in online_services:
			print(path)
			print('---------------------------------------------------------------------------')
			if online_services[path]['Type']:
				print('	Type={}'.format(online_services[path]['Type']))
			if online_services[path]['Name']:
				print('	Name={}'.format(online_services[path]['Name']))
			print('')

	def do_check_wifi_or_ethernet_online(self, arg):
		''' Check if there is an online wifi or ethernet service '''

		if wifi_or_ethernet_online():
			print('Yes')
		else:
			print('No')

	def do_get_route(self, arg):
		''' Get Internet route '''

		iface, ip_addr = get_route()
		print('Current Internet route interface={}, ip address={}'.format(iface, ip_addr))

	def do_scan_wifi(self, arg):
		''' Scan wifi for services'''

		scan_result = wifi_scan()
		print('Found {} wifi services'.format(len(scan_result)))
		for path in scan_result.keys():
			print(path)
			print('---------------------------------------------------------------------------')
			if scan_result[path]['Name']:
				print('	Name={}'.format(scan_result[path]['Name']))
			if scan_result[path]['State']:
				print('	State={}'.format(scan_result[path]['State']))
			if scan_result[path]['Security']:
				print('	Security={}'.format(scan_result[path]['Security']))
			if scan_result[path]['Strength']:
				print('	Strength={:d}'.format(scan_result[path]['Strength']))
			if scan_result[path]['AutoConnect']:
				print('	AutoConnect={}'.format(scan_result[path]['AutoConnect']))
			if scan_result[path]['IPv4']:
				print('	IPv4={}'.format(scan_result[path]['IPv4']))
			print('')

	def do_connect_service(self, arg):
		''' Connect to a service '''

	def do_disconnect_service(self, arg):
		''' Disconnect from a service '''

	def do_check_connectivity(self, arg):
		''' Check for Internet connection '''

		if is_online():
			print('Internet connection = true')
		else:
			print('Internet connection = false')

	def do_quit(self, arg):
		''' Quit connman '''
		sys.exit()


def process_arg(arg):
	if '=' in arg:
		return arg.split('=')
	else:
		return arg

def parse(arg):
	'Convert a series of zero or more numbers to an argument tuple'
	return tuple(map(process_arg, arg.split()))

def quit(signal, frame):
	''' Quit application '''
	logging.info('Exiting')
	sys.exit()


if __name__ == "__main__":

	# signal handlers
	signal.signal( signal.SIGINT, quit )
	signal.signal( signal.SIGTERM, quit )

	# root logger
	logger = logging.getLogger('')
	logger.setLevel(logging.DEBUG)

	# format for logging
	format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

	# output to file
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(format)
	logger.addHandler(handler)
	logging.info('Starting')

	Cli().cmdloop()
