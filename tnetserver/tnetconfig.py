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


def get_config():
	''' get config '''
	global tnet_config
	return copy.copy(tnet_config)
