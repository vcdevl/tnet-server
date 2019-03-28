import json
import logging
from logging.handlers import TimedRotatingFileHandler
import signal
import sys
import time

from tnetserver import tnetapi, tnetconfig
	#, tnetconnman, tnetemail, tnetevent, tnethamachi, tnetmodel, tnetnetwork, tnetnotify,
	#tnetofono, tnetsms, tnetsystem, tnettemperature, tnetutils

def signal_handler(signal, frame):
	logging.info("Caught signal {}, exiting tnetserver".format(signal))
	sys.exit()

signal.signal( signal.SIGINT, signal_handler )
signal.signal( signal.SIGTERM, signal_handler )

tnetconfig.load_config()
config = tnetconfig.get_config()

# root logger
logger = logging.getLogger('')
logger.setLevel(config['log']['level'])

# format for logging
format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

# log to stdout
if config['log']['dest'] == 'file' :
	file_handler = TimedRotatingFileHandler("/var/log/tnet/tnethub.log", when="midnight", interval=1, backupCount=14, encoding=None, delay=True, utc=False)
	file_handler.setFormatter(format)
	logger.addHandler(file_handler)
else:
	stdout_handler = logging.StreamHandler(sys.stdout)
	stdout_handler.setFormatter(format)
	logger.addHandler(stdout_handler)

logging.info("Starting tnetserver")

# start other adapters
tnetapi.start_mqtt()
while True:
	time.sleep(0.1)
