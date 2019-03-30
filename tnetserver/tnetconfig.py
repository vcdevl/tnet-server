import logging
import json
import copy
import sys
import os

CONFIG_FILE 		= '/etc/default/tnetserver.conf'

tnet_config = {
	'mqtt':{
		'port': 34512
	},
	'log': {
		'level': 0,
		'dest': 'stdout'
	},
	'database': {
		'type': 'file',
		'path': '/home/tgard/'
	}
}

def load_config():
	''' load configuration '''

	global tnet_config
	config = None

	if not os.path.exists(CONFIG_FILE):
		logging.info('Config {} file does not exist'.format(CONFIG_FILE))
		return

	with open(CONFIG_FILE, 'r') as f:
		config = json.load(f)

	if 'mqtt' in config and 'port' in config['mqtt']:
		tnet_config['mqtt']['port'] = config['mqtt']['port']

	if 'log' in config:
		if 'level' in config['log'] and config['log']['level'] >= logging.DEBUG and config['log']['level'] < logging.CRITICAL:
			tnet_config['log']['level'] = config['log']['level']

		if 'dest' in config['log'] and config['log']['dest'] == 'file' or config['log']['dest'] == 'stdout':
			tnet_config['log']['dest'] = config['log']['dest']

	if 'database' in config:
		if 'type' in config['database'] and config['database']['type'] == 'file' or config['database']['type'] == 'mongo':
			tnet_config['database']['type'] = config['database']['type']

		if 'path' in config['database']:
			tnet_config['database']['path'] = config['database']['path']

def test_setup(path):
	''' called by test framework to as part of the setup/teardown '''
	global tnet_config
	tnet_config['database']['path'] = path

def test_teardown():
	pass

def get_config():
	''' get config '''
	global tnet_config
	return copy.copy(tnet_config)
