#!/usr/bin/env python2

''' @file : tgEmail.py
	@brief : Email with SMTP.
'''
import os
import sys
import logging
import logging.handlers
import smtplib
from email.MIMEMultipart import MIMEMultipart 
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import threading 
import Queue 
import time
import json
import copy
import socket

from tggateway.tgModel import Model
import tggateway.tgEvent as tgEvent

EMAIL_CONFIG_FILE = '/home/tgard/config/email.json'


class Email(Model):
	''' @class : SmtpClient
		@brief : Contains smtplib.SMTP object which handles the connection, 
				MIME contruction and sending of emails to SMTP server.
					
				smtplib.STMP methods are run from the Thread object's run method.
				A Queue object is used to queue requests to send emails upon events
				triggered by the owner of the SmtpClient instance.
	'''

	def __init__(self, deviceName, eventMgr):
		
		super(Email, self).__init__('Email')

		self.eventMgr = eventMgr

		# some stats
		self.totalEmailsRequested = 0
		self.totalEmailsSent = 0
		self.interval = 1
		
		self.deviceName = deviceName
		# smtp server settings
		self.config = {}
		self.configured = False
	
		self.connectFail = True
		# Create the required mail queue
		self.queue = Queue.Queue(maxsize=30)
		self.mailserver = None

		# raise event if can't connect to smtp server after 30mins
		self.noConnectionTimeout = 1800 
		self.noConnectionTime = 0

		logging.debug('Email: Initialised.')
	
	def run(self):
		''' @fn run
			@brief : Executes in the thread.
					Handles connection to Smtp mail server.
					Pulls from the MIME messages from the queue and sends the emails.
		'''	
		lasttime = 0
		while True:
			
			# Sleep for a moment
			time.sleep(1)

			# Check if self.stop has been set
			if self.stopThread:
				break

			if time.time() - lasttime < self.interval:
				continue

			# not configured yet
			if not self.configured:
				logging.debug('Email: Not configured.')
				self.interval = 30
				lasttime = time.time()
				continue

			# Make sure there is something in the queue
			if self.queue.qsize() == 0:
				logging.debug('Email: Queue empty nothing todo.')
				self.interval = 10
				lasttime = time.time()
				continue
			else:
				self.interval = 1

			if not self.isConnected():
				self.connect()
				self.interval = 5
				lasttime = time.time()
				continue
	
			# pull from the queue (only if connected)
			message = self.queue.get()
			self.send(message)
							
			# inform queue that task is done
			self.queue.task_done()

			lasttime = time.time()

		# stopped thread at this point, process any remaining
		self.processRemaining()

		
	def processRemaining(self):
		''' @brief : Process outstanding emails in the queue. '''
		while True:
			if self.queue.qsize():
				message = self.queue.get()
				self.send(message)
				self.queue.task_done()
			else:
				break


	def connectionStatus(self):
		''' @fn connectionStatus
			@brief : Check status of connection.
		'''		
		logging.debug('Email: Still not connected.')
		self.interval = 60
		
		# no connection after 30 mins?
		if time.time() - self.noConnectionTime >= self.noConnectionTimeout:
			logging.warning('Email: No connection after 30mins.')
			self.noConnectionTime = time.time()

	def send(self, message):
		''' @fn send
			@return : Boolean
			@param message: List containing smtp user, list of recipient email addresses and the MIME
			@brief : Actually send the mail.
		'''
	 
		try:
			self.mailserver.sendmail(message[0], message[1], message[2])
		except Exception as e:
			logging.error("Email: SMTP error {0}.".format(e))
			return False
			
		# a config setting to report stats
		self.totalEmailsSent += 1
		logging.debug('Email: Sent. Total emails sent {0}.'.format(self.totalEmailsSent))
		return True

	def queueSize(self):
		''' @fn queueSize
			@return : Number of messages in the queue
			@brief : Wrapper around the queue.qsize() function.
		'''
		return self.queue.qsize()

	def queueMessage(self, from_addr, to_addr_list, msg):
		''' @fn queueMessage
			@return : Boolean
			@param from_addr : Smtp user
			@param to_addr_list : Recipient email address list 
			@param msg : MIME 
			@brief : Puts the email content in the queue which is processed by the worker thread.
		'''
	
		if not self.stopThread:
			message = [from_addr, to_addr_list, msg]
			self.queue.put(message)
			self.totalEmailsRequested += 1
			return True
		else:
			logging.warning("Email: Thread not running. Not adding to queue.")
			return False

	def mailRequest(self, addressList, emailData):
		''' @fn mailRequest
			@brief : Creates the MIME and pushes it on to the queue.
			@return : Boolean
			@param addressList : List of the email addresses to send this email to.
			@param emailData : Contains the email data i.e. subject and body
		'''
		try:
			logging.debug('Email: Subject {0}.'.format(emailData['subject']))
			logging.debug('Email: Body {0}.'.format(emailData['body']))
			if len(addressList) == 0:
				logging.debug('Email: No addresses to email.')
				return False
			
			# MIME setup
			mime = MIMEMultipart()
			mime['From'] = "TempNetZ {} <".format(self.deviceName) + self.config['User'] + ">"
			mime['To'] = ", ".join(addressList)
			mime['Subject'] = "{}".format(emailData['subject'])
			mime.attach(MIMEText(emailData['body'], 'html'))
		except Exception as e:
			logging.error('Email: Request error {0}.'.format(e))
			return False
		
		# put in queue
		return self.queueMessage(self.config['User'], addressList, mime.as_string())

	def mailImages(self, addressList=[], imagePaths=[]):
		''' @fn mailImage
			@brief : Creates MIME image and queues it.
			@return : Boolean
			@param addressList : List of the email addresses to send this email to.
			@param images : List of image paths
		'''
		try:

			# MIME setup
			mime = MIMEMultipart()
			mime['From'] = "TempNetZ {} <".format(self.deviceName) + self.config['User'] + ">"
			mime['To'] = ", ".join(addressList)
			mime['Subject'] = "Screenshots"

			for imagePath in imagePaths:
				if os.path.exists(imagePath):
					imageData = open(imagePath, "rb").read()
					image = MIMEImage(imageData, name=os.path.basename(imagePath))
					mime.attach(image)

			# put in queue
			return self.queueMessage(self.config['User'], addressList, mime.as_string())

		except Exception as e:
			logging.error('Email: Send images error {0}.'.format(e))
			return False		

	def connect(self):
		''' @fn connect
			@return : Boolean
			@brief : Connects and logs in to the mail server. 
			@note: Only called from the worker thread.
		'''
	
		# socket connection
		try:
			self.mailserver = smtplib.SMTP(self.config['Url'], self.config['Port'],"", 60)
		except Exception as e:
			logging.error("Email: SMTP error {0}.".format(e))
			self.connectFail = True
			return False
			
		# tls
		try:
			self.mailserver.starttls()
		except Exception as e:
			logging.error("Email: SMTP error {0}.".format(e))
			self.connectFail = True
			return False
			
		# login
		try:
			self.mailserver.login(self.config['User'], self.config['Pass'])
		except Exception as e:
			logging.error("Email: SMTP error {0}.".format(e))
			self.connectFail = True
			return False

		logging.info("Email: SMTP connected.")
		self.connectFail = False
		return True

	def disconnect(self):
		''' @fn disconnect
			@brief : Disconnects from the mail server. 
		'''
	
		try:
			self.mailserver.quit()
			logging.info("Email: SMTP disconnected.")
		except Exception as e :
			logging.error("Email: SMTP error {0}.".format(e))
		self.mailserver = None

	def isConnected(self):
		''' @fn isConnected
			@brief : Probes the status of the connection.
		'''
		
		if self.mailserver == None:
			return False
		try:
			status = self.mailserver.noop()[0]
		except Exception as e:
			logging.error("Email: SMTP error {0}.".format(e))
			status = -1
		
		if status == 250:
			return True  
		else: 
			return False

	def stop(self):
		''' @fn destroy
			@brief : Stops the worker thread and disconnects from the Smtp mail server.
		'''
		# Stop thread (will process remaining emails)
		super(Email, self).stop()

		# disconnect
		if not self.connectFail:
			self.disconnect()
		
		qsize = self.queueSize()
		logging.info("Email: Total emails requested {0}.".format(self.totalEmailsRequested))
		logging.info("Email: Total emails sent {0}.".format(self.totalEmailsSent))
		logging.info("Email: Remaining jobs {0}.".format(qsize))

	def setDeviceName(self, deviceName):
		'''
			@brief : Set device name in case of change.
		'''
		self.deviceName = deviceName
	
	def loadConfig(self):
		'''
			@brief : Load config from file.
		'''
		try:
			with open(EMAIL_CONFIG_FILE, 'r') as f:
				self.config = json.load(f)

			logging.debug('Email config:')
			logging.debug('	Smtp url: {0}.'.format(self.config['Url']))
			logging.debug('	Smtp port: {0}.'.format(self.config['Port']))
			logging.debug('	Smtp user: {0}.'.format(self.config['User']))
			logging.debug('	Smtp pass: {0}.'.format(self.config['Pass']))
			#logging.debug(' Report stats: {0}.'.format(self.config['Report']['Stats']))
			#logging.debug(' Report status: {0}.'.format(self.config['Report']['Status']))
			
			logging.info('Email: Config loaded from file.')
			self.configured = True

		except Exception as e:
			logging.error("Email: Load config error {0}.".format(e))
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_EMAIL, tgEvent.EVTOPIC_EML_NO_CONFIG, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_DATABASE])

	def dumpConfig(self):
		'''
			@brief : Dump config to file.
		'''
		try:
			with open(EMAIL_CONFIG_FILE, 'w') as f:
				json.dump(device, f)
		
			logging.info('Email: Config dumped to file.')
		
		except Exception as e:
			logging.error("Email: Dump config error {0}.".format(e))



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

			logging.debug('Email: SMTP set config.')

			self.configured = True
			return True
		except Exception as e:
			logging.error('Email: SMTP set config error {0}.'.format(e))
			# restore previous
			self.config = copy.deepcopy(backup)
			return False

	def getConfig(self):
		''' 
			@brief : Get config.
		'''
		return copy.deepcopy(self.config)

	def getLiveState(self):
		'''@brief Get live state'''
	
		logging.info("Email: Live state request")
	
		liveState = {}
		if self.connectFail:
			liveState['Connected'] = False
		else:
			liveState['Connected'] = True
		liveState['EmailsRequested'] = copy.copy(self.totalEmailsRequested)
		liveState['EmailsSent'] = copy.copy(self.totalEmailsSent)

		return liveState

	

def cleanExit():
	''' @fn cleanExit
		@brief : Clean exit handler when signal terminates program.
	'''	

	email.stop()
	logging.info('Email: Exiting application.')
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

	logging.info('Email: Starting application.')

	tgEml = Email('Tempgard')
	tgEml.loadConfig()
	#tgEml.start()

	#while True:
	#	time.sleep(1)
