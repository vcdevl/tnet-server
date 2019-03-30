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

	if tnetdatabase.update_info(name, description):
		logging.info('Device info changed to name={} description={}'.format(name, description))
		reply['success'] = True
		reply['data'] = {'name':name, 'description':description}
	else:
		logging.warning(reply['error'])

	return reply
