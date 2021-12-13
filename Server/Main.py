from DataTools import DataTools
from pathlib import Path
import logging
import time
import os


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
logger.setLevel(logging.INFO)
logger.info("Session Started. Welcome!")


# Kill the program if more than 10 errors are encountered in 15 minutes
errors = []
def error_counter():
	global errors
	RETRIES = 10
	WINDOW  = 15 #minutes
	
	errors.append(time.time())
	while len(errors) > RETRIES: errors.pop(0)

	t_cutoff = time.time() - (WINDOW*60)
	fail = (len(errors) == RETRIES) and (min(errors) > t_cutoff)
	
	if fail: logger.error("Too Many Errors Occured, Exiting...")
	return (not fail)


# Main Loop
data = DataTools()
running = True
while running:

	try:
		next_poll  = DataTools.poll(logger)
		next_audit = DataTools.audit(logger)

		logger.info("Sleeping Until " + ("Next Poll" if next_poll < next_audit else "Next Audit") + " in " + str(round(max(min(next_poll, next_audit),0))) + " Seconds")
		time.sleep(max(min(next_poll, next_audit),0))
	
	except KeyboardInterrupt:
		logger.info("Interrupt Detected. Goodbye!")
		running = False
		continue
	except:
		logger.exception("Exception: ")
		time.sleep(60)
		running = error_counter()
		continue


logger.info("Session Ended")