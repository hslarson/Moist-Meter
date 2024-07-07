# Modules
from cloudflare import CloudFlare
from pushover import Pushover
from youtube import YouTube
from worker import Worker
from pathlib import Path
from s3 import S3
import logging
import time
import json
import os

# Exceptions
from youtube import StatusCodeError
from urllib3.exceptions import NewConnectionError
from urllib3.contrib.pyopenssl import SocketError
from requests.exceptions import ConnectionError
from socket import gaierror

allowed_exceptions = {
	NewConnectionError, 
	ConnectionError, 
	gaierror, 
	StatusCodeError, 
	SocketError
}


# Initialize the log File
logs_path = os.path.join(Path().absolute(), "logs")
Path(logs_path).mkdir(parents=True, exist_ok=True)
logs_file = os.path.join(logs_path, "moist_meter.log")

handler = logging.FileHandler(logs_file, 'a', 'utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s (%(name)s:%(levelname)s) --> %(message)s', datefmt='%m-%d-%y %H:%M:%S'))

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

with open(logs_file, 'a') as file:
	file.write("\n" + '-'*64 + "\n\n")
logger.info("Session Started. Welcome!")


def handler(exception, logger):
	"""Handles exceptions, returns True for fatal errors"""
	
	# Handle interrupts
	if type(exception) == KeyboardInterrupt:
		logger.info("Interrupt Detected. Goodbye!")
		return True

	# Display exception traceback in log file
	logger.exception("Exception: TYPE="+str(type(exception)))

	# Handle Specific Errors
	if type(exception) in allowed_exceptions:
		cooldown = 60
		logger.info("Exception Was Non-Fatal, Program Will Continue in " + str(cooldown) + " Seconds")
		time.sleep(cooldown)
		return False

	return True


module_dir = os.path.dirname(os.path.realpath(__file__))

# Read config file
logger.debug("Reading config file...")
with open(os.path.join(module_dir, "config.json"), "r") as file:
	config = json.load(file)
	logger.debug("Config file read successfully")

# Read secrets file
logger.debug("Reading secrets file...")
with open(os.path.join(module_dir, "secrets.json"), "r") as file:
	secrets = json.load(file)
	logger.debug("Secrets file read successfully")

# Initialize static classes
Pushover.begin(config, secrets)
S3.begin(config, secrets)
CloudFlare.begin(secrets)
YouTube.begin(secrets)
Worker.begin(config)


# Main Loop
running = True
while running:
	try:
		next_poll  = Worker.poll()
		next_audit = Worker.audit()

		logger.debug("Sleeping Until " + ("Next Poll" if next_poll < next_audit else "Next Audit") + " in " + str(round(max(min(next_poll, next_audit),0))) + " Seconds")
		time.sleep(max(min(next_poll, next_audit), 0))

	except BaseException as err:
		running = not handler(err, logger)

logger.info("Session Ended")
