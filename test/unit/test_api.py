import json
import os
import sys
import signal
import logging
from functools import wraps
import pytest
from tnetserver import tnetuser, tnetdevice, tnetdatabase, tnetconfig


def validate_reply(reply):
	assert all(fields in reply for fields in ['success', 'data', 'error']), "Missing field(s) in reply"
	if reply['success']:
		assert reply['success'] and reply['error'] == ''
	else:
		assert not reply['success'] and reply['error'] != ''



def api_dev_info_get():
	reply = tnetdevice.get_info()
	print('Device info = {}'.format(reply))
	validate_reply(reply)
	assert all( fields in reply['data'] for fields in ['id', 'name', 'description', 'hardware_version',
		'manufacture_date', 'provision_date', 'software_version', 'timezone', 'locale'] )
	assert all( fields in reply['data']['software_version'] for fields in ['libcomm', 'libchart', 'appgui', 'server'])

def api_dev_info_set():

	TEST_DEVICE_NAME = 'ROCK CRUSHER'
	TEST_DEVICE_DESCRIPTION = 'SMASHES HARD ROCKS TO DUST'

	reply = tnetdevice.update_info({'name':TEST_DEVICE_NAME, 'description': TEST_DEVICE_DESCRIPTION})
	validate_reply(reply)

	info = tnetdevice.get_info()
	validate_reply(reply)
	assert all( fields in reply['data'] for fields in ['name', 'description'])
	assert reply['data']['name'] == TEST_DEVICE_NAME
	assert reply['data']['description'] == TEST_DEVICE_DESCRIPTION

def api_user_register():

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


	reply = tnetuser.register({'first':TEST_USER_FIRST,
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
	print('Register reply = {}'.format(reply))
	assert all( fields in reply['data'] for fields in ['first', 'last', 'email', 'password', 'username', 'admin', 'alerts'] )
	assert all( fields in reply['data']['alerts'] for fields in ['alarm1', 'alarm2', 'sensorFault',
		'sessionChange', 'networkChange', 'powerChange', 'batteryLow', 'systemOff', 'systemOn'])
	assert reply['data']['first'] == TEST_USER_FIRST
	assert reply['data']['last'] == TEST_USER_LAST
	assert reply['data']['username'] == TEST_USER_USERNAME
	assert reply['data']['email'] == TEST_USER_EMAIL
	assert reply['data']['password'] == TEST_USER_PASSWORD
	assert reply['data']['admin'] == TEST_USER_ADMIN
	assert reply['data']['alerts']['alarm1'] == TEST_USER_ALERTS_ALARM1
	assert reply['data']['alerts']['alarm2'] == TEST_USER_ALERTS_ALARM2
	assert reply['data']['alerts']['sensorFault'] == TEST_USER_ALERTS_SENSOR_FAULT
	assert reply['data']['alerts']['sessionChange'] == TEST_USER_ALERTS_SESSION_CHANGE
	assert reply['data']['alerts']['networkChange'] == TEST_USER_ALERTS_NETWORK_CHANGE
	assert reply['data']['alerts']['powerChange'] == TEST_USER_ALERTS_POWER_CHANGE
	assert reply['data']['alerts']['batteryLow'] == TEST_USER_ALERTS_BATTERY_LOW
	assert reply['data']['alerts']['systemOff'] == TEST_USER_ALERTS_SYSTEM_OFF
	assert reply['data']['alerts']['systemOn'] == TEST_USER_ALERTS_SYSTEM_ON
	assert False, "Fuck"

def load_test_environment(path):
	test_env = {}
	if os.path.exists(path):
		with open(path, 'r') as f:
			test_env = json.load(f)

	assert test_env != {}, 'No test environment provided'
	assert all(vars in test_env for vars in ['db_path']), 'Test environment missing variables'

	return test_env

@pytest.mark.unit
def test_base(env):

	# setup
	print('Environment path = {}'.format(env))
	test_env = load_test_environment(env)
	tnetdatabase.test_setup(db_path=test_env['db_path'])
	# run tests
	api_dev_info_get()
	api_dev_info_set()
	api_user_register()
	# teardown
	tnetdatabase.test_teardown()
