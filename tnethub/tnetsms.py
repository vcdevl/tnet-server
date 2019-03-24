#!/usr/bin/env python2

''' @file : tgSms.py
	@brief : Sms with ofono.
'''
import sys
import logging
import tggateway.tgEvent as tgEvent


class Sms(object):
	def __init__(self, eventMgr):
		self.eventMgr = eventMgr
		logging.info('Sms: Initialised.')

	def send(self, number, message):

		# if fail, raise event
		# self.eventMgr.raiseEvent(tgEvent.EVCLASS_SMS, tgEvent.EVTOPIC_SMS_SEND_FAIL, '', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_DATABASE])
		return

def cleanExit():
	''' @fn cleanExit
		@brief : Clean exit handler when signal terminates program.
	'''	
	logging.info('Sms: Exiting application.')
	sys.exit()

def fSignalHandler(signal, frame):		
	''' @fn fSignalHandler
		@brief : Signal handler.
	'''
	cleanExit()

if __name__ == '__main__':
	
	logging.info('Sms: Starting application.')

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

	tgEvt = TgEvent.Event()
	tgSms = Sms(tgEvt)
