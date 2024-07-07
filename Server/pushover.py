"""Wrapper for the Pushover push notification API"""

import requests
import logging


class Pushover():
	"""Wrapper for the Pushover push notification API"""

	# Static members
	_logger = None
	_enabled = None
	_token = None
	_key = None

	@staticmethod
	def begin(config, secrets):
		"""
		Initialize the module
		
		Parameters:
		- config (dict): Dictionary of config information
		- secrets (dict): Dictionary of secret information
		"""
		
		# Configure logger
		Pushover._logger = logging.getLogger(__name__)
		Pushover._logger.setLevel(logging.DEBUG)

		# Check if Pushover is enabled
		try:
			Pushover._enabled = config["allow_pushover_notifications"]
			Pushover._logger.info("Pushover " + ("enabled" if Pushover._enabled else "disabled"))
			if not Pushover._enabled: 
				return
		except KeyError:
			Pushover._logger.error("config.json missing info")
			raise

		# Load the Pushover API token and user key
		try:
			Pushover._token = secrets["pushover"]["app_token"]
			Pushover._key   = secrets["pushover"]["user_key"]
		except KeyError:
			Pushover._logger.error("secrets.json missing info")
			raise


	@staticmethod
	def send_notification(msg, id=None):
		"""
		Sends a Pushover notification

		Parameters:
		- msg (str): The message text to send
		- id (str | None): The video ID associated with the message. This gets converted to a URL.
		"""
		# Check if Pushover notifications are enabled
		# Always returns if begin() hasn't been called
		if not Pushover._enabled:
			return

		# Construct payload
		payload = {
			"token" : Pushover._token,
			"user" : Pushover._key,
			"message" : msg
		}

		# Add URL to payload
		if isinstance(id, str):
			# For new Moist Meters, provide a link to the rating form
			if "New Moist Meter:" in msg:
				payload["url"] = "https://www.moistmeter.org/form/"
				payload["url_title"] = "Go To Form"
			
			# Otherwise, just link the video
			else:
				payload["url"] = f"https://www.youtube.com/watch?v={id}"
				payload["url_title"] = "Watch Video" 

		# Send notification
		try:
			Pushover._logger.debug(f"Sending Pushover notification: {payload}")
			response = requests.post("https://api.pushover.net/1/messages.json", params=payload)
			# TODO: Check response?
		except:
			Pushover._logger.error("Notification failed to send")
			raise
		else: 
			Pushover._logger.debug(f"Notification sent. Response={response}")
