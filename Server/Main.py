# Modules
from DataTools import DataTools
from pathlib import Path
import logging
import time
import os

# Exceptions
from FileOps import SubprocessError
from YouTube import StatusCodeError
from urllib3.exceptions import NewConnectionError
from urllib3.contrib.pyopenssl import SocketError
from requests.exceptions import ConnectionError
from socket import gaierror


# Initialize the log File
logs_path = os.path.join(Path().absolute(), "logs")
Path(logs_path).mkdir(parents=True, exist_ok=True)
logs_file = os.path.join(logs_path, f"moist_meter.log", )

handler = logging.FileHandler(logs_file, 'a', 'utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s (%(levelname)s) --> %(message)s', datefmt='%m-%d-%y %H:%M:%S'))

logger = logging.getLogger("Log")
logger.addHandler(handler)

temp_file = open(logs_file, 'a')
temp_file.write("\n" + '-'*64 + "\n\n")
temp_file.close()
logger.setLevel(logging.DEBUG)
logger.info("Session Started. Welcome!")


# Handles Exceptions, Returns True for Fatal Errors
def handler(exception, logger):

	# Handle Interrupts
	if type(exception) == KeyboardInterrupt:
		logger.info("Interrupt Detected. Goodbye!")
		return True

	# Display Exception Traceback in Log File
	else:
		logger.exception("Exception: TYPE="+str(type(exception)))

	# Handle Specific Errors
	if type(exception) in {NewConnectionError, ConnectionError, gaierror, StatusCodeError, SocketError}:
		cooldown = 60
		logger.info("Exception Was Non-Fatal, Program Will Continue in " + str(cooldown) + " Seconds")
		time.sleep(cooldown)
		return False

	elif type(exception) == SubprocessError:
		logger.warning(exception.msg)
		return False

	else:
		return True


# Main Loop
data = DataTools()
running = True
while running:

	try:
		next_poll  = DataTools.poll(logger)
		next_audit = DataTools.audit(logger)

		logger.debug("Sleeping Until " + ("Next Poll" if next_poll < next_audit else "Next Audit") + " in " + str(round(max(min(next_poll, next_audit),0))) + " Seconds")
		time.sleep(max(min(next_poll, next_audit),0))

	except BaseException as err:
		running = not handler(err, logger)


logger.info("Session Ended")