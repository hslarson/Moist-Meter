import requests
import json
import os


class Pushover():
	
	# Loads Config Data
	def __init__(self):

		source_dir = os.path.dirname(os.path.realpath(__file__)) + '/'

		# Load the secrets file
		secrets_file = open(source_dir + 'secrets.json')
		if secrets_file.readable:
			secrets_obj = json.load(secrets_file)
			Pushover.token = secrets_obj["pushover"]["app_token"]
			Pushover.key = secrets_obj["pushover"]["user_key"]
			secrets_file.close()
		else:
			raise Exception("Failed to Read secrets.json")

		# Load the config file
		config_file = open(source_dir + 'config.json')
		if config_file.readable:
			config_obj = json.load(config_file)
			Pushover.enabled = config_obj["pushover_settings"]["allow_pushover_notifications"]
			config_file.close()
		else:
			raise Exception("Failed to Load config.json")


	# Sends a Pushover Notification
	def send_notification(msg , id=None):
		if not Pushover.enabled:
			return

		payload = {
			"token" : Pushover.token,
			"user" : Pushover.key,
			"message" : msg
		}

		if type(id) == str:
			payload["url"] = ("https://www.youtube.com/watch?v=" + id if "New Moist Meter:" not in msg else "https://www.moistmeter.org/form/")
			payload["url_title"] = ("Watch Video" if "New Moist Meter:" not in msg else "Go To Form")

		# Trying to fix notification error, got OSError("(104, 'ECONNRESET')
		# I don't think this is as efficient, could try using a queue and retrying send until it goes through
		requests.post("https://api.pushover.net/1/messages.json", params=payload)
		# YouTube.rqst.post("https://api.pushover.net/1/messages.json", params=payload)
