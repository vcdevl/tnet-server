#!/usr/bin/env python2

''' @file : tgTemperature.py
	@brief : Temperature sensor network management.
'''

import threading
import signal
import sys
import logging
import logging.handlers
import json
import random
import ctypes
import copy
import time
import tggateway.tgEvent as tgEvent
from tggateway.tgModel import Model
from tggateway.tgDataLogger import TnetDataLogger

TEMPERATURE_STATE_OFFLINE 		= 0
TEMPERATURE_STATE_ONLINE 		= 1
TEMPERATURE_STATE_HALTED		= 2

TEMPERATURE_CONFIG_FILE			= '/home/tgard/config/temperature.json'
TEMPERATURE_CONFIG_FILE_BAK		= '/home/tgard/config/temperature.json.bak'

ALARM_STATE_UNSET	 			= -1
ALARM_STATE_NONE 				= 0
ALARM_STATE_PAST_A1 			= 1
ALARM_STATE_PAST_A2 			= 2
ALARM_STATE_CURRENT_A1 			= 3
ALARM_STATE_CURRENT_A2 			= 4

# A1 crossing
ALARM_CHANGE_NONE				= -1
ALARM_CHANGE_RISING_A1			= 0
ALARM_CHANGE_FALLING_A1			= 1
ALARM_CHANGE_RISING_A2			= 2
ALARM_CHANGE_FALLING_A2			= 3

ALARM_TYPE_HIGH_HIGH			= 1
ALARM_TYPE_HIGH_LOW				= 2
ALARM_TYPE_LOW_LOW				= 3

CONTROLLER_STTY 				= '/dev/ttyS2'
CONTROLLER_RESET_PIN_FILE 		= '/sys/class/gpio/gpio26_ph20/value'

HumanReadableAlarmTrigger = ['A1 rising', 'A1 falling', 'A2 rising','A2 falling']
HumanReadableGlobalAlarmState = ['No alarms', 'Past A1 alarms', 'Past A2 alarms', 'Current A1 alarms', 'Current A2 alarms']
HumanReadableSensorAlarmState = ['No alarm', 'Past A1 alarm', 'Past A2 alarm', 'A1 alarm', 'A2 alarm']

class Sensor(object):
	''' @class : Sensor
		@brief : Temperature sensor.
	'''	
	def __init__(self):
		''' @fn init
			@brief : Class initialisation.
		'''
		self.address = 0
		# address of another sensor in the network
		self.temperature = 0
		self.alarmState = ALARM_STATE_NONE
		self.lastContact = 0
		self.triggerA0 = 0
		self.triggerA1 = 0
		self.triggerA2 = 0
		self.triggerState = ALARM_CHANGE_NONE
		self.config = {}

	def setConfig(self, addr, config):
		''' @fn setConfig
			@brief : Set attributes of the sensor.
		'''
		self.address = addr
		self.config = config
		
		'''logging.debug('Sensor:')
		logging.debug('	Addr: {0}.'.format(self.address))
		logging.debug('	Name: {0}.'.format(self.config['Alias']))
		logging.debug('	Serial: {0}.'.format(self.config['Serial']))
		logging.debug('	Alarm 1: {0}.'.format(self.config['A1']))
		logging.debug('	Alarm 2: {0}.'.format(self.config['A2']))
		logging.debug('	Sensor ref: {0}.'.format(self.config['Diffmode']))
		logging.debug('	Alarm 1 triggered: {0}.'.format(self.config['A1trig']))
		logging.debug('	Alarm 2 triggered: {0}.'.format(self.config['A2trig']))'''

	def changeConfig(self, config):
		''' @brief : CHange sensor config '''

		if self.config['Serial'] != config['Serial']:
			self.config['Serial'] = config['Serial']

		if self.config['Alias'] != config['Alias']:
			self.config['Alias'] = config['Alias']

		if self.config['A1'] != config['A1']:
			self.config['A1'] = config['A1']

		if self.config['A2'] != config['A2']:
			self.config['A2'] = config['A2']

	def initialiseAlarmState(self):
		# set alarm status
		if self.config['A2trig']:
			self.alarmState = ALARM_STATE_PAST_A2
		elif self.config['A1trig']:
			self.alarmState = ALARM_STATE_PAST_A1
		else:
			self.alarmState = ALARM_STATE_NONE

	def getPos(self):
		return copy.copy(self.address)

	def getAddr(self):
		''' @fn getAddr
			@brief : Get address sensor.
		'''
		return copy.copy(self.address)

	def getSerial(self):
		''' @fn getSerial
			@brief : Get serial number of sensor.
		'''
		return copy.copy(self.config['Serial'])

	def getName(self):
		''' @fn getName
			@brief : Get name of sensor.
		'''
		return copy.copy(self.config['Alias'])

	def getAlarms(self):
		''' @fn getAlarms
			@brief : Get alarms of sensor.
		'''
		return copy.copy(self.config['A1']), copy.copy(self.config['A2'])

	def getTriggeredAlarms(self):
		''' @brief : Get A1trig and A2Trig states '''
		return copy.copy(self.config['A1trig']), copy.copy(self.config['A2trig'])

	def getSensorRef(self):
		''' @fn getSensorRef
			@brief : Get ref sensor.
		'''
		return copy.copy(self.config['Diffmode'])

	def setTemperature(self, temperature):
		''' @fn setTemperature
			@brief : Get a new temperature reading.
		'''
		self.lastContact = time.time()
		self.temperature = temperature

	def getTemperature(self):
		''' @fn getTemperature
			@brief : Get temperature reading.
		'''
		return copy.copy(self.temperature)

	def getLastContact(self):
		''' @fn getLastContact
			@brief : Last time sensor produced valid reading.
		'''
		return copy.copy(self.lastContact)

	def getPastAlarmState(self):
		''' @fn getPastAlarmState
			@brief : Get past alarm state.
		'''
		if self.config['A2trig']:
			return ALARM_STATE_PAST_A2
		elif self.config['A1trig']:
			return ALARM_STATE_PAST_A1
		else:
			return ALARM_STATE_NONE

	def getAlarmState(self):
		''' @fn getAlarmState
			@brief : Get alarm state of sensor.
		'''
		return copy.copy(self.alarmState)

	def getTriggerState(self):
		'''
			@brief : Get trigger state.
		'''
		return copy.copy(self.triggerState)

	def processAlarm(self, alarmInterpretation, alarmTriggerRate, refSensorTemperature=None):
		''' @fn processAlarm
			@brief : Process alarm with given thresholds.
		'''
		self.triggerState = ALARM_CHANGE_NONE

		if refSensorTemperature is not None and self.config['Diffmode'] != 0 and self.config['Diffmode'] != self.address:
			temperature = self.temperature - refSensorTemperature
		else:
			temperature = self.temperature

		#logging.debug('Sensor: Process alarm, temperature = {}.'.format(temperature))

		if alarmInterpretation == ALARM_TYPE_HIGH_HIGH:

			# past A2 
			if temperature >= self.config['A2']:
				self.triggerA2 += 1

				if self.triggerA2 == alarmTriggerRate:
					self.triggerA2 = 0
					# a2 triggered

					if self.alarmState != ALARM_STATE_CURRENT_A2:
						self.alarmState = ALARM_STATE_CURRENT_A2
						self.triggerState = ALARM_CHANGE_RISING_A2

						# set past alarm 2 trigger
						self.config['A2trig'] = True

			# past A1
			elif temperature >= self.config['A1']:
				self.triggerA1 += 1

				if self.triggerA1 == alarmTriggerRate:
					self.triggerA1 = 0

					# trigger occur i.e. change alarm state
					if self.alarmState != ALARM_STATE_CURRENT_A1:

						# come from A2
						if self.alarmState == ALARM_STATE_CURRENT_A2:
							self.triggerState = ALARM_CHANGE_FALLING_A2
						else:
							self.triggerState = ALARM_CHANGE_RISING_A1

						self.alarmState = ALARM_STATE_CURRENT_A1
						
						# set past alarm 1 trigger
						self.config['A1trig'] = True

			# 
			else:
				self.triggerA0 += 1

				if self.triggerA0 == alarmTriggerRate:
					self.triggerA0 = 0

					if self.alarmState >= ALARM_STATE_CURRENT_A1:
						# do past status if gone back to no current
						if self.config['A2trig']:
							self.alarmState = ALARM_STATE_PAST_A2
						elif self.config['A1trig']:
							self.alarmState = ALARM_STATE_PAST_A1
						else:
							self.alarmState = ALARM_STATE_NONE

						# come from A1
						self.triggerState = ALARM_CHANGE_FALLING_A1



		elif alarmInterpretation == ALARM_TYPE_HIGH_LOW:
			# past A2 
			if temperature >= self.config['A2']:
				self.triggerA2 += 1

				if self.trigger == alarmTriggerRate:
					self.triggerA2 = 0
					# a2 triggered

					if self.alarmState == ALARM_STATE_CURRENT_A1 or self.alarmState == ALARM_STATE_NONE:
						self.alarmState = ALARM_STATE_CURRENT_A2
						self.triggerState = ALARM_CHANGE_RISING_A2

						# set past alarm 2 trigger
						self.config['A2trig'] = True

			# past A1
			elif temperature <= self.config['A1']:
				self.triggerA1 += 1

				if self.triggerA1 == alarmTriggerRate:
					self.triggerA1 = 0

					# trigger occur i.e. change alarm state
					if self.alarmState == ALARM_STATE_CURRENT_A2 or self.alarmState == ALARM_STATE_NONE:
						self.triggerState = ALARM_CHANGE_FALLING_A1
						self.alarmState = ALARM_STATE_CURRENT_A1
						
						# set past alarm 1 trigger
						self.config['A1trig'] = True

			# 
			else:
				self.triggerA0 += 1

				if self.triggerA0 == alarmTriggerRate:
					self.triggerA0 = 0

					if self.alarmState >= ALARM_STATE_CURRENT_A1:
						
						# come from A1 or A2
						if self.alarmState == ALARM_STATE_CURRENT_A2:
							self.triggerState = ALARM_CHANGE_FALLING_A2
						else:
							self.triggerState = ALARM_CHANGE_RISING_A1

						# do past status if gone back to no current
						if self.config['A2trig']:
							self.alarmState = ALARM_STATE_PAST_A2
						elif self.config['A1trig']:
							self.alarmState = ALARM_STATE_PAST_A1
						else:
							self.alarmState = ALARM_STATE_NONE



		elif alarmInterpretation == ALARM_TYPE_LOW_LOW:
			# past A2 
			if temperature <= self.config['A2']:
				self.triggerA2 += 1

				if self.trigger == alarmTriggerRate:
					self.triggerA2 = 0
					# a2 triggered

					if self.alarmState != ALARM_STATE_CURRENT_A2:
						self.alarmState = ALARM_STATE_CURRENT_A2
						self.triggerState = ALARM_CHANGE_FALLING_A2

						# set past alarm 2 trigger
						self.config['A2trig'] = True

			# past A1
			elif temperature <= self.config['A1']:
				self.triggerA1 += 1

				if self.triggerA1 == alarmTriggerRate:
					self.triggerA1 = 0

					# trigger occur i.e. change alarm state
					if self.alarmState != ALARM_STATE_CURRENT_A1:

						# come from A2 or A0
						if self.alarmState == ALARM_STATE_CURRENT_A2:
							self.triggerState = ALARM_CHANGE_RISING_A2
						else:
							self.triggerState = ALARM_CHANGE_FALLING_A1

						self.alarmState = ALARM_STATE_CURRENT_A1
						
						# set past alarm 1 trigger
						self.config['A1trig'] = True

			# 
			else:
				self.triggerA0 += 1

				if self.triggerA0 == alarmTriggerRate:
					self.triggerA0 = 0

					if self.alarmState >= ALARM_STATE_CURRENT_A1:
						# do past status if gone back to no current
						if self.config['A2trig']:
							self.alarmState = ALARM_STATE_PAST_A2
						elif self.config['A1trig']:
							self.alarmState = ALARM_STATE_PAST_A1
						else:
							self.alarmState = ALARM_STATE_NONE

						# come from A1
						self.triggerState = ALARM_CHANGE_RISING_A1

		return copy.copy(self.alarmState)




class Controller(object):
	''' @class : Controller.py
		@brief : Tempgard base object for all objects.
	'''	
	def __init__(self):
		''' @fn init
			@brief : Class initialisation.
		'''
		self.ctlHandle = -1
		self.cowlib = ctypes.cdll.LoadLibrary('/usr/lib/libtnetonewire.so')

	def state(self):
		return copy.copy(self.ctlHandle)

	def acquire(self):
		''' @fn acquire
			@brief : Initialise the controller via ctypes.
		'''
		# c one wire library call
		try:
			# set ctlFault
			self.ctlHandle = -1	
			f = self.cowlib.OWAcquireBusController
			f.argtypes = [ctypes.c_char_p]
			self.ctlHandle = f(CONTROLLER_STTY.encode())

		except Exception as e:
			logging.critical('Controller: Acquire failed {0}.'.format(e))

		if self.ctlHandle >= 0:
			logging.debug('Controller: Initialised.')			
			
		else:
			logging.critical('Controller: Failed to initialise.')	
			

	def release(self):
		''' @fn release
			@brief : Release controller handle.
		'''
		logging.debug('Controller: Releasing handle = {0}.'.format(self.ctlHandle))
		if self.ctlHandle >= 0:
			try:
				f = self.cowlib.OWReleaseBusController
				f.argtypes = [ctypes.c_int]
				f(self.ctlHandle)
			except Exception as e:
				logging.error('Controller: Failed to release handle {0}.'.format(e))
		else:
			logging.debug('Controller: Invalid handle.')

		self.ctlHandle = -1

	def cyclePower(self):
		''' @fn cyclePower
			@brief : Hw reset of the bus controller.
		'''
		# power cycle		
		with open(CONTROLLER_RESET_PIN_FILE, 'w') as f:
			f.write('0')
			time.sleep(3)
			f.write('1')	
			logging.debug('Controller: Cycling the power.')

	def reset(self):
		''' @fn reset
			@brief : Hw reset of the bus controller.
		'''
		self.release()
		self.cyclePower()
		self.acquire()

	def temperature(self, sensorSerial):
		''' @fn temperature
			@brief : Read temperature from sensor.
		'''
		value = 200.0
		try:
			f = self.cowlib.OWReadTemperature
			f.argtypes = [ctypes.c_int, ctypes.c_char_p]
			f.restype = ctypes.c_float
			value = round(f(self.ctlHandle, sensorSerial.encode()))
			logging.debug('Controller: Reading temperature from {0} value = {1}.'.format(sensorSerial, value))

		except Exception as e:
			logging.error('Controller: Unable to read temperature from {0}.'.format(e))

		return value




class Temperature(Model):
	''' @class : Temperature
		@brief : Temperature sensor manager.
	'''
	def __init__(self, eventMgr=None, tempLogger=None):
		''' @fn : __init__
			@brief : Class initialisation.
		'''
		super(Temperature, self).__init__('Temperature')
		self.eventMgr = eventMgr
		self.config = {}
		self.globalAlarmStatus = 0
		self.anySensorsReferenced = False
		self.configured = False
		self.interval = 1
		self.state = TEMPERATURE_STATE_OFFLINE
		self.tempLogger = TnetDataLogger() 

		self.controller = Controller()
		self.sensors = []

		logging.info('Temperature: Initialised.')

	def halt(self):
		logging.info('Temperature: Halt processing.')
		self.state = TEMPERATURE_STATE_HALTED

	def resume(self):
		logging.info('Temperature: Resume processing.')
		self.state = TEMPERATURE_STATE_ONLINE

	def loadConfig(self):
		''' @fn : loadConfig
			@brief : Load configuration from file.
		'''

		try:
			
			with open(TEMPERATURE_CONFIG_FILE, 'r') as f:
				self.config = json.load(f)

			# pass the session name to the logger
			self.tempLogger.newSession(self.config['Session']['Number'], removePrevious=False)
			# set batchsize depending in the size of the network
			if self.config['Session']['TotalSensors'] > 0 and self.config['Session']['TotalSensors'] <= 60:
				self.tempLogger.setBatchSize(60/self.config['Session']['TotalSensors'] + 1)

			#logging.debug('Loaded Session config: {0}'.format(config))

			self.sensors[:]
			# initialise the realtime temp and alarm status of each sensor
			for i in range(self.config['Session']['TotalSensors']):
				key = '{0}'.format(i+1)
				sensor = Sensor()
				sensor.setConfig(i+1, self.config['Sensors'][key])
				sensor.initialiseAlarmState()

				self.sensors.append(sensor)
				# check if any sensors referencing others
				if self.config['Sensors'][key]['Diffmode'] != 0:
					self.anySensorsReferenced = True

			# do some additional checks to make sure config is valid

			# set the global alarm status depending on past a1/a2 of the sensors
			self.processAlarmStatus()
			logging.info('Temperature: Config loaded from file.')
			self.configured = True

			return True
		except Exception as e:
			logging.error('Temperature: Config load error {0}.'.format(e))
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_TEMP, tgEvent.EVTOPIC_TEMP_NO_CONFIG, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_DATABASE])
			self.configured = False
			return False

	def dumpConfig(self):
		'''
			@brief : Dump config to file.
		'''
		try:
			with open(TEMPERATURE_CONFIG_FILE, 'w') as f:
				json.dump(self.config, f)
		
			logging.info('Temperature: Config dumped to file.')
		
		except Exception as e:
			logging.error("Temperature: Config dump error {0}.".format(e))

	def setSensorConfig(self):
		'''
			@brief : Set sensor config.
		'''
		try:
			self.sensors = []
			# initialise the realtime temp and alarm status of each sensor
			for i in range(self.config['Session']['TotalSensors']):
				key = '{}'.format(i+1)
				sensor = Sensor()
				self.config['Sensors'][key]['A1trig'] = False
				self.config['Sensors'][key]['A2trig'] = False
				sensor.setConfig(i+1, self.config['Sensors'][key])

				self.sensors.append(sensor)
				# check if any sensors referencing others
				if self.config['Sensors'][key]['Diffmode'] != 0:
					self.anySensorsReferenced = True

		except Exception as e:
			logging.error('Temperature: Set sensor error {0}.'.format(e))

	def changeConfig(self, config):
		''' @brief : Change config, called by Resume Session API '''
		backup = copy.deepcopy(self.config)
		try:	
			# alias changed ?
			if self.config['Session']['Alias'] != config['Session']['Alias']:
				self.config['Session']['Alias'] = config['Session']['Alias']	

			# trigger rate changed ?
			if self.config['Session']['TriggerRate'] != config['Session']['TriggerRate']:
				self.config['Session']['TriggerRate'] = config['Session']['TriggerRate']
			
			# sensor serial, alias, a1 or a2 changed ?
			for i in range(config['Session']['TotalSensors']):
				pos = '{}'.format(i+1)
				if self.config['Sensors'][pos]['Serial'] != config['Sensors'][pos]['Serial'] or \
					self.config['Sensors'][pos]['Alias'] != config['Sensors'][pos]['Alias'] or \
					self.config['Sensors'][pos]['A1'] != config['Sensors'][pos]['A1'] or \
					self.config['Sensors'][pos]['A2'] != config['Sensors'][pos]['A2']:
						# get A1trig, A2trig
						a1trig, a2trig = self.sensors[i].getTriggeredAlarms()
						self.config['Sensors'][pos] = copy.deepcopy(config['Sensors'][pos])
						self.config['Sensors'][pos]['A1trig'] = a1trig
						self.config['Sensors'][pos]['A2trig'] = a2trig
						# change sensor config
						self.sensors[i].changeConfig(self.config['Sensors'][pos])

			self.processAlarmStatus()
			
			# update the commit
			self.config['Commit'] = backup['Commit'] + 1
			self.dumpConfig()
			self.configured = True
			logging.debug('Temperature: Change config.')

			# change sessio name for logger
			# pass the session name to the logger
			self.tempLogger.flushLogs()
			self.tempLogger.newSession(self.config['Session']['Number'], removePrevious=True) 

			return True
		except Exception as e:
			logging.error('Temperature: Change config error {0}.'.format(e))
			# restore previous
			self.config = copy.deepcopy(backup)
			for i in range(config['Session']['TotalSensors']):
				pos = '{}'.format(i+1)
				self.sensors[i].setConfig(pos, self.config['Sensors'][pos])
			self.processAlarmStatus()
			self.dumpConfig()
			self.configured = True
			return False

	def setConfig(self, config):
		''' 
			@brief : Set config.
			@param resetTriggers : Reset A1Trig, A2Trig
		'''
		backup = copy.deepcopy(self.config)
		self.config.clear()
		try:	
			self.config	= copy.deepcopy(config)
			
			# validate 

			self.setSensorConfig()
			self.processAlarmStatus()
					
			# update the commit
			self.config['Commit'] = backup['Commit'] + 1
			self.dumpConfig()
			logging.debug('Temperature: Set config.')
			self.configured = True

			self.tempLogger.flushLogs()
			self.tempLogger.newSession(self.config['Session']['Number'], removePrevious=True)

			# set batchsize depending on total sensors
			if self.config['Session']['TotalSensors'] > 0 and self.config['Session']['TotalSensors'] <= 60:
				self.tempLogger.setBatchSize(60/self.config['Session']['TotalSensors'] + 1)

			return True
		except Exception as e:
			logging.error('Temperature: Set config error {0}.'.format(e))
			# restore previous
			self.config = copy.deepcopy(backup)
			self.setSensorConfig()
			self.processAlarmStatus()
			self.dumpConfig()
			self.configured = True
			return False

	def getConfig(self):
		''' 
			@brief : Get config.
		'''
		return copy.deepcopy(self.config)

	def getLiveState(self):
		''' @fn : getLiveState
			@brief : Get live state.
		'''
		# controller state, sensor state {temperature, alarm status}
		# add commit for every config change, when client gets latest config it keeps track of the commit
		# which is sent with every live state update. If the commit changes or is different from the client,
		# then client gets latest
		liveState = '{0},{1},{2}'.format(self.config['Commit'], self.state, self.globalAlarmStatus)
		return liveState

	def getGlobalAlarmState(self):
		return self.globalAlarmStatus

	def processAlarmStatus(self):
		''' @fn processAlarmStatus
			@brief : Calculate global alarm status based .
		'''		
		# calculate global alarm status
		a1past = False
		a2past = False
		a1current = False
		a2current = False

		globalAlarmStatusNow = ALARM_STATE_NONE

		for sensor in self.sensors:
			alarmState = sensor.getAlarmState()
			pastAlarmState = sensor.getPastAlarmState()
			
			if alarmState == ALARM_STATE_CURRENT_A2:
				a2current = True
			elif alarmState == ALARM_STATE_CURRENT_A1:
				a1current = True
			elif pastAlarmState == ALARM_STATE_PAST_A2:
				a2past = True		
			elif pastAlarmState == ALARM_STATE_PAST_A1:
				a1past = True

		if a2current:
			globalAlarmStatusNow = ALARM_STATE_CURRENT_A2
		elif a1current:
			globalAlarmStatusNow = ALARM_STATE_CURRENT_A1
		elif a2past:
			globalAlarmStatusNow = ALARM_STATE_PAST_A2
		elif a1past:
			globalAlarmStatusNow = ALARM_STATE_PAST_A1
		else:
			globalAlarmStatusNow = ALARM_STATE_NONE

		# raise av event if state changes
		if globalAlarmStatusNow != self.globalAlarmStatus and globalAlarmStatusNow == ALARM_STATE_CURRENT_A2:
			# turn a2 audio on
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_AUDVIS, tgEvent.EVTOPIC_AUV_STATE_A2, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_AUDIOVISUAL])

		elif globalAlarmStatusNow != self.globalAlarmStatus and globalAlarmStatusNow == ALARM_STATE_CURRENT_A1:
			# turn a1 audio on
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_AUDVIS, tgEvent.EVTOPIC_AUV_STATE_A1, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_AUDIOVISUAL])

		elif globalAlarmStatusNow != self.globalAlarmStatus:
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_AUDVIS, tgEvent.EVTOPIC_AUV_STATE_A0, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_AUDIOVISUAL])

		self.globalAlarmStatus = globalAlarmStatusNow
		logging.debug('Temperature: Global alarm status {0}.'.format(self.globalAlarmStatus))	

	def startController(self):
		''' @fn : startController
			@brief : Initialise controller.
		'''
		self.controller.acquire()

	def streamData(self):
		'''
			@brief : Stream live data.
		'''	
		data = ''
		for sensor in self.sensors:
			a1, a2 = sensor.getAlarms()
			data += ',{:3.1f},{},{},{}'.format(sensor.getTemperature(), a1, a2, sensor.getAlarmState())	
	
		self.eventMgr.raiseEvent(tgEvent.EVCLASS_TEMP, tgEvent.EVTOPIC_TEMP_NEW_DATA, data[1:], tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_STREAM])

	def logData(self):
		'''
			@brief : Send minute data to logger.
		'''	
		data = ''
		for sensor in self.sensors:
			a1, a2 = sensor.getAlarms()
			data += ',{:3.1f},{},{},{}'.format(sensor.getTemperature(), a1, a2, sensor.getAlarmState())	
	
		self.tempLogger.log(int(time.time()), data[1:])

	def updateSensors(self):
		''' @fn : updateSensors
			@brief : Update temperature and alarm status for network.
		'''
		sensorAlarmTriggerChanged =False
		# some sensors reference other sensors for differential temperature read
		if self.anySensorsReferenced:
			for sensor in self.sensors:
				if self.stopThread:
					return

				if self.state == TEMPERATURE_STATE_HALTED:
					return

				temperature = self.controller.temperature(sensor.getSerial())
				sensor.setTemperature(temperature)
				refSensor = sensor.getSensorRef()
				if refSensor == 0:
					a1trigBefore, a2trigBefore = sensor.getTriggeredAlarms()
					sensor.processAlarm(self.config['Session']['AlarmType'], self.config['Session']['TriggerRate'])
					a1trigNow, a2trigNow = sensor.getTriggeredAlarms()
					if a1trigBefore != a1trigNow or a2trigBefore != a2trigNow:
						logging.debug("Sensor {} trig changed, a1trig before = {} a1trig now = {} a2trig before {} a2trig now {}".format(sensor.getPos(),
							a1trigBefore, a1trigNow, a2trigBefore, a2trigNow))
						sensorAlarmTriggerChanged = True

			for sensor in self.sensors:
				refSensor = sensor.getSensorRef() 
				addrRefSensor = self.sensors[refSensor-1].getAddr()
				myAddr = sensor.getAddr()
				if refSensor != 0 and addrRefSensor != myAddr:
					tempOfRefSensor = self.sensors[refSensor-1].getTemperature()
					#logging.debug('Temperature: Sensor {} references sensor {}.'.format(myAddr, addrRefSensor))
					a1trigBefore, a2trigBefore = sensor.getTriggeredAlarms()
					sensor.processAlarm(self.config['Session']['AlarmType'], self.config['Session']['TriggerRate'], refSensorTemperature=tempOfRefSensor)
					a1trigNow, a2trigNow = sensor.getTriggeredAlarms()
					if a1trigBefore != a1trigNow or a2trigBefore != a2trigNow:
						logging.debug("Sensor {} trig changed, a1trig before = {} a1trig now = {} a2trig before {} a2trig now {}".format(sensor.getPos(),
							a1trigBefore, a1trigNow, a2trigBefore, a2trigNow))
						sensorAlarmTriggerChanged = True

		# no referencing, read and process in same loop
		else:
			for sensor in self.sensors:
				if self.stopThread:
					return

				if self.state == TEMPERATURE_STATE_HALTED:
					return

				temperature = self.controller.temperature(sensor.getSerial())
				sensor.setTemperature(temperature)

				a1trigBefore, a2trigBefore = sensor.getTriggeredAlarms()
				sensor.processAlarm(self.config['Session']['AlarmType'], self.config['Session']['TriggerRate'])
				a1trigNow, a2trigNow = sensor.getTriggeredAlarms()
				if a1trigBefore != a1trigNow or a2trigBefore != a2trigNow:
					logging.debug("Sensor {} trig changed, a1trig before = {} a1trig now = {} a2trig before {} a2trig now {}".format(sensor.getPos(),
						a1trigBefore, a1trigNow, a2trigBefore, a2trigNow))
					sensorAlarmTriggerChanged = True

		# process triggers and save to file
		if sensorAlarmTriggerChanged:
			logging.debug("Alarm triggers changed, saving config")
			self.dumpConfig()

		# update global alarm status
		self.processAlarmStatus()

		# stream the data
		self.streamData()

		# any sensors in triggered state then send alarm event
		sensorStrA1 = ''
		sensorStrA2 = ''
		for sensor in self.sensors:
			triggerState = sensor.getTriggerState() 
			if triggerState != ALARM_CHANGE_NONE:
				a1,a2 = sensor.getAlarms() 
				# format is addr,name,temp,a1,a2,state,trigger
				sensorStr = ',{},{},{},{},{},{},{}'.format(sensor.getAddr(),
															sensor.getName(),
															sensor.getTemperature(),
															a1,
															a2,
															HumanReadableSensorAlarmState[sensor.getAlarmState()],
															HumanReadableAlarmTrigger[triggerState])

				logging.debug('Temperature: Sensor alarm trigger {}.'.format(sensorStr))

				# add 
				if triggerState == ALARM_CHANGE_RISING_A1 or triggerState == ALARM_CHANGE_FALLING_A1:
					sensorStrA1 += sensorStr
				elif triggerState == ALARM_CHANGE_FALLING_A2 or triggerState == ALARM_CHANGE_RISING_A2:
					sensorStrA2 += sensorStr

		if sensorStrA2 != '':
			# add global alarm status to front
			sensorStrA2 = '{}{}'.format(HumanReadableGlobalAlarmState[self.globalAlarmStatus], sensorStrA2)
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_TEMP, tgEvent.EVTOPIC_TEMP_ALRM_A2, sensorStrA2, tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])

		if sensorStrA1 != '':
			# add global alarm status to front
			sensorStrA1 = '{}{}'.format(HumanReadableGlobalAlarmState[self.globalAlarmStatus], sensorStrA1)
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_TEMP, tgEvent.EVTOPIC_TEMP_ALRM_A1, sensorStrA1, tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])



	def run(self):
		''' @fn : threadTask
			@brief : Run main task.
		'''

		minutetime = time.time()
		lasttime = 0
		updatesensortime = 0
		while True:
			
			time.sleep(1)

			if self.stopThread:
				break

			if time.time() - lasttime < self.interval:
				continue

			if self.state == TEMPERATURE_STATE_HALTED:
				continue

			if not self.configured:
				logging.error('Temperature: Unable to load configuration. Check in 60 seconds.')
				self.interval = 60
				self.loadConfig()
				lasttime = time.time()
				continue

			if self.controller.state() < 0:
				logging.error('Temperature: Controller not initialised. Check in 60 seconds.')
				self.interval = 60
				self.controller.reset()
				lasttime = time.time()
				continue

			self.interval = 1
			
			# if total sensors is less than 10, only update every 8 seconds otherwise update every time
			if self.config["Session"]["TotalSensors"] < 10:
				if time.time() - updatesensortime < 8:
					continue

			self.updateSensors()
			updatesensortime = time.time()
			

			# log data every minute
			#if time.time() - minutetime >= 60:
			#	minutetime = time.time()
			self.logData()

			lasttime = time.time()


	def start(self):
		''' @fn : start
			@brief : Start manager.
		'''	
		self.startController()
		self.interval = 1
		logging.info('Temperature: Going online.')
		self.state = TEMPERATURE_STATE_ONLINE
		super(Temperature,self).start()		
			
	def stop(self):
		''' @fn : stop
			@brief : Stop manager.
		'''	
		
		logging.info('Temperature: Going offline.')
		self.state = TEMPERATURE_STATE_OFFLINE
		super(Temperature,self).stop()
		self.controller.release()
		
	def getState(self):
		''' @fn : getState
			@brief : Return state of manager.
		'''	
		return copy(self.state)

	def factoryReset(self):
		'''
			@brief : Factory reset.
		'''
		try:
			logging.info('Temperature: Factory reset.')
			
			# move temperature config to backup
			p = subprocess.Popen(['mv', TEMPERATURE_CONFIG_FILE, TEMPERATURE_CONFIG_FILE_BAK], stdout=subprocess.PIPE)
			p.communicate()
			
			return True
		except Exception as e:
			logging.error('Temperature: Unexpected error {0}.'.format(e))
			return False


def cleanExit():
	''' @fn cleanExit
		@brief : Clean exit handler when signal terminates program.
	'''	

	# stop
	tgTmp.stop()

	#logging.info('Stopping reactor.')
	#reactor.stop()

	logging.info('Temperature: Exiting application.')
	sys.exit()

def fSignalHandler(signal, frame):		
	''' @fn fSignalHandler
		@brief : Signal handler.
	'''
	cleanExit()




# unit tests
def test_updateConfig():
	'''
		@brief : Change the config during running session.
	'''
	return

def test_getConfig():
	'''
		@brief : Report config during running session.
	'''
	return

def test_corruptConfig():
	'''
		@brief : Test behaviour if config is corrupted.
	'''
	return

def test_normalOperation():
	'''
		@brief : Test normal operation.
	'''
	tgTmp.loadConfig()
	tgTmp.startController()
	tgTmp.start()
	while True:
		time.sleep(1)
	

if __name__ == "__main__":

	argc = len(sys.argv)	

	# signal handlers
	signal.signal(signal.SIGINT, fSignalHandler)
	signal.signal(signal.SIGTERM, fSignalHandler)
	
	# root logger
	logger = logging.getLogger('')
	logger.setLevel(logging.DEBUG)
	
	# format for logging
	format = logging.Formatter(fmt='%(asctime)s %(levelname)8s [%(module)10s.%(funcName)10s %(lineno)d] %(message)s', datefmt='%b %d %H:%M:%S')

	# add stdout stream handler
	stdouth = logging.StreamHandler(sys.stdout)
	stdouth.setFormatter(format)
	logger.addHandler(stdouth)

	tgEvt = tgEvent.Event()
	tgTmp = Temperature(tgEvt)
	
	if sys.argv[1] == '--normal':
		test_normalOperation()

