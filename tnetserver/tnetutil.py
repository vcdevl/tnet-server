import logging
from functools import wraps

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
