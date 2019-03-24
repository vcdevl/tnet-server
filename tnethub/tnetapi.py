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
import paho.mqtt.client as mqtt

import tggateway.tgEvent as tgevent
import tggateway.tgHamachi as tghamachi
import tggateway.tgTemperature as tgtemperature
import tggateway.tgConfiguration as tgconfiguration
import tggateway.tgMetrics as tgmetrics
import tggateway.tgEmail as tgemail
import tggateway.tgNetwork as tgnetwork

TNET_UNIT_ID = '1234567890'
tg_mqtt = None
tg_apis = None

TNET_API_DEVICE_DISCOVERY_REQ = '{}/discover/REQ'.format(TNET_UNIT_ID)
TNET_API_DEVICE_DISCOVERY_REQ = '{}/{}/discover/RSP'.format(TNET_UNIT_ID)

def validate_payload(keys=[],list_of_items=False):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):

			topic = args[1]
			payload = args[2]

			if not all(key in payload for key in ['success', 'data', 'error']):
				print('Payload invalid for {}'.format(topic))
				return

			if not payload['success']:
				print('Api {} response failed with {}'.format(topic, payload['error']))
				return

			if list_of_items:
				for item in payload['data']:
					if not all(x in item for x in keys):
						print('Payload missing fields in data')
						return
			else:
				if not all(x in payload['data'] for x in keys):
					print('Payload missing fields in data')
					return

			func(*args, **kwargs)

		return wrapper
	return decorator

class DiscoverApi():
	''' handler for device discovery request '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		# grab all config
		device_profile = {}
		rsp = {'success': True, 'data':device_profile, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/discover/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class TemperatureNewApi():
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

class UserRegisterApi():
	''' handler for registering a user with a device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/user/register/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

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

class NetworkWifiEnableApi():
	''' handler for enabling the wifi radio on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/enable/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

class NetworkWifiDisableApi():
	''' handler for disabling the wifi radio on the device '''

	def handler(self, client_id, topic, payload):
		global mqtt_client
		rsp = {'success': True, 'data':{}, 'error':''}
		mqtt_client.publish_message(topic='{}/{}/network/wifi/disable/RSP'.format(client_id, TNET_UNIT_ID), message=rsp)

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


class TgMqtt(object):

	def __init__(self):
		self._endpoints = {}
		#{TODO: get name from database }
		id = 'LCD'
		self._mqtt = mqtt.Client(client_id=id)
		self._mqtt.on_connect = self.connected
		self._mqtt.on_publish = self.message_sent
		self._mqtt.on_message = self.message_received
		self._mqtt.on_disconnect = self.disconnected
		config = tgconfiguration.get_config()
		self._mqtt.connect('localhost', config['mqtt']['port'])

	def start(self):
		self._mqtt.loop_start()
		pass

	def stop(self):
		self._mqtt.loop_stop()
		pass

	def register_endpoint(self, in_topic, out_topic, endpoint):
		if in_topic not in self._endpoints:
			self._endpoints[in_topic] = (out_topic, endpoint)

	def publish_message(self, topic, message):
		''' Function callback so board can publish data '''

		logging.debug("Publish msg topic={} payload={}".format(topic, message))
		self._mqtt.publish(topic=topic, payload=json.dumps(message))

	def connected(self, client, userdata, flags, rc):
		''' Mqtt client connected to broker '''

		logging.debug("Connected to MQTT broker")

		for in_topic in self._endpoints:
			logging.debug("Subscribing to topic {} [Tuple = {}]".format(in_topic, self._endpoints[in_topic]))
			self._mqtt.subscribe(in_topic)

	def message_received(self, client, userdata, msg):
		''' Mqtt client received message from broker '''

		global tg_apis
		logging.debug("Received MQTT msg: topic={}, payload={}, qos={}, retain={}".format(msg.topic, msg.payload, msg.qos, msg.retain))

		for tup in tg_apis:
			if msg.topic in tup[0]:
				data = json.loads(msg.payload.decode('utf-8'))
				tg_apis[msg.topic](client, msg.topic, data)

	def message_sent(self, client, userdata, mid):
		''' Mqtt client published message to broker
			mid is the message id '''

		logging.debug("Published MQTT msg: Mid = {}".format(mid))


def start_mqtt():
	''' create mqtt, register endpoints and api handlers '''
	global tg_mqtt
	global tg_apis


	tg_apis = (('{}/discover/REQ'.format(TNET_UNIT_ID), DiscoverApi()),
				('{}/temperature/new/REQ'.format(TNET_UNIT_ID), TemperatureNewApi()),
				('{}/temperature/restart/REQ'.format(TNET_UNIT_ID), TemperatureRestartApi()),
				('{}/temperature/resume/REQ'.format(TNET_UNIT_ID), TemperatureResumeApi()),
				('{}/temperature/get/REQ'.format(TNET_UNIT_ID), TemperatureGetApi()),
				('{}/temperature/stopctl/REQ'.format(TNET_UNIT_ID), TemperatureStopCtlApi()),
				('{}/temperature/startctl/REQ'.format(TNET_UNIT_ID), TemperatureStartCtlApi()),
				('{}/temperature/logdata/REQ'.format(TNET_UNIT_ID), TemperatureLogdataApi()),
				('{}/temperature/realtimedata/REQ'.format(TNET_UNIT_ID), TemperatureRealtimeDataApi()),
				('{}/user/register/REQ'.format(TNET_UNIT_ID), UserRegisterApi()),
				('{}/user/login/REQ'.format(TNET_UNIT_ID), UserLoginApi()),
				('{}/user/add/REQ'.format(TNET_UNIT_ID), UserAddApi()),
				('{}/user/delete/REQ'.format(TNET_UNIT_ID), UserDeleteApi()),
				('{}/user/edit/REQ'.format(TNET_UNIT_ID), UserEditApi()),
				('{}/user/get/REQ'.format(TNET_UNIT_ID), UserGetApi()),
				('{}/system/metrics/REQ'.format(TNET_UNIT_ID), SystemMetricsApi()),
				('{}/system/shutdown/REQ'.format(TNET_UNIT_ID), SystemShutdownApi()),
				('{}/audio/on/REQ'.format(TNET_UNIT_ID), AudioOnApi()),
				('{}/audio/off/REQ'.format(TNET_UNIT_ID), AudioOffApi()),
				('{}/audio/get/REQ'.format(TNET_UNIT_ID), AudioGetApi()),
				('{}/network/wifi/scan/REQ'.format(TNET_UNIT_ID), NetworkWifiScanApi()),
				('{}/network/wifi/connect/REQ'.format(TNET_UNIT_ID), NetworkWifiConnectApi()),
				('{}/network/wifi/disconnect/REQ'.format(TNET_UNIT_ID), NetworkWifiDisconnectApi()),
				('{}/network/wifi/forget/REQ'.format(TNET_UNIT_ID), NetworkWifiForgetApi()),
				('{}/network/wifi/enable/REQ'.format(TNET_UNIT_ID), NetworkWifiEnableApi()),
				('{}/network/wifi/disable/REQ'.format(TNET_UNIT_ID), NetworkWifiDisableApi()),
				('{}/network/wifi/get/REQ'.format(TNET_UNIT_ID), NetworkWifiGetApi()),
				('{}/network/cellular/enable/REQ'.format(TNET_UNIT_ID), NetworkCellularEnableApi()),
				('{}/network/cellular/disable/REQ'.format(TNET_UNIT_ID), NetworkCellularDisableApi()),
				('{}/network/cellular/get/REQ'.format(TNET_UNIT_ID), NetworkCellularGetApi()),
				('{}/network/cellular/apn/REQ'.format(TNET_UNIT_ID), NetworkCellularApnApi()),
				('{}/network/hamachi/join/REQ'.format(TNET_UNIT_ID), NetworkHamchiJoinApi()),
				('{}/network/hamachi/leave/REQ'.format(TNET_UNIT_ID), NetworkHamchiLeaveApi()),
				('{}/network/hamachi/login/REQ'.format(TNET_UNIT_ID), NetworkHamchiLoginApi()),
				('{}/network/hamachi/logout/REQ'.format(TNET_UNIT_ID), NetworkHamchiLogoutApi()),
				('{}/network/hamachi/nickname/REQ'.format(TNET_UNIT_ID), NetworkHamchiNicknameApi()),
				('{}/network/hamachi/get/REQ'.format(TNET_UNIT_ID), NetworkHamchiGetApi()),
				('{}/network/state/REQ'.format(TNET_UNIT_ID), NetworkStateApi()))
	tg_mqtt = TgMqtt()
	tg_mqtt.start()
