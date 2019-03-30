import logging
import sys
import os
import json
import copy
from functools import wraps

DB_PATH = '/home/tgard'



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


db = {'devinfo': {'path': '{}/db/devinfo.json', 'collection': devinfo_collection},
		'user': {'path': '{}/db/user.json', 'collection': user_collection},
		'ham': {'path': '{}/db/ham.json', 'collection': hamachi_collection},
		'email':{'path': '{}/db/email.json', 'collection': email_collection},
		'session':{'path': '{}/db/session.json', 'collection': session_collection}}

def db_load(collection, update=False):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			global db
			global DB_PATH

			db_path = db[collection]['path'].format(DB_PATH)

			# create file if not exist and dump the default
			if not os.path.exists(db_path):
				try:
					# json list quirk, if list then create a dictionary with the key being the name of the collection
					db_collection = copy.copy(db[collection]['collection'])
					if type(db_collection) is list:
						db_collection = {collection: db_collection}

					with open(db_path, 'w') as f:
						json.dump(db_collection, f)

				except Exception as e:
					logging.error(e)

			# else read from file and update the db collection
			else:
				db_collection = {}
				try:

					with open(db_path, 'r') as f:
						db_collection = json.load(f)

					# json list quirk, if dictionary with key being the collection name and the value is a list, then create list
					if collection in db_collection and type(db_collection[collection]) is list:
						db_collection = db_collection[collection]

					# update if not empty
					if db_collection:
						db[collection]['collection'] = db_collection

				except Exception as e:
					logging.error(e)

			# call decorated function
			result = func(*args, **kwargs)

			# now dump back to file if result and update both True
			if result == True and update:
				try:
					# json list quirk, if list then create a dictionary with the key being the name of the collection
					db_collection = copy.copy(db[collection]['collection'])
					if type(db_collection) is list:
						db_collection = {collection: db_collection}

					with open(db_path, 'w') as f:
						json.dump(db_collection, f)
				except Exception as e:
					logging.error(e)

			return result

		return wrapper
	return decorator

@db_load(collection='user', update=True)
def insert_user(user):
	global db
	if db['user']['collection']:
		for u in db['user']['collection']:
			if user['email'] == u['email']:
				return False

	db['user']['collection'].append(user)
	return True

@db_load(collection='user', update=True)
def edit_user(user):
	global db
	user_edited = False
	if db['user']['collection']:
		for u in db['user']['collection']:
			if user['email'] == u['email']:
				u['password'] = user['password']
				u['settings'] = user['settings']
				u['first'] = user['first']
				u['last'] = user['last']
				user_edited = True

	return user_edited

@db_load(collection='user', update=True)
def delete_user(user_id):
	global db
	user_removed = False
	if db['user']['collection']:
		for u in db['user']['collection']:
			if user['email'] == u['email']:
				removed_user = db['user']['collection'].pop(db['user']['collection'].index(u))
				user_removed = True

	return user_removed

@db_load(collection='user')
def count_users():
	global db
	count = 0
	if db['user']['collection']:
		for u in db['user']['collection']:
			count += 1

	return count

@db_load(collection='user')
def get_user(username=None):
	global db
	all_users = []
	if username is None:
		if db['user']['collection']:
			for u in db['user']['collection']:
				all_users.append(u)
	else:
		if db['user']['collection']:
			for u in db['user']['collection']:
				if u['email'] == username:
					all_users.append(u)

	return copy.copy(all_users)


@db_load(collection='devinfo')
def get_devinfo(field=None):
	global db

	if field is None:
		return copy.copy(db['devinfo']['collection'])
	else:
		if db['devinfo']['collection']:
			if field in db['devinfo']['collection']:
				return copy.copy(db['devinfo']['collection'][field])

	return None

@db_load(collection='devinfo', update=True)
def set_devinfo(name, description):
	global db
	if db['devinfo']['collection']:
		db['devinfo']['collection']['name'] = name
		db['devinfo']['collection']['description'] = description
		return True

	return False

db_load(collection='session')
def get_session(id=None):
	global db
	all_sessions = []
	if id is None:
		if db['session']['collection']:
			for s in db['session']['collection']:
				all_sessions.append(s)
	else:
		if db['session']['collection']:
			for s in db['session']['collection']:
				if s['id'] == id:
					all_sessions.append(s)

	return copy.copy(all_sessions)



def test_setup(db_path, clean=False):
	global DB_PATH
	global db
	DB_PATH = db_path
	print('Db path = {}'.format(DB_PATH))

	# remove all files
	if clean:
		for collection in db.keys():
			if os.path.exists(db[collection]['path'].format(DB_PATH)):
				os.remove(db[collection]['path'].format(DB_PATH))

def test_teardown(clean=False):
	if clean:
		global DB_PATH
		global db

		for collection in db.keys():
			if os.path.exists(db[collection]['path'].format(DB_PATH)):
				os.remove(db[collection]['path'].format(DB_PATH))
