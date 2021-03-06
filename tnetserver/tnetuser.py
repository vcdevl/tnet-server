import logging
import json
import os
import time
from functools import wraps

from tnetserver import tnetdatabase, tnetutil


def verify_user(f):
	@wraps(f)
	def decorator(*args, **kwargs):

		payload = args[0]

		all_users = tnetdatabase.get_user()
		for user in all_users:
			if payload['username'] == user['username']:
				if payload['password'] == user['password']:
					return f(*args, **kwargs)
				else:
					logging.debug('Invalid password')
					return {'success': False, 'data':{}, 'error':'Invalid password'}

		logging.debug('User does not exist')
		return {'success':False, 'data':{}, 'error':'User does not exist'}

	return decorator

def validate_payload(keys=[]):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			payload = args[0]

			for key in keys:
				if key not in payload:
					error_str = 'Payload missing key {}'.format(key)
					logging.warning(error_str)
					return {'success': False, 'data':{}, 'error':error_str}

			return func(*args, **kwargs)
		return wrapper
	return decorator

@tnetutil.validate_payload(keys=['first', 'last', 'email', 'password', 'username', 'alerts'])
def register(payload):
	''' register an admin user (one time request during device provisioning)
		users can be added via the add() method '''

	reply = {'success': False, 'data': {}, 'error': ''}

	if not all(alert_fields in payload['alerts'] for alert_fields in ['alarm1', 'alarm2', 'sensorFault',
		'sessionChange', 'networkChange', 'powerChange', 'batteryLow', 'systemOff', 'systemOn']):
		reply['error'] = 'Missing alert fields'
		logging.warning(reply['error'])
		return reply

	# first get all users
	this_user = tnetdatabase.get_user(payload['email'])

	this_user_total = len(this_user)

	if this_user_total > 1:
		reply['error'] = 'Multiple users with same username {} registered'.format(payload['email'])

	elif this_user_total == 1:
		reply['error'] = 'User with email {} already registered'.format(payload['email'])

	elif this_user_total == 0:

		new_user = {
			'first': payload['first'],
			'last': payload['last'],
			'email': payload['email'],
			'username': payload['username'],
			'password': payload['password'],
			'admin': True,
			'alerts':payload['alerts']
		}

		# do the database insert
		if tnetdatabase.insert_user(new_user):
			logging.debug("User with email={} created".format(new_user["email"]))
			reply['data'] = new_user
			reply['success'] = True
		else:
			reply['error'] = 'Failed to create user'

	if not reply['success']:
		logging.warning(reply['error'])
	return reply


def get(payload):
	''' get all users '''

	reply = {'success': False, 'data': [], 'error': ''}

	# get users which returns list
	users = tnetdatabase.get_user()
	logging.debug('Get user result = {}'.format(users))

	for user in users:
		if all(x in user for x in ['first', 'last', 'username', 'email', 'password', 'admin', 'alerts']):
			reply['data'].append(user)
		else:
			logging.warning('User missing some fields')

	reply['success'] = True
	return reply


@tnetutil.validate_payload(keys=['first', 'last', 'username', 'password', 'alerts'])
def edit(payload):
	''' edit a user '''

	reply = {'success': False, 'data': {}, 'error': ''}

	if tnetdatabase.edit_user():
		logging.debug('Edited user first={} last={}'.format(payload['first'], payload['last']))
		reply['success'] = True
	else:
		reply['error'] = 'Failed to edit user'
		logging.warning(reply['error'])

	return reply


"""@validate_payload(keys=['username', 'password', 'deviceId'])
def login(payload):
	reply = {
		'success': False,
		'data': {},
		'error': ''
	}

	# get users which returns list
	user = tnetdatabase.get_user(payload['username'])
	logging.debug('Get user result = {}'.format(user))
	if len(user) == 0:
		reply['error'] = 'User does not exist'

	elif user[0]['email'] == payload['username']:

		# hash password
		hashed = binascii.hexlify(hashlib.pbkdf2_hmac('sha256', payload['password'].encode('utf-8'), user[0]['salt'].encode('utf-8'), 10000)).decode('utf-8')
		if hashed == user[0]['password']:
			reply['data'] = {
				'id': user[0]['id'],
				'firstName': user[0]['firstName'],
				'lastName': user[0]['lastName'],
				'isAdmin': user[0]['isAdmin'],
				'token': user[0]['token'],
				'settings': user[0]['settings'],
				'deviceId': user[0]['deviceId']
			}
			reply['success'] = True
		else:
			reply['error'] = 'Incorrect password'

	else:
		reply['error'] = 'Unable to validate user'

	logging.info(reply['error'])
	return reply





@validate_payload(keys=['userId', 'token'])
@verify_token
def add(payload):
	return { 'success': False,  'data': {}, 'error': 'Not implemented yet'}

@validate_payload(keys=['userId', 'token'])
@verify_token
def delete(payload):
	reply = {
		'success': False,
		'data': {},
		'error': ''
	}
	logging.debug('Removed user first={} last={}'.format(removed_user['first'], removed_user['last']))
	# can't delete the primary user i.e. user with Id = 1
	if payload['userId'] == 1:
		reply['error'] = 'Not permissible to delete user with Id=1'
	else:

		# get user info to return in data field of payload
		all_users = tnetdatabase.get_user()
		user_to_delete = {}
		found_user = False
		for u in all_users:
			if payload['userId'] == u['id']:
				found_user = True
				user_to_delete = u

		if not found_user:
			reply['error'] = 'User with id={} does not exist'.format(payload['userId'])

		else:

			# delete
			tnetdatabase.delete_user(payload['userId'])

			time.sleep(2)

			all_users = tnetdatabase.get_user()
			confirm_user = False
			for u in all_users:
				if payload['userId'] == u['id']:
					confirm_user = True

			if confirm_user:
				reply['error'] = 'Unable to delete user'
			else:
				reply['data'] = [{'id': -1, 'firstName': '', 'lastName': '', 'isAdmin': False}]
				if 'id' in user_to_delete:
					reply['data'][0]['id'] = user_to_delete['id']
				if 'firstName' in user_to_delete:
					reply['data'][0]['firstName'] = user_to_delete['firstName']
				if 'lastName' in user_to_delete:
					reply['data'][0]['lastName'] = user_to_delete['lastName']
				if 'isAdmin' in user_to_delete:
					reply['data'][0]['isAdmin'] = user_to_delete['isAdmin']
				reply['success'] = True

	logging.info(reply['error'])
	return reply
"""
