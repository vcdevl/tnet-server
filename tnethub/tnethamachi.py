''' Hamachi adapter '''

import sys
import os
import logging
import logging.handlers
import subprocess
import json
import copy
import time
import cmd
from functools import wraps

from tggateway.tgUtils import Systemd


HAMACHID_OFF		= 0
HAMACHID_RUNNING	= 1

HAMACHI_ERR         = 0
HAMACHI_NOT_RUNNING = 0
HAMACHI_OFFLINE     = 0
HAMACHI_LOGGING_IN  = 0
HAMACHI_LOGGED_IN   = 1

HAMACHI_CONFIG_FILE = '/home/tgard/config/hamachi.json'

hamachi_config = {}
hamachi_client_online = HAMACHI_OFFLINE
hamachi_client_status = {}

hamachi_model = None



def process_ham_status(out):
	''' helper method to separate two fields by : '''

	if ':' in out:
		items = out.split(':')
		items[0] = items[0].strip()
		items[1] = items[1].strip()
		return items
	else:
		return None

def service_state():
	''' get hamachi service state '''

	sysd = Systemd()
	return sysd.unit_active('logmein-hamachi')

def service_start():
	''' start hamachi service '''

	sysd = Systemd()
	sysd.unit_start('logmein-hamachi')

def service_stop():
	''' stop hamachi service '''

	sysd = Systemd()
	sysd.unit_stop('logmein-hamachi')


def login():
	''' login to hamachi client '''

	try:
		logging.info('Logging into hamachi')
		p = subprocess.Popen(['hamachi', 'login'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is None:
			logging.info('Logged into hamachi')
			return True
		else:
			logging.warning(err)
			return False
	except Exception as e:
		logging.error(e)
		return False

def logout():
	''' logout of hamachi client '''

	try:
		logging.info('Logging out of hamachi')
		p = subprocess.Popen(['hamachi', 'logout'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is None:
			logging.info('Logged out of hamachi')
			return True
		else:
			logging.warning(err)
			return False
	except Exception as e:
		logging.error(e)
		return False

def join(network_id, password):
	''' join a hamachi network '''

	try:
		logging.info('Joining hamachi network {}'.format(network_id))
		p = subprocess.Popen(['hamachi', 'join', network_id, password], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is None:
			logging.info('Joined hamachi network')
			return True
		else:
			logging.warning(err)
			return False

	except Exception as e:
		logging.error(e)
		return False

def leave(network_id):
	''' leave hamachi network '''

	try:
		logging.info('Leaving hamachi network {}'.format(network_id))
		p = subprocess.Popen(['hamachi', 'leave', network_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is None:
			logging.info('Left hamachi network')
			return True
		else:
			logging.warning(err)
			return False

	except Exception as e:
		logging.error(e)
		return False

def set_nickname(name):
	''' set hamachi client nickname '''

	try:
		logging.info('Setting hamachi nickname to {}'.format(name))
		p = subprocess.Popen(['hamachi', 'set-nick', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is None:
			logging.info('Set hamachi nickname')
			return True
		else:
			logging.warning(err)
			return False
	except Exception as e:
		logging.error(e)
		return False

def factory_reset():
	''' reset hamachi to factory default by stopping service and clearing all related files '''

	try:
		logging.info('Setting hamachi to factory default')
		logout()
		service_stop()
		# remove logmein-hamachi config files
		p = subprocess.Popen(['rm', '/usr/lib/logmein-hamachi/*'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = p.communicate()
		if err is not None:
			logging.info('Set hamachi to factory default')
		else:
			logging.warning(err)

		# remove config file
		if os.path.exists(HAMACHI_CONFIG_FILE):
			os.remove(HAMACHI_CONFIG_FILE)

		return True
	except Exception as e:
		logging.error('Hamachi: Unexpected error {0}.'.format(e))
		return False

def load_config():
	''' load configuration from file '''

	global hamachi_config

	try:
		with open(HAMACHI_CONFIG_FILE, 'r') as f:
			hamachi_config = json.load(f)

		logging.debug('Hamachi config:')
		logging.debug('	Net ID: {}.'.format(hamachi_config['NetId']))
		logging.debug('	Client ID: {}.'.format(hamachi_config['ClientId']))
		logging.debug('	Join pass: {}.'.format(hamachi_config['NetPass']))
		logging.debug('	Ip address: {}.'.format(hamachi_config['Ipv4']))
		logging.debug('	Version: {}.'.format(hamachi_config['Version']))

		return True

	except Exception as e:
		logging.error(e)
		return False


def dump_config():
	''' save configuration to file '''

	global hamachi_config

	try:
		with open(HAMACHI_CONFIG_FILE, 'w') as f:
			json.dump(hamachi_config, f)

		logging.info('Save hamachi config to file')
		return True
	except Exception as e:
		logging.error(e)
		return False

def set_config(config):
	''' update config '''

	global hamachi_config

	backup = copy.deepcopy(hamachi_config)
	hamachi_config.clear()
	try:
		hamachi_config	= config

		logging.debug('New hamachi config {}'.format(hamachi_config))
		# validate

		dump_config()

		return True
	except Exception as e:
		logging.error(e)
		# restore previous
		hamachi_config = copy.deepcopy(backup)
		return False

def get_config():
	''' get config '''

	global hamachi_config
	return copy.deepcopy(hamachi_config)

def get_live_state():
	''' get current state of hamachi'''

	global hamachi_client_online
	return copy.copy(hamachi_client_online)

def read_client_status():
	''' read hamachi client status '''
	global hamachi_client_status

	try:

		p = subprocess.Popen(["hamachi"], stdout=subprocess.PIPE, stdout=subprocess.PIPE)
		out, err = p.communicate()

		if err is not None:
			logging.warning(err)
			return None

		if '\n' not in out:
			logging.info('No lines in output of Hamachi status')
			return None

		# process out
		info = tuple(map(process_ham_status, out.split('\n')))

		for item in info:
			if item is None:
				continue
			if item[0] is None:
				continue
			if 'version' in item[0]:
				hamachi_client_status['version'] = item[1]
			if 'pid' in item[0]:
				hamachi_client_status['pid'] = item[1]
			if 'status' in item[0]:
				hamachi_client_status['status'] = item[1]
			if 'address' in item[0]:
				hamachi_client_status['address'] = item[1]
			if 'nickname' in item[0]:
				hamachi_client_status['nickname'] = item[1]

		hamachi_client_status['lastupdate'] = int(time.time())
		logging.debug('Hamachi state: address={}, nickname={}, status={}, time={}'.format(
			hamachi_client_status['address'],
			hamachi_client_status['nickname'],
			hamachi_client_status['status'],
			hamachi_client_status['lastupdate']))
	except Exception as e:
		logging.error(e)




if __name__ == "__main__":

	# root logger
	logger = logging.getLogger('')
	logger.setLevel(logging.DEBUG)

	# format for logging
	format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

	# add stdout stream handler
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(format)
	logger.addHandler(handler)

	class Cli(cmd.Cmd):

		intro = 'Hamachi cli. Type help or ? to list commands.\n'
		prompt = '(Hamachi) '
		file = None

		def do_service_state(self, arg):
			''' Show state of logmein-hamachi service '''
			service_state()

		def do_service_start(self, arg):
			''' Start logmein-hamachi service '''
			service_start()

		def do_service_stop(self, arg):
			''' Stop logmein-hamachi service '''
			service_stop()

		def do_login(self, arg):
			''' Login to hamachi client '''
			login()

		def do_logout(self, arg):
			''' Logout of hamachi client '''
			logout()

		def do_join(self, arg):
			''' Join hamachi network <id> <password> '''
			argmap = parse(arg)

			id = ''
			passw = ''
			for a in argmap:
				if 'id' in a[0]:
					id = a[1]
				if 'pass' in a[0]
					passw = a[1]

			if not 'id':
				print('Id is not valid')
				return

			join(id, passw)

		def do_leave(self, arg):
			''' Leave hamachi network <id> '''

			argmap = parse(arg)

			id = ''
			for a in argmap:
				if 'id' in a[0]:
					id = a[1]

			if not 'id':
				print('Id is not valid')
				return

			leave(id)

		def do_set_nickname(self, arg):
			''' Set nickname of hamachi client <name> '''

			argmap = parse(arg)

			name = ''
			for a in argmap:
				if 'name' in a[0]:
					name = a[1]

			if not 'name':
				print('Name is not valid')
				return

			set_nickname(name)

		def do_load_config(self, arg):
			''' load configuration from file '''
			load_config()

		def do_client_status(self, arg):
			''' get status of hamachi client '''
			read_client_status()

		def do_quit(self, arg):
			''' Quit hamachi '''
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
		print('Exiting')
		sys.exit()

	Cli().cmdloop()

else:
	from tggateway.tgModel import Model
	import tggateway.tgevent as tgevent

	def is_client_online():
		''' Check if hamachi client is online '''

		global hamachi_client_status
		global hamachi_client_online

		try:
			read_client_status()
			time_elapsed = int(time.time()) - hamachi_client_status['lastupdate']
			if time_elapsed > 30:
				logging.warning('Hamachi status read out of sync, last status read {} seconds ago. Ignoring'.format(time_elapsed))
				return

			if 'status' not in hamachi_client_status:
				logging.warning('Hamachi status contains no status field')
				return

			if 'logged in' == hamachi_client_status['status']:
				if hamachi_client_online != HAMACHI_LOGGED_IN:
					tgevent.event_raise(tgevent.EVCLASS_HAMACHI, tgevent.EVTOPIC_HAM_ONLINE, '', tgevent.EVENT_PRIORITY_HIGH, [tgevent.EVACTION_DATABASE])
				hamachi_client_online = HAMACHI_LOGGED_IN
				logging.debug('Hamachi client logged in')

			elif 'logging in' == hamachi_client_status['status']:
				hamachi_client_online = HAMACHI_LOGGING_IN
				logging.debug('Hamachi client logging in ...')

			else:
				if hamachi_client_online == HAMACHI_LOGGED_IN:
					tgevent.event_raise(tgevent.EVCLASS_HAMACHI, tgevent.EVTOPIC_HAM_OFFLINE, '', tgevent.EVENT_PRIORITY_HIGH, [tgevent.EVACTION_DATABASE])
				hamachi_client_online = HAMACHI_OFFLINE
				logging.info('Hamachi client logged out')

		except Exception as e:
			logging.error(e)

	class Hamachi(Model):
		def __init__(self):

			super(Hamachi, self).__init__('Hamachi')

			global hamachi_config
			global hamachi_client_status
			global hamachi_client_online

			hamachi_config = {}
			if not load_config():
				tgevent.event_raise(tgevent.EVCLASS_HAMACHI, tgevent.EVTOPIC_HAM_NO_CONFIG, '', tgevent.EVENT_PRIORITY_HIGH, [tgevent.EVACTION_DATABASE])
			hamachi_client_status = {'lastupdate': 0}

			logging.info('Hamachi initialised')

		def run(self):
			''' main run method in model thread '''

			global hamachi_client_online

			is_client_online()
			lasttime = 0
			stillLoggingIn = 0

			while True:

				time.sleep(1)

				if self.stopThread:
					break

				if time.time() - lasttime < 10:
					continue

				is_client_online()

				if hamachi_client_online == HAMACHI_OFFLINE:
					login()
					stillLoggingIn = 0

				elif hamachi_client_online == HAMACHI_LOGGING_IN:
					# if hamachi saying its still logging in after 1 minutes, try logout and then login again.
					stillLoggingIn += 1
					if stillLoggingIn == 5:
						stillLoggingIn = 0
						logout()
						service_stop()
						service_start()
						login()
				else:
					stillLoggingIn = 0

				lasttime = time.time()

	def start_hamachi():
		''' start hamachi runtime handler '''
		global hamachi_model
		hamachi_model = Hamachi()
		hamachi_model.start()

	def stop_hamachi():
		''' stop hamachi runtime handler '''
		global hamachi_model
		hamachi_model.stop()
