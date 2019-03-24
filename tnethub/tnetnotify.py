#!/usr/bin/env python2

''' @file : tgNotifications.py
	@brief : Notifications.
'''
import sys
import copy
import time
import signal
import json
import logging
import Queue 
from tggateway.tgEmail import Email
from tggateway.tgSms import Sms
import tggateway.tgEvent as tgEvent
from tggateway.tgModel import Model

NOTIFICATION_CONFIG_FILE = '/home/tgard/config/notification.json'

ALERT_TYPE_POWERON			= 'PowerOn'
ALERT_TYPE_POWEROFF			= 'PowerOff'
ALERT_TYPE_POWERCHANGE		= 'PowerChange'
ALERT_TYPE_LOWBATTERY		= 'LowBattery'
ALERT_TYPE_SESSION_RESTART	= 'SessionRestart'
ALERT_TYPE_SESSION_RESUME	= 'SessionResume'
ALERT_TYPE_SESSION_NEW		= 'SessionNew'
ALERT_TYPE_SESSION_STOP		= 'SessionStop'
ALERT_TYPE_ALARM_1			= 'A1Alarms'
ALERT_TYPE_ALARM_2			= 'A2Alarms'
ALERT_TYPE_NETIFACE			= 'IfaceChange'
ALERT_TYPE_DISK_FULL 		= 'DiskFull'

LOGDEBUG_ENABLED = True
LOGINFO_ENABLED = True
LOGWARNING_ENABLED = True
LOGERROR_ENABLED = True
LOGCRICICAL_ENABLED = True

def LOGDEBUG(logstr):
	if LOGDEBUG_ENABLED:
		logging.debug(logstr)

def LOGINFO(logstr):
	if LOGINFO_ENABLED:
		logging.info(logstr)

def LOGWARNING(logstr):
	if LOGWARNING_ENABLED:
		logging.warning(logstr)

def LOGERROR(logstr):
	if LOGERROR_ENABLED:
		logging.error(logstr)

def LOGCRITICAL(logstr):
	if LOGCRITICAL_ENABLED:
		logging.critical(logstr)

class EmailTemplate(object):

	def __init__(self):
		'''
			@brief : Class initialisation.
		'''
		self.template = {}
		self.templates = {'PowerOn':self.powerOnTemplate, 
						'PowerOff':self.powerOffTemplate,
						'PowerChange':self.powerChangeTemplate,
						'LowBattery':self.lowBatteryTmplate,
						'SessionRestart':self.sessionRestartTemplate,
						'SessionResume':self.sessionResumeTemplate,
						'SessionNew':self.sessionNewTemplate,
						'SessionStop':self.sessionStopTemplate,
						'A1Alarms':self.alarmTemplate,
						'A2Alarms':self.alarmTemplate,
						'IfaceChange':self.ifaceChangeTemplate,
						'DiskFull':self.diskFullTemplate}
		return

	def getTemplate(self):
		''' @brief : Return template '''
		return copy.copy(self.template)

	def generate(self, alertType, alertData, alertTime):
		'''
			@brief : Generate template.
		'''
		return self.templates[alertType](alertType, alertData, alertTime)

	def powerOnTemplate(self, alertType, alertData, alertTime):
		''' @brief : Power on template '''

		body = ''			
		self.template = {}
		
		self.template['subject'] = 'POWER ON notification'

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {0}</h4>					
					</body>
				</html>
				'''.format(alertTime)

		self.template['body'] = body
		return True	

	def powerOffTemplate(self, alertType, alertData, alertTime):
		''' @brief : Power off template '''

		body = ''			
		self.template = {}
		
		self.template['subject'] = 'POWER OFF notification'

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {}</h4>
						<h4>Cause of shutdown: {}</h4>					
					</body>
				</html>
				'''.format(alertTime, alertData)

		self.template['body'] = body
		return True

	def powerChangeTemplate(self, alertType, alertData, alertTime):
		''' @brief : Power change template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'POWER CHANGE notification'

		try:
			# split alertData into 2 tokens, 0 should be previous power interface, 1 should be current power interface
			data = alertData.split(',')
			body += '''\
					<html>
						<body>
							<h4>Date/time of event: {}</h4>
							<h4>Change from {} to {}</h4>					
						</body>
					</html>
					'''.format(alertTime, data[0], data[1])

			self.template['body'] = body

		except Exception as e:
			logging.error('Notification: Power change template unexpected error {}'.format(e))
		
		return True

	def lowBatteryTmplate(self, alertType, alertData, alertTime):
		''' @brief : Low battery template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'BATTERY LOW notification'

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {}</h4>
						<h4>Battery capacity: {} %</h4>					
					</body>
				</html>
				'''.format(alertTime, alertData)

		self.template['body'] = body
		return True

	def sessionRestartTemplate(self, alertType, alertData, alertTime):
		''' @brief : Session restart template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'SESSION RESTART notification'
		try:
			# split alertData into tokens 0=session number, 1=session alias
			data = alertData.split(',')
			body += '''\
					<html>
						<body>
							<h4>Date/time of event: {}</h4>
							<h4>Session number: {}</h4>
							<h4>Session alias: {}</h4>					
						</body>
					</html>
					'''.format(alertTime, data[0], data[1])

			self.template['body'] = body

		except Exception as e:
			logging.error('Notification: Session restart template unexpected error {}'.format(e))
				
		return True

	def sessionResumeTemplate(self, alertType, alertData, alertTime):
		''' @brief : Session resume template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'SESSION CONFIG CHANGE notification'
		try:

			# alertData contains {session number, session alias, alarm type, trigger rate, sensor change={pos, alias, A1, A2}, {}, ...}

			data = alertData.split(',')
			datalen = len(data) - 4
			table = ''
			if datalen > 4:
				i = 0
				while True:
					table += '<tr><td align="left">{}</td>\
							<td align="left">{}</td>\
							<td align="left">{}</td>\
							<td align="left">{}</td></tr>'.format(data[4+i], data[5+i], data[6+i], data[7+i])

					i += 4
					if i == datalen:
						break

				body += '''\
						<html>
							<body>
								<h4>Date/time of event: {}</h4>
								<h4>Session number: {}</h4>
								<h4>Session alias: {}</h4>
								<h4>Trigger rate: {}</h4>

								<h4>Sensor changes:</h4>
								<table border="0" cellspacing="20px">
									<tr><th>POS</th><th>NAME</th><th>A1</th><th>A2</th></tr>
									{}
								</table>

							</body>
						</html>
						'''.format(alertTime, data[0], data[1], data[3], table)
			else:
				body += '''\
						<html>
							<body>
								<h4>Date/time of event: {}</h4>
								<h4>Session number: {}</h4>
								<h4>Session alias: {}</h4>
								<h4>Trigger rate: {}</h4>
							</body>
						</html>
						'''.format(alertTime, data[0], data[1], data[3])


			self.template['body'] = body

		except Exception as e:
			logging.error('Notification: Session resume template unexpected error {}'.format(e))
			return False

		return True

	def sessionNewTemplate(self, alertType, alertData, alertTime):
		''' @brief : Session new template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'SESSION NEW notification'

		try:
			# split alertData into tokens 0=session number, 1=session alias

			data = alertData.split(',')

			body += '''\
					<html>
						<body>
							<h4>Date/time of event: {}</h4>
							<h4>Session number: {}</h4>
							<h4>Session alias: {}</h4>					
						</body>
					</html>
					'''.format(alertTime, data[0], data[1])

			self.template['body'] = body

		except Exception as e:
			logging.error('Notification: Session new template unexpected error {}'.format(e))

		return True

	def sessionStopTemplate(self, alertType, alertData, alertTime):
		''' @brief : Session restart template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'SESSION STOP notification'

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {}</h4>			
					</body>
				</html>
				'''.format(alertTime)

		self.template['body'] = body
		return True

	def ifaceChangeTemplate(self, alertType, alertData, alertTime):
		''' @brief : Interface change template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'NETWORK INTERFACE CHANGE notification'

		try:
			# split alertData into tokens 0=previous network interface, 1=current network interface

			data = alertData.split(',')

			body += '''\
					<html>
						<body>
							<h4>Date/time of event: {}</h4>
							<h4>Change from {} to {}</h4>					
						</body>
					</html>
					'''.format(alertTime, data[0], data[1])

			self.template['body'] = body

		except Exception as e:
			logging.error('Notification: Network interface change template unexpected error {}'.format(e))

		return True

	def diskFullTemplate(self, alertType, alertData, alertTime):
		''' @brief : Disk full template '''
			
		body = ''			
		self.template = {}
		
		self.template['subject'] = 'DISK FULL notification'

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {0}</h4>					
					</body>
				</html>
				'''.format(alertTime)

		self.template['body'] = body
		return True

	def alarmTemplate(self, alertType, alertData, alertTime):
		'''
			@brief : Alarm template.
			@details : alertdata is string "addr1,name1,temp1,a11,a21,s1,trig1,addr2,name2,temp2,a12,a22,s2,trig2, ...."
		'''

		body = ''			
		self.template = {}
		
		# split into tokens
		data = alertData.split(',')
		datalen = len(data)
		# check validity NOTE first token is global alarm status
		if datalen < 8:
			logging.warning('Notifications: Alarm data seems incorrect not expecting {} fields.'.format(datalen))
			return False

		if (datalen-1) % 7 != 0:
			logging.warning('Notifications: Alarm data seems incorrect not modular 7.')
			return False

		if alertType == ALERT_TYPE_ALARM_1:
			self.template['subject'] = 'ALARM A1 notification'
		elif alertType == ALERT_TYPE_ALARM_2:
			self.template['subject'] = 'ALARM A2 notification'

		table = ''
		i = 1
		while True:
			table += '<tr><td align="left">{0}</td>\
					<td align="left">{1}</td>\
					<td align="left">{2}</td>\
					<td align="left">{3}C</td>\
					<td align="left">{4}C</td>\
					<td align="left">{5}C</td>\
					<td align="left">{6}</td></tr>'.format(data[i], data[i+1], data[i+6], data[i+2], data[i+3],data[i+4],data[i+5])

			i += 7
			if i == datalen:
				break

		body += '''\
				<html>
					<body>
						<h4>Date/time of event: {0}</h4>
						<h4>Device alarm status: {1}</h4>						
						<h4>Sensor alarm status:</h4>
						<table border="0" cellspacing="20px">
							<tr>
								<th>POS</th>
								<th>NAME</th>
								<th>TRIGGER</th>
								<th>TEMP</th>
								<th>A1</th>
								<th>A2</th>
								<th>STATUS</th>
							</tr>
							{2}
						</table>
					</body>
				</html>
				'''.format(alertTime, data[0], table)

		self.template['body'] = body
		return True 


class Notification(Model):

	def __init__(self, email=None, sms=None):
		'''
			@brief : Class initialisation.
		'''
		super(Notification, self).__init__('Notification')
		self.emailTemplate = EmailTemplate()
		#self.smsTemplate = smsTemplate()
		self.email = email
		self.sms = sms
		self.config = {}
		self.configured = False
		self.queue = Queue.Queue(maxsize=50)
		self.interval = 1
		logging.debug('Notification: Initialised.')

	def loadConfig(self):
		'''
			@brief : Load config from file.
		'''
		try:
			with open(NOTIFICATION_CONFIG_FILE, 'r') as f:
				self.config = json.load(f)

			# users		
			logging.debug('Notification: Emails enabled {0}.'.format(self.config['Email']))
			logging.debug('Notification: Sms enabled {0}.'.format(self.config['Sms']))

			logging.debug('Notification: Users config')
			for user in self.config['Users'].keys():
				logging.debug('	Name {0}.'.format(user))
				logging.debug('	Email {0}.'.format(self.config['Users'][user]['Email']))
				logging.debug('	Number {0}.'.format(self.config['Users'][user]['Mobile']))
				logging.debug('	Alerts')
				for alert in self.config['Users'][user]['Alerts'].keys():
					logging.debug('		{0} {1}.'.format(alert, self.config['Users'][user]['Alerts'][alert]))
		
			logging.info('Notification: Config loaded from file.')
			self.configured = True

		except Exception as e:
			logging.error("Notification: Load config error {0}.".format(e))

	def dumpConfig(self):
		'''
			@brief : Dump config to file.
		'''
		try:
			with open(NOTIFICATION_CONFIG_FILE, 'w') as f:
				json.dump(self.config, f)
		
			logging.info('Notification: Config dumped to file.')
		
		except Exception as e:
			logging.error("Notification: Dump config error {0}.".format(e))

	def setConfig(self, config):
		''' 
			@brief : Set config.
		'''
		backup = copy.deepcopy(self.config)
		self.config.clear()
		try:	
			self.config	= config
			
			# validate 

			self.dumpConfig()

			logging.debug('Notification: Config set.')

			self.configured = True
			return True
		except Exception as e:
			logging.error('Notification: Config set error {0}.'.format(e))
			# restore previous
			self.config = copy.deepcopy(backup)
			self.dumpConfig()
			self.configured = True
			return False

	def getConfig(self):
		''' 
			@brief : Get config.
		'''
		return copy.deepcopy(self.config)

	def evtopicToAlert(self, evtopic):
		'''@brief : Convert event topic to user alert '''
		if evtopic == tgEvent.EVTOPIC_TEMP_ALRM_A1:
			return ALERT_TYPE_ALARM_1

		elif evtopic == tgEvent.EVTOPIC_TEMP_ALRM_A2:
			return ALERT_TYPE_ALARM_2

		elif evtopic == tgEvent.EVTOPIC_TEMP_STOP_SESH:
			return ALERT_TYPE_SESSION_STOP

		elif evtopic == tgEvent.EVTOPIC_TEMP_NEW_SESH:
			return ALERT_TYPE_SESSION_NEW 

		elif evtopic == tgEvent.EVTOPIC_TEMP_RESTART_SESH:
			return ALERT_TYPE_SESSION_RESTART

		elif evtopic == tgEvent.EVTOPIC_TEMP_RESUME_SESH:
			return ALERT_TYPE_SESSION_RESUME

		elif evtopic == tgEvent.EVTOPIC_SYS_SHUTDOWN or evtopic == tgEvent.EVTOPIC_SYS_RESTART:
			return ALERT_TYPE_POWEROFF

		elif evtopic == tgEvent.EVTOPIC_SYS_POWERON:
			return ALERT_TYPE_POWERON

		elif evtopic == tgEvent.EVTOPIC_SYS_DISKFULL:
			return ALERT_TYPE_DISK_FULL

		elif evtopic == tgEvent.EVTOPIC_SYS_POWERCHANGE:
			return ALERT_TYPE_POWERCHANGE

		elif evtopic == tgEvent.EVTOPIC_SYS_BATTERYLOW:
			return ALERT_TYPE_LOWBATTERY

		elif evtopic == tgEvent.EVTOPIC_NET_IFACECHANGE:
			return ALERT_TYPE_NETIFACE

	def alert(self, event):
		''' 
		event['Class'], event['Topic'], event['Data'], event['Time']
			@brief : Send alert.
		'''
		try:
			self.queue.put(event,block=False)
			logging.debug('Notification: Queue size = {}.'.format(self.queue.qsize()))
		except Exception as e:
			logging.warning('Notification: Queue put error = {}.'.format(e))


	def run(self):
		''' @brief : Run called in thread. '''

		lasttime = 0
		while True:

			time.sleep(1)

			if self.stopThread:
				break

			if time.time() - lasttime < self.interval:
				continue

			if self.queue.qsize() == 0:
				logging.debug('Notification: Empty nothing to process.')
				self.interval = 10
				lasttime = time.time()
				continue
			else:
				self.interval = 1

			# pull from queue
			event = self.queue.get()

			emailAddr = []
			#smsAddr = []

			evclass = event['Class']
			evtopic = event['Topic']
			evdata = event['Data']
			evtime = event['Time']
			self.queue.task_done()
			# translate evtopic to alert type
			alertType = self.evtopicToAlert(evtopic)
			if alertType == '':
				logging.warning('Notification: Event topic not supported evclass={} evtopic={}.'.format(evclass, evtopic))
				return

			# email
			if self.config['Email']:

				# any users subscribing to this alert type?
				for user in self.config['Users'].keys():
					logging.debug("Notification: User = {}, Alert-{} = {}".format(user, alertType, self.config['Users'][user]['Alerts'][alertType]))		
					if not self.config['Users'][user]['Alerts'][alertType]:
						continue
					else:
						emailAddr.append(self.config['Users'][user]['Email'])

				# prepare template depending on topic
				if len(emailAddr) > 0:
					result = self.emailTemplate.generate(alertType, evdata, evtime)

					# send it
					if result:
						self.email.mailRequest(emailAddr, self.emailTemplate.getTemplate())
				else:
					logging.debug('Notification: Email no users subscribing to this event.')

			else:
				logging.debug('Notification: Email alerts disabled.')

			lasttime = time.time()

			# sms
			'''if self.config['Sms']:

				# any users subscribing to this alert type?
				for user in self.config['Users'].keys():
					if not self.config['Users'][user]['Alerts'][alertType]:
						continue
					else:
						smsAddr.append(self.config['Users'][user]['Email'])

				if len(smsAddr) > 0:
					# prepare template depending on topic
					#result, smsMsg = smsTemplate.generate(alertType, evdata, evtime)
					result = smsTemplate.generate(alertType, evdata, evtime)

					# send it
					if result:
						self.sms.smsRequest(smsAddr, smsTemplate.getTemplate())
				else:
					logging.debug('Notification: Sms no users subscribing to this event.')

			else:
				logging.debug('Notification: Sms alerts disabled.')'''





def cleanExit():
	''' @fn cleanExit
		@brief : Clean exit handler when signal terminates program.
	'''	
	logging.info('Notification: Exiting application.')
	sys.exit()

def fSignalHandler(signal, frame):		
	''' @fn fSignalHandler
		@brief : Signal handler.
	'''
	cleanExit()

if __name__ == '__main__':
	
	argc = len(sys.argv)	

	# root logger
	logger = logging.getLogger('')
	logger.setLevel(logging.DEBUG)
	
	# format for logging
	format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

	# add stdout stream handler
	stdouth = logging.StreamHandler(sys.stdout)
	stdouth.setFormatter(format)
	logger.addHandler(stdouth)

	tgNfy = Notification()
	tgNfy.loadConfig()
