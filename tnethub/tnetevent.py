#!/usr/bin/env python

''' @file : tgEvent.py
	@brief : Event handler.
'''

import signal
import sys
import time
import logging
import logging.handlers
import json
import Queue
from functools import wraps
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ServerEndpoint

from tggateway.tgDataLogger import TnetEventLogger
from tggateway.tgModel import Model

# Event classes
EVCLASS_LIVE    			= 'LVE'
EVCLASS_TEMP    			= 'TMP'
EVCLASS_SYSTEM 				= 'SYS'
EVCLASS_HAMACHI				= 'HAM'
EVCLASS_NETWORK				= 'NET'
EVCLASS_EMAIL				= 'EML'
EVCLASS_SMS 				= 'SMS'
EVCLASS_GATEWAY				= 'GWY'
EVCLASS_AUDVIS				= 'AUV'

# Event topics
EVTOPIC_LIVE_DATA 			= '0'

EVTOPIC_TEMP_NO_CONFIG 		= '000'
EVTOPIC_TEMP_CTRL_FAULT 	= '001'
EVTOPIC_TEMP_ALRM_A1    	= '002'
EVTOPIC_TEMP_ALRM_A2		= '003'
EVTOPIC_TEMP_STOP_SESH   	= '004'
EVTOPIC_TEMP_NEW_SESH   	= '005'
EVTOPIC_TEMP_RESTART_SESH   = '006'
EVTOPIC_TEMP_RESUME_SESH   	= '007'
EVTOPIC_TEMP_NO_SENSORS     = '008'
EVTOPIC_TEMP_NEW_DATA 		= '009'

EVTOPIC_SYS_NO_CONFIG 		= '100'
EVTOPIC_SYS_SHUTDOWN 		= '101'
EVTOPIC_SYS_RESTART 		= '102'
EVTOPIC_SYS_POWERON			= '103'
EVTOPIC_SYS_UPDATING 		= '104'
EVTOPIC_SYS_DISKFULL  	 	= '105'
EVTOPIC_SYS_POWERCHANGE    	= '106'
EVTOPIC_SYS_BATTERYLOW 		= '107'

EVTOPIC_HAM_NO_CONFIG 		= '200'
EVTOPIC_HAM_JOINED 			= '201'
EVTOPIC_HAM_LEAVE 			= '202'
EVTOPIC_HAM_OFFLINE			= '203'
EVTOPIC_HAM_ONLINE 			= '204'

EVTOPIC_GWY_NO_CONFIG 		= '300'
EVTOPIC_GWY_PROVISIONED		= '301'
EVTOPIC_GWY_FACTORY_RESET	= '302'
EVTOPIC_GWY_NEW_ADMIN_PSK 	= '303'
EVTOPIC_GWY_PSK_RESET 		= '304'

EVTOPIC_AUV_NO_CONFIG		= '400'
EVTOPIC_AUV_A1_ON			= '401'
EVTOPIC_AUV_A1_OFF			= '402'
EVTOPIC_AUV_A2_ON			= '403'
EVTOPIC_AUV_A2_OFF			= '404'
EVTOPIC_AUV_BUZZ_ON			= '405'
EVTOPIC_AUV_BUZZ_OFF		= '406'
EVTOPIC_AUV_OFF 			= '407'
EVTOPIC_AUV_MUTE			= '408'
EVTOPIC_AUV_STATE_A0		= '409'
EVTOPIC_AUV_STATE_A1		= '410'
EVTOPIC_AUV_STATE_A2		= '411'

EVTOPIC_EML_NO_CONFIG		= '500'
EVTOPIC_EML_SMTP_FAIL		= '501'
EVTOPIC_EML_SEND_FAIL 		= '502'

EVTOPIC_SMS_NO_CONFIG 		= '600'
EVTOPIC_SMS_SEND_FAIL 		= '601'

EVTOPIC_NET_NO_CONFIG 		= '700'
EVTOPIC_NET_IFACECHANGE 	= '701'
EVTOPIC_NET_NOINET 			= '702'


# Event priorities
EVENT_PRIORITY_LOW			= 0
EVENT_PRIORITY_MEDIUM   	= 1
EVENT_PRIORITY_HIGH			= 2

# Event action types
EVACTION_STREAM				= 1
EVACTION_NOTIFICATIONS		= 2
EVACTION_AUDIOVISUAL   		= 3
EVACTION_DATABASE 			= 4

event_model = None


class StreamerProtocol(Protocol):
	''' @class StreamerProtocol
		@brief : Publishes data on socket. No receive.
	'''

	def __init__(self, connections):
		''' @class __init__
			@brief : Initilise
			@note : Reference to connections is a list of DataPublisher instances.
		'''
		self.connections = connections

	def connectionMade(self):
		''' @fn connectionMade
			@brief : New socket connection made. Add to list of connections.
		'''
		if self not in self.connections:
			logging.debug('Streamer: Connection made.')
			self.connections.append(self)

	def connectionLost(self, reason):
		''' @fn connectionLost
			@brief : Lost socket connection. Remove from list of connections.
		'''
		if self in self.connections:
			logging.debug('Streamer: Connection closed. Reason = {}.'.format(reason))
			self.connections.remove(self)

	def publish(self, data):
		''' @fn publish
			@brief : Send data on socket
		'''
		self.transport.write(data)
		logging.debug('Streamer: Data written {}.'.format(data))


class StreamerFactory(Factory):
	''' @class StreamerFactory
		@brief : Data Publisher factory.
	'''

	def __init__(self):
		''' @class __init__
			@brief : Initilise
		'''
		self.connections = []


	def buildProtocol(self, addr):
		''' @fn buildProtocol
			@brief : Build protocol that will be handled by incomming connection.
			@param addr : The socket address of the incomming connection.
		'''

		logging.info('Streamer Factory: Incomming connection {0}.'.format(addr))
		return StreamerProtocol(self.connections)

	def publish(self, newData):
		''' @class publish
			@brief : Publish new data to all connections (listeners)
			@param measurement : The data to send.
		'''

		if len(self.connections) == 0:
			logging.debug('Streamer: No connections, nothing to publish.')
			return

		for streamer in self.connections:
			streamer.publish(newData)



class Event(Model):
	''' @class : EventHandler.py
		@brief : Event handling class.
	'''
	# def __init__(self, reactor, eventStreamer, emailPublisher, smsPublisher, ioHandler):
	def __init__(self, reactor=None, notifications=None, audvis=None, streamPort=54113):
		''' @fn init
			@brief : Class initialisation.
		'''
		super(Event, self).__init__('Event')
		self.streamFactory = StreamerFactory()
		server = TCP4ServerEndpoint(reactor, interface='0.0.0.0', port=streamPort)
		server.listen(self.streamFactory)

		self.notifications = notifications
		self.audiovisual = audvis

		self.queue = Queue.Queue(maxsize=50)
		self.interval = 1
		self.eventLogger = TnetEventLogger()

		logging.info('Event: Initialised.')

	def raise_event(self, evClass, evTopic, evData, evPriority, evActions):
		''' @fn raiseEvent
			@brief : Put event on the queue.
		'''

		event = {}
		event['Class'] = evClass
		event['Topic'] = evTopic
		event['Priority'] = evPriority
		event['Data'] = evData
		event['Actions'] = evActions
		# pk for database
		event['Pk'] = int(time.time())
		event['Time'] = time.strftime("%H:%M %d/%m/%Y", time.localtime(time.time()))

		try:
			self.queue.put(event,block=False)
			logging.debug('Queue size = {}.'.format(self.queue.qsize()))
		except Exception as e:
			logging.warning(e)

	def run(self):

		lastTempEvent = 0
		while True:

			time.sleep(0.5)

			if self.stopThread:
				break

			if self.queue.qsize() == 0:
				continue

			# pull from queue
			event = self.queue.get()
			self.queue.task_done()

			logging.debug('Class = {} Topic = {} Priority = {} Action = {} Data = {} Time = {} Pk = {}.'.format(
				event['Class'],
				event['Topic'],
				event['Priority'],
				event['Actions'],
				event['Data'],
				event['Time'],
				event['Pk']))


			# temperature event not received for some time, do something
			if event['Topic'] == EVTOPIC_TEMP_NEW_DATA:
				# something wrong? have not received temperature event in 3 minutes
				if lastTempEvent != 0 and (time.time() - lastTempEvent) >= 180:
					logging.warning('Event: Not received temperature event in 3 minutes.')

				lastTempEvent = time.time()

			# what action(s) to perform for this event
			# to stream
			if EVACTION_STREAM in event['Actions']:
				self.streamFactory.publish('<{}:{}:{}:{}>'.format(event['Class'], event['Topic'], event['Priority'], event['Data']))

			# to database
			if EVACTION_DATABASE in event['Actions']:
				self.eventLogger.log(event['Pk'], event['Class'], event['Topic'], event['Priority'], event['Data'])

			# to audio visual
			if EVACTION_AUDIOVISUAL in event['Actions']:
				self.audiovisual.alert(event['Topic'])

			# to notifications
			if EVACTION_NOTIFICATIONS in event['Actions']:
				self.notifications.alert(event)


def event_start():
	''' create model and run it '''

	global event_model
	event_model = Event()
	event_model.start()

def event_stop():
	''' stop event model '''

	global event_model
	event_model.stop()

def event_raise(ev_class, ev_topic, ev_data, ev_priority, ev_actions):
	''' raise an event '''

	global event_model
	event_model.raise_event(ev_class, ev_topic, ev_data, ev_priority, ev_actions)
