import logging
import sys
import os
import json
from functools import wraps

from tnetserver import tnetconfig

tnetdb = {'user':[], 'device':{}}

def db_valid(func):

	@wraps(func)
	def decorator(*args, **kwargs):
		global tnetdb
		config = tnetconfig.get_config()

		if not os.path.exists(config['database']['path'])
			open(config['database']['path'], 'w').close()
		else:
			data = {}
			try:
				with open(config['database']['path'], 'r') as f:
					data = json.load(f)
			except Exception as e:
				logging.error(e)

			if 'user' in data:
				tnetdb['user'] = data['user']

			if 'device' in data:
				tnetdb['device'] = data['device']

		return func(*args, **kwargs)
	return decorator

def db_save(func):

	@wraps(func)
	def decorator(*args, **kwargs):
		global tnetdb
		config = tnetconfig.get_config()

		if func(*args, **kwargs):
			with open(config['database']['path'], 'w') as f:
				json.dump(tnetdb, f)

	return decorator

@db_valid
@db_save
def insert_user(user):
	global tnetdb
	collection = tnetdb['user']
	if collection:
		for u in collection:
			if user['email'] == u['email']:
				return False

	collection.append(user)
	logging.debug("User with email={} created".format(user["email"]))
	return True

@db_valid
@db_save
def edit_user(user):
	global tnetdb
	collection = tnetdb['user']
	user_edited = False
	if collection:
		for u in collection:
			if user['email'] == u['email']:
				u['password'] = user['password']
				u['settings'] = user['settings']
				u['first'] = user['first']
				u['last'] = user['last']
				logging.debug('Edited user first={} last={}'.format(user['first'], user['last']))
				user_edited = True

	return user_edited

@db_valid
@db_save
def delete_user(user_id):
	global tnetdb
	collection = tnetdb['user']
	user_removed = False
	if collection:
		for u in collection:
			if user['email'] == u['email']:
				removed_user = collection.pop(collection.index(u))
				logging.debug('Removed user first={} last={}'.format(removed_user['first'], removed_user['last']))
				user_removed = True

	return user_removed

@db_valid
def count_users():
	global tnetdb
	collection = tnetdb['user']
	count = 0
	for u in collection:
		count += 1
	return count

@db_valid
def get_user(username=None):
	global tnetdb
	collection = tnetdb['user']
	all_users = []
	if username is None:
		for u in collection:
			all_users.append(u)
	else:
		if collection:
			for u in collection:
				if u['email'] == username:
					all_users.append(u)

	return all_users
