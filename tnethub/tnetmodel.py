''' Model for all components to run in thread '''

import threading
import logging

class Model(object):
	''' Base model for all tempnetz system handlers '''

	def __init__(self, name):
		self.name = name
		self.stopThread = False
		self.thread = None

	def start(self):
		''' start thread and call run() '''
		self.stopThread = False
		logging.debug('{}: Starting new thread.'.format(self.name))
		self.thread = threading.Thread(target=self.run, args=(), name=self.name)
		self.thread.daemon = True
		self.thread.start()

	def stop(self):
		''' stop thread '''

		self.stopThread = True
		logging.debug('{}: Stopping thread.'.format(self.name))
		if self.thread is not None:
			if self.thread.is_alive():
				self.thread.join()
