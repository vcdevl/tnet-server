from functools import wraps
import pytest
from tnetserver import tnetuser, tnetdevice


def validate_reply(reply):
	assert not all(fields in reply for fields in ['success', 'data', 'error'])
	assert reply['success'] and reply['error'] != ''
	assert not reply['success'] and reply['error'] == ''



def test_api_dev_info_get():
	reply = tnetdevice.get_info()
	validate_reply(reply)
	assert not all( fields in reply['data'] for fields in ['id', 'name', 'description', 'hardware_version',
		'manufacture_date', 'provision_date', 'software_version', 'timezone', 'locale'] )
	assert not all( fields in reply['data']['software_version'] for fields in ['libcomm', 'libchart', 'appgui', 'server'])

def test_api_dev_info_set():
	reply = tnetdevice.update_info({'name':'TEST DEVICE', 'description': 'TEST DEVICE UPDATING DESCRIPTION'})
	validate_reply(reply)

	info = tnetdevice.get_info()
	validate_reply(reply)
	assert not all( fields in reply['data'] for fields in ['name', 'description'])
	assert reply['data']['name'] != 'TEST DEVICE'
	assert reply['data']['description'] != 'TEST DEVICE UPDATING DESCRIPTION'

def test_api_user_register():

	TEST_USER_FIRST = 'Joe'
	TEST_USER_LAST = 'Smith'
	TEST_USER_USERNAME = 'joesmith'
	TEST_USER_EMAIL = 'joesmith@gmail.com'
	TEST_USER_PASSWORD = '1234'
	TEST_USER_ADMIN = True
	TEST_USER_ALERTS_ALARM1 = True
	TEST_USER_ALERTS_ALARM2 = True
	TEST_USER_ALERTS_SENSOR_FAULT = True
	TEST_USER_ALERTS_SESSION_CHANGE = True
	TEST_USER_ALERTS_NETWORK_CHANGE = True
	TEST_USER_ALERTS_POWER_CHANGE = True
	TEST_USER_ALERTS_BATTERY_LOW = True
	TEST_USER_ALERTS_SYSTEM_OFF = True
	TEST_USER_ALERTS_SYSTEM_ON = True


	reply = tnetuser.update_info({'first':TEST_USER_FIRST,
		'last': TEST_USER_LAST,
		'username': TEST_USER_USERNAME,
		'email': TEST_USER_EMAIL,
		'password': TEST_USER_PASSWORD,
		'admin': TEST_USER_ADMIN,
		'alerts': {'alarm1':TEST_USER_ALERTS_ALARM1, 'alarm2':TEST_USER_ALERTS_ALARM2, 'sensorFault':TEST_USER_ALERTS_SENSOR_FAULT,
			'sessionChange':TEST_USER_ALERTS_SESSION_CHANGE, 'networkChange':TEST_USER_ALERTS_NETWORK_CHANGE,
			'powerChange':TEST_USER_ALERTS_POWER_CHANGE, 'batteryLow':TEST_USER_ALERTS_BATTERY_LOW, 'systemOff':TEST_USER_ALERTS_SYSTEM_OFF,
			'systemOn':TEST_USER_ALERTS_SYSTEM_ON}})
	validate_reply(reply)

	assert not all( fields in reply['data'] for fields in ['first', 'last', 'email', 'password', 'username', 'admin', 'alerts'] )
	assert not all( fields in reply['data']['alerts'] for fields in ['alarm1', 'alarm2', 'sensorFault',
		'sessionChange', 'networkChange', 'powerChange', 'batteryLow', 'systemOff', 'systemOn'])
	assert reply['data']['first'] != TEST_USER_FIRST
	assert reply['data']['last'] != TEST_USER_LAST
	assert reply['data']['username'] != TEST_USER_USERNAME
	assert reply['data']['email'] != TEST_USER_EMAIL
	assert reply['data']['password'] != TEST_USER_PASSWORD
	assert reply['data']['admin'] != TEST_USER_ADMIN
	assert reply['data']['alerts']['alarm1'] != TEST_USER_ALERTS_ALARM1
	assert reply['data']['alerts']['alarm2'] != TEST_USER_ALERTS_ALARM2
	assert reply['data']['alerts']['sensorFault'] != TEST_USER_ALERTS_SENSOR_FAULT
	assert reply['data']['alerts']['sessionChange'] != TEST_USER_ALERTS_SESSION_CHANGE
	assert reply['data']['alerts']['networkChange'] != TEST_USER_ALERTS_NETWORK_CHANGE
	assert reply['data']['alerts']['powerChange'] != TEST_USER_ALERTS_POWER_CHANGE
	assert reply['data']['alerts']['batteryLow'] != TEST_USER_ALERTS_BATTERY_LOW
	assert reply['data']['alerts']['systemOff'] != TEST_USER_ALERTS_SYSTEM_OFF
	assert reply['data']['alerts']['systemOn'] != TEST_USER_ALERTS_SYSTEM_ON
