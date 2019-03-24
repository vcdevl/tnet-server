#!/usr/bin/env python3

''' @file : tgSystem.py
    @brief : Tempgard system module.
'''

import time 
import logging
import sys
import signal
import subprocess
import os
from copy import copy

from tggateway.tgModel import Model
import tggateway.tgEvent as tgEvent

SYS_CLASS_PS_AC         	= "/sys/class/power_supply/ac/online"
SYS_CLASS_PS_USB        	= "/sys/class/power_supply/usb/online"
SYS_CLASS_PS_BAT        	= "/sys/class/power_supply/battery/online"
SYS_CLASS_PS_BAT_LEVEL  	= "/sys/class/power_supply/battery/capacity"

POWER_OFFLINE 				= 0
POWER_ONLINE  				= 1

ACTIVE_POWER_UNKNOWN		= 0
ACTIVE_POWER_AC   			= 1
ACTIVE_POWER_BAT  			= 2
ACTIVE_POWER_USB  			= 3

INTERFACE_UNKNOWN   		= 0
INTERFACE_ETHERNET  		= 1
INTERFACE_WIFI      		= 2
INTERFACE_CELL      		= 3

SHUTDOWN_CAUSE_USER 		= 0
SHUTDOWN_CAUSE_LOWBATTERY	= 1

HumanReadblePowerInterface = ['Unknown', 'AC Mains', 'Battery', 'Usb']


class System(Model):
	''' @class : System class
		@brief : Power off, restart etc.
	'''
	def __init__(self, eventMgr=None):
		''' @fn : __init__
			@brief : Class initialisation.
		'''
		super(System, self).__init__('System')
		self.eventMgr = eventMgr
		# can report metrics at different configurable frequency
		self.memory = 0
		self.cpu = 0
		self.disk = 0
		self.powerAc = POWER_OFFLINE
		self.powerUsb = POWER_OFFLINE
		self.powerBat = POWER_OFFLINE
		self.batLevel = 100
		self.uptime = 0
		self.currentPower = ACTIVE_POWER_UNKNOWN
		self.lowPowerTriggered = False
		self.shutdownTriggered = False

		logging.info('System: Initialised.')

	def shutdown(self):
		''' @brief : Shutdown gateway in 1 minute'''
		p = subprocess.Popen(['shutdown', '-h', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.communicate()
		logging.warning('System: Shutting down 1 minute from now.')

	def reboot(self):
		''' @brief : Reboot gateway. '''
		logging.warning('System: Rebooting now.')
		p = subprocess.Popen(['shutdown', '-r', 'now'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.communicate()

	def getLiveState(self):
		''' @brief : Get live state. '''

		metrics = '{0},{1},{2},{3},{4},{5},{6},{7}'.format(self.cpu, 
													self.memory,
													self.disk,
													self.powerAc,
													self.powerUsb,
													self.powerBat,
													self.batLevel,
													self.uptime)
		return metrics

	def batlevCheck(self):
		''' @fn batlevCheck
			@brief : Get battery level of battery.
		'''
		try:
			with open(SYS_CLASS_PS_BAT_LEVEL, 'r') as f:
				value = f.readline().strip()
		except:
			logging.critical("Failure to open: " + SYS_CLASS_PS_BAT_LEVEL)
			return

		self.batLevel = int(value)

		# only check for triggers if running on battery
		if self.currentPower != ACTIVE_POWER_BAT:
			return

		# shutting down now
		if self.batLevel <= 10 and not self.shutdownTriggered:
			self.shutdownTriggered = True
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, tgEvent.EVTOPIC_SYS_SHUTDOWN, 'Low battery', tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])
			self.shutdown()

		# bat level reached 25% ?
		elif self.batLevel <= 25 and not self.lowPowerTriggered:
			self.lowPowerTriggered = True
			self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, tgEvent.EVTOPIC_SYS_BATTERYLOW, '{}'.format(self.batLevel), tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])

		elif self.batLevel > 25:
			self.shutdownTriggered = False
			self.lowPowerTriggered = False

	def powerCheck(self, filepath):
		''' @fn powerCheck
			@param filepath: Sysfs path for power supply.
			@brief : Checks the value of /sys/class/power_supply/$/online file.
			@return : 1 if online or 0 if not.
		'''
		try:
			with open(filepath, 'r') as f:
				value = f.readline().strip()
		except Exception as e:
			logging.error("System: Unexpected error {}.".format(e))
			return POWER_OFFLINE

		if int(value):
			return POWER_ONLINE
		else:
			return POWER_OFFLINE

	def cpuCheck(self):
		''' @fn : cpuCheck
			@brief : Percentage CPU usage for each core and total.
			@details : Read /proc/stat first 3 lines with columns 
						user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
		'''
		'''try:
			with open('/proc/stat'.encode('utf-8'), 'r') as f:
				value = f.decode().readline().strip()

				PrevIdle = previdle + previowait
				Idle = idle + iowait

				PrevNonIdle = prevuser + prevnice + prevsystem + previrq + prevsoftirq + prevsteal
				NonIdle = user + nice + system + irq + softirq + steal

				PrevTotal = PrevIdle + PrevNonIdle
				Total = Idle + NonIdle

				# differentiate: actual value minus the previous one
				totald = Total - PrevTotal
				idled = Idle - PrevIdle

				CPU_Percentage = (totald - idled)/totald
		except Exception as e:
			logging.error("System: Unexpected error {0}.".format(e))
		'''
		self.cpu = 0

	def memCheck(self):
		''' @fn : memCheck
			@brief : Check memory usage.
		'''
		# if disk full, raise event 
		# self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, tgEvent.EVTOPIC_SYS_DISKFULL, '{}'.format(self.disk), 
		# tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])
		try:
			totalMB = os.popen('free -m | grep Mem: | tr -s [:blank:] | cut -d" " -f2').read().strip()
			usedMB = os.popen('free -m | grep Mem: | tr -s [:blank:] | cut -d" " -f3').read().strip()
			self.memory = int((float(usedMB) / float(totalMB)) * 100)
		except:
			loggin.debug('System: Unable to process disk usage')
			self.disk = 0

	def diskCheck(self):
		''' @fn : diskCheck
			@brief : Check disk usage.
		'''
		# if disk full, raise event 
		# self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, tgEvent.EVTOPIC_SYS_DISKFULL, '{}'.format(self.disk), 
		# tgEvent.EVENT_PRIORITY_HIGH, [tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])
		try:
			outobj = os.popen('df -Bm | grep /dev/root | tr -s [:blank:] | cut -d" " -f5')
			out = outobj.read()
			if '%\n' in out:
				self.disk = int(out[:-2])
				if self.disk < 1 or self.disk > 100:
					self.disk = 0
			else:
				self.disk = 0
		except:
			loggin.debug('System: Unable to process disk usage')
			self.disk = 0
		
	def upTime(self):
		'''
			@brief : Uptime of os in seconds.
		'''
		try:
			p = subprocess.Popen(['cat', '/proc/uptime'],stdout=subprocess.PIPE)
			o,e = p.communicate()
			# returns 2 numbers, first is uptime in seconds, second is idle time in seconds
			self.uptime = o.split()[0]
		except Exception as e:
			logging.warning('System: Unable to probe uptime {}.'.format(e))
			self.uptime = 0


	def powerChange(self):
		''' @brief : Check power interface '''

		powerInterface = ACTIVE_POWER_UNKNOWN

		if self.powerAc == POWER_ONLINE:
			powerInterface = ACTIVE_POWER_AC

		elif self.powerBat == POWER_ONLINE:
			powerInterface = ACTIVE_POWER_BAT

		# power interface changed, raise event
		if powerInterface != self.currentPower and powerInterface != ACTIVE_POWER_UNKNOWN and self.currentPower != ACTIVE_POWER_UNKNOWN:
			if powerInterface == ACTIVE_POWER_AC:
				self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, 
										tgEvent.EVTOPIC_SYS_POWERCHANGE, 
										'{},{}'.format(HumanReadblePowerInterface[ACTIVE_POWER_BAT], HumanReadblePowerInterface[ACTIVE_POWER_AC]), 
										tgEvent.EVENT_PRIORITY_HIGH, 
										[tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])
			
			elif powerInterface == ACTIVE_POWER_BAT:
				self.eventMgr.raiseEvent(tgEvent.EVCLASS_SYSTEM, 
										tgEvent.EVTOPIC_SYS_POWERCHANGE, 
										'{},{}'.format(HumanReadblePowerInterface[ACTIVE_POWER_AC], HumanReadblePowerInterface[ACTIVE_POWER_BAT]),
										tgEvent.EVENT_PRIORITY_HIGH,
										[tgEvent.EVACTION_STREAM, tgEvent.EVACTION_DATABASE, tgEvent.EVACTION_NOTIFICATIONS])	

		self.currentPower = powerInterface

	def run(self):
		''' @fn run
			@brief : Executes in the thread.
				Polls sysfs files to check metrics.
		'''

		lazycheck = 0
		while True:

			time.sleep(3)

			if self.stopThread:
				break
			
			self.powerAc = self.powerCheck(SYS_CLASS_PS_AC)
			self.powerUsb = self.powerCheck(SYS_CLASS_PS_USB)
			self.powerBat = self.powerCheck(SYS_CLASS_PS_BAT)
			self.powerChange()

			# check these every minute
			if time.time() - lazycheck < 60:
				continue
				
			self.batlevCheck()
			self.cpuCheck()
			self.memCheck()
			self.diskCheck()
			self.upTime()
			lazycheck = time.time()

def cleanExit():
	''' @fn cleanExit
		@brief : Clean exit handler when signal terminates program.
	'''	
	# destroy
	system.stop()
	logging.info('System: Exiting application.')
	sys.exit()

def fSignalHandler(signal, frame):		
	''' @fn fSignalHandler
		@brief : Signal handler.
	'''
	cleanExit()


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

	evMgr = tgEvent.Event()
	system = System(evMgr)
	system.start()




