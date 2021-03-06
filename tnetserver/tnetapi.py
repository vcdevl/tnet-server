import os
import sys
import logging
import logging.handlers
import signal
import threading
import time
import copy
import json
import subprocess
import threading
import queue
import collections
from functools import wraps
import paho.mqtt.client as mqtt

from tnetserver import tnetconfig, tnetuser, tnetnetman


TNET_UNIT_ID = 'TNET-123456789'
tnet_mqtt = None
tnet_apis = None
tnet_reqq = None

TnetRequest = collections.namedtuple('TnetRequest', 'client_id, topic, payload')

def check_policy(rsp_topic):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			global tnet_mqtt
			global TNET_UNIT_ID

			client_id = args[1]
			topic = args[2]

			# strip prefix from the client_id which should return one of the following {LCD, USB, LAN, HAM}
			prefix = client_id.split('-')[0]

			# process the topic by removing the APIREQ/{UNIT-d} part of the topic
			tpc = '/' + '/'.join(topic.split('/')[2:])

			if 'policies' in tnetconfig and \
				prefix in tnetconfig['policies'] and \
				tpc not in tnetconfig['policies'][prefix]:
				return func(*args, **kwargs)

			# check policy for client-id <-> api request
			rsp = {'success': False, 'data':None, 'error':'Policy restricts client from api request'}
			tnet_mqtt.publish_message(topic=rsp_topic.format(client_id, TNET_UNIT_ID), message=rsp)

		return wrapper
	return decorator

def send_message(rsp_topic):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			global tnet_mqtt
			global TNET_UNIT_ID

			client_id = args[1]
			rsp = {'success': False, 'data':{}, 'error':'Unknown error'}

			reply = func(*args, **kwargs)

			if 'success' in reply:
				rsp['success'] = reply['success']
			if 'data' in reply:
				rsp['data'] = reply['data']
			if 'error' in reply:
				rsp['error'] = reply['error']

			tnet_mqtt.publish_message(topic=rsp_topic.format(client_id, TNET_UNIT_ID), message=rsp)
		return wrapper
	return decorator

class DeviceGetInfoApi():
	''' handler for get device info request '''

	@check_policy(rsp_topic='APIRSP/{}/{}/devinfo/get')
	@send_message(rsp_topic='APIRSP/{}/{}/devinfo/get')
	def handler(self, client_id, topic, payload):
		return tnetdevice.get_info()

class DeviceSetInfoApi():
	''' handler for set device info request '''

	@check_policy(rsp_topic='APIRSP/{}/{}/devinfo/set')
	@send_message(rsp_topic='APIRSP/{}/{}/devinfo/set')
	def handler(self, client_id, topic, payload):
		return tnetdevice.update_info(payload)

class UserRegisterApi():
	''' handler for registering a user with a device '''

	@check_policy(rsp_topic='APIRSP/{}/{}/user/register')
	@send_message(rsp_topic='APIRSP/{}/{}/user/register')
	def handler(self, client_id, topic, payload):
		return tnetuser.register(payload)

class NetworkWifiEnableApi():
	''' handler for enabling the wifi radio on the device '''

	@check_policy(rsp_topic='APIRSP/{}/{}/net/wifi/modemon')
	@send_message(rsp_topic='APIRSP/{}/{}/net/wifi/modemon')
	def handler(self, client_id, topic, payload):
		return tnetnetman.wifi_radio_on()

class NetworkWifiDisableApi():
	''' handler for disabling the wifi radio on the device '''

	@check_policy(rsp_topic='APIRSP/{}/{}/net/wifi/modemoff')
	@send_message(rsp_topic='APIRSP/{}/{}/net/wifi/modemoff')
	def handler(self, client_id, topic, payload):
		return tnetnetman.wifi_radio_off()

"""class TemperatureNewApi():
	''' handler for new temperature session request'''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/new/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureRestartApi():
	''' handler for restart temperature session request'''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/restart/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureResumeApi():
	''' handler for resume temperature session request'''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/resume/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureGetApi():
	''' handler for temperature configuration request'''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureStopCtlApi():
	''' handler for stopping the 1-wire bus controller '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/stopctl/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureStartCtlApi():
	''' handler for starting the 1-wire bus controller '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/startctl/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureLogdataApi():
	''' handler for requesting log data '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/logdata/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureRealtimeDataApi():
	''' handler for requesting realtime data '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/temperature/realtimedata/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)



class UserLoginApi():
	''' handler for registering a user with a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/register/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class UserAddApi():
	''' handler for add a user to a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/add/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class UserDeleteApi():
	''' handler for delete a user from a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/delete/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class UserEditApi():
	''' handler for edit a user on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/edit/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)


class UserGetApi():
	''' handler for getting all users on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class SystemMetricsApi():
	''' handler for getting all system metrics on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/system/metrics/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class SystemShutdownApi():
	''' handler for reboot or shutdown a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/system/shutdown/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class AudioOnApi():
	''' handler for audio on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/audio/on/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class AudioOffApi():
	''' handler for audio on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/audio/off/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class AudioGetApi():
	''' handler for getting audio settings on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/audio/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkWifiScanApi():
	''' handler for scanning wifi on a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/scan/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkWifiConnectApi():
	''' handler for connecting device to wifi network '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/connect/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkWifiDisconnectApi():
	''' handler for disconnecting device from wifi network '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/disconnect/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkWifiForgetApi():
	''' handler for disabling a wifi network i.e. don't auto connect '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/forget/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)



class NetworkWifiGetApi():
	''' handler for getting wifi details on device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkCellularEnableApi():
	''' handler for enabling the 3g modem on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/cellular/enable/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkCellularDisableApi():
	''' handler for disabling the 3g modem on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/cellular/disable/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkCellularApnApi():
	''' handler for setting the APN so modem can connect to Internet '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/cellular/apn/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkCellularGetApi():
	''' handler for getting 3g modem details on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/cellular/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiJoinApi():
	''' handler for joining a hamachi network on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/join/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiLeaveApi():
	''' handler for leaving a hamachi network on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/leave/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiLoginApi():
	''' handler for hamachi network login on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/login/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiLogoutApi():
	''' handler for hamachi network logout on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/logout/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiNicknameApi():
	''' handler for setting hamachi nickname on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/nickname/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkHamachiGetApi():
	''' handler for getting hamachi details on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/hamachi/get/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkStateApi():
	''' handler for getting connectivity details on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/state/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)
"""

class TgMqtt(object):

	def __init__(self):
		#{TODO: get name from database }
		id = 'SERVER'
		self._mqtt = mqtt.Client(client_id=id)
		self._mqtt.on_connect = self.connected
		self._mqtt.on_publish = self.message_sent
		self._mqtt.on_message = self.message_received
		self._mqtt.on_disconnect = self.disconnected
		config = tnetconfig.get_config()
		self._mqtt.connect('localhost', config['mqtt']['port'])

	def start(self):
		self._mqtt.loop_start()

	def stop(self):
		self._mqtt.loop_stop()

	def publish_message(self, topic, message):
		''' Function callback so board can publish data '''

		logging.debug("Publish msg topic={} payload={}".format(topic, message))
		self._mqtt.publish(topic=topic, payload=json.dumps(message))

	def connected(self, client, userdata, flags, rc):
		''' Mqtt client connected to broker '''

		global tnet_apis
		logging.debug("Connected to MQTT broker")
		try:
			for tup in tnet_apis:
				logging.debug("Subscribing to topic {}".format(tup[0]))
				self._mqtt.subscribe(tup[0])
		except Exception as e:
			logging.error(e)

	def disconnected(self):
		''' Mqtt client disconnect from broker '''
		logging.debug('Disconnected from broker')

	def message_received(self, client, userdata, msg):
		''' Mqtt client received message from broker '''

		global tnet_apis
		global tnet_reqq
		logging.debug("Received MQTT msg: topic={}, payload={}, qos={}, retain={}".format(msg.topic, msg.payload, msg.qos, msg.retain))

		for tup in tnet_apis:
			if msg.topic in tup[0]:
				try:
					data = json.loads(msg.payload.decode('utf-8'))
					if 'client-id' in data:
						# enqueue request
						tnet_reqq.put(TnetRequest(client_id=data['client-id'], topic=msg.topic, payload=data))
					else:
						logging.warning('No client-id in payload data')
				except Exception as e:
					logging.error(e)

	def message_sent(self, client, userdata, mid):
		''' Mqtt client published message to broker
			mid is the message id '''

		logging.debug("Published MQTT msg: Mid = {}".format(mid))

def raise_alert(topic, payload):
	''' Public method to publish message from event manager '''

	global tnet_mqtt
	tnet_mqtt.publish_message(topic, payload)

def start_mqtt():
	''' create mqtt, register endpoints and api handlers '''

	global tnet_mqtt
	global tnet_apis
	global tnet_reqq

	tnet_apis = (
		('APIREQ/{}/devinfo/get'.format(TNET_UNIT_ID), DeviceGetInfoApi()),
		('APIREQ/{}/devinfo/set'.format(TNET_UNIT_ID), DeviceSetInfoApi()),
		('APIREQ/{}/user/register'.format(TNET_UNIT_ID), UserRegisterApi()),)
		('APIREQ/{}/net/wifi/modemon'.format(TNET_UNIT_ID), NetworkWifiEnableApi()),
		('APIREQ/{}/net/wifi/modemoff'.format(TNET_UNIT_ID), NetworkWifiDisableApi())

	tnet_reqq = queue.Queue(maxsize=50)
	tnet_mqtt = TgMqtt()
	tnet_mqtt.start()

	logging.debug('Starting queue handler')
	# dequeue messages and execute handlers
	while True:

		time.sleep(0.1)
		try:
			if not tnet_reqq.empty():
				request = tnet_reqq.get()
				for tup in tnet_apis:
					if request.topic in tup[0]:
						tup[1].handler(request.client_id, request.topic, request.payload)
				tnet_reqq.task_done()
			#else:
			#	logging.debug('No requests to dequeue')
		except Exception as e:
			logging.warning(e)
			continue
