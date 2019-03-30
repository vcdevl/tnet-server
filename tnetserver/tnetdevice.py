import logging

from tnetserver import tnetdatabase, tnetutil

def get_info():
	''' get info for device '''

	dev_info = tnetdatabase.get_devinfo()
	return {'success':True, 'data':dev_info, 'error':''}

@tnetutil.validate_payload(['name', 'description'])
def update_info(payload):
	''' update device info '''

	reply = {'success': False, 'data':{}, 'error':''}

	if tnetdatabase.set_devinfo(payload['name'], payload['description']):
		logging.info('Device info changed to name={} description={}'.format(payload['name'], payload['description']))
		reply['success'] = True
		reply['data'] = {'name':payload['name'], 'description':payload['description']}
	else:
		logging.warning(reply['error'])

	return reply
