import logging
import sys
import os
import json
import copy
from functools import wraps

DEVINFO_FILE = '/home/tgard/db/devinfo.json'
USER_FILE = '/home/tgard/db/user.json'
HAM_FILE = '/home/tgard/db/ham.json'
EMAIL_FILE = '/home/tgard/db/email.json'
SESSION_FILE = '/home/tgard/db/session.json'

user_collection = []
devinfo_collection = {
	'id': '',
	'name': '',
	'description':'',
	'hardware_version': '',
	'manufacture_date': '',
	'provision_date': '',
	'software_version': {'libcomm': '','libchart': '','appgui': '','server': ''},
	'timezone':'',
	'locale':''}
hamachi_collection = {'client_id':'', 'ipv4_address':'', 'network_id':''}
email_collection = {'url':'', 'port': -1, 'user':'', 'pass':''}
connectivity_collection = {'preferred_interface':'', 'single_connection':False}
cell3g_collection = {'number':'', 'imei': '', 'puk':'', 'provider':'', 'pin': '', 'apn':'', 'enable': False}
system_settings_collection = {}
av_settings_collection = {}

"""sensor = {'pos':0, 'id':'', 'name':'', 'a1':0, 'a2':0, 'diffmode':0, 'a1trig': False, 'a2trig': False, 'temp':0, 'alarm_status':0, 'fault': False}
session {
	'id':'',
	'name':'',
	'start_date':'',
	'end_date':'',
	'total_sensors':'',
	'global_alarm_status':'',
	'alarm_interpretation': '',
	'log_interval': 0,
	'sensors': []}"""
session_collection = []


def db_load(collection, path, update=False):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):

			try:
				# create file if not exist
				if not os.path.exists(path):
					with open(path, 'w') as f:
						json.dump(collection, f)
				else:
					with open(path, 'r') as f:
						collection = json.load(f)
			except Exception as e:
				logging.error(e)

			if func(*args, **kwargs) and update:
				with open(path, 'w') as f:
					json.dump(collection, f)

		return wrapper
	return decorator

@db_load(collection=user_collection, path=USER_FILE, update=True)
def insert_user(user):
	global user_collection
	if user_collection:
		for u in user_collection:
			if user['email'] == u['email']:
				return False

	user_collection.append(user)
	return True

@db_load(collection=user_collection, path=USER_FILE, update=True)
def edit_user(user):
	global user_collection
	user_edited = False
	if user_collection:
		for u in user_collection:
			if user['email'] == u['email']:
				u['password'] = user['password']
				u['settings'] = user['settings']
				u['first'] = user['first']
				u['last'] = user['last']
				user_edited = True

	return user_edited

@db_load(collection=user_collection, path=USER_FILE, update=True)
def delete_user(user_id):
	global user_collection
	user_removed = False
	if user_collection:
		for u in user_collection:
			if user['email'] == u['email']:
				removed_user = user_collection.pop(user_collection.index(u))
				user_removed = True

	return user_removed

@db_load(collection=user_collection, path=USER_FILE)
def count_users():
	global user_collection
	count = 0
	for u in user_collection:
		count += 1

	return count

@db_load(collection=user_collection, path=USER_FILE)
def get_user(username=None):
	global user_collection
	all_users = []
	if username is None:
		for u in user_collection:
			all_users.append(u)
	else:
		if user_collection:
			for u in user_collection:
				if u['email'] == username:
					all_users.append(u)

	return copy.copy(all_users)




db_load(collection=session_collection, path=SESSION_FILE)
def get_session(id=None)
	global session_collection
	all_sessions = []
	if id is None:
		for s in session_collection:
			all_sessions.append(s)
	else:
		if session_collection:
			for s in session_collection:
				if s['id'] == id:
					all_sessions.append(s)

	return copy.copy(all_sessions)
