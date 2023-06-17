from YouTube import YouTube
from FileOps import FileOps
from Pushover import Pushover
import json
import time


class Worker():

	# Constructor
	def __init__(self):
		Worker.yt_obj = YouTube()
		Worker.file_ops = FileOps()
		Worker.pushover_obj = Pushover()

		# Clear Lingering Data Files
		FileOps.delete_file(".data.json")

		# Load the config file
		config_file = open(FileOps.SOURCE_DIR + 'config.json')
		if config_file.readable:
			config_obj = json.load(config_file)

			Worker.poll_settings = config_obj["poll_settings"]
			Worker.poll_settings["last_vid"] = Worker.poll_settings["last_poll"]
			Worker.audit_settings = config_obj["audit_settings"]

			config_file.close()
		else:
			raise Exception("Failed to Load config.json")


	# Gets YouTube Data and Checks for New Moist Meters
	# If Found, Add Entry to Data File
	def poll(logger, custom_start_time=-1):

		# Maintain the Desired Poll Frequency
		if custom_start_time < 0 and time.time() < Worker.poll_settings["last_poll"] + Worker.poll_settings["poll_frequency_seconds"]:
			return Worker.poll_settings["last_poll"] + Worker.poll_settings["poll_frequency_seconds"] - time.time()

		logger.debug("Polling")

		# Pull YouTube Data
		start = Worker.poll_settings["last_vid"]
		if custom_start_time >= 0:
			start = custom_start_time
			last_id = None

		uploads = YouTube.pull_uploads(start)
		logger.debug(uploads.__dict__)	
		if len(uploads):
			Worker.poll_settings["last_vid"] = uploads[0].date + 1

		moist_meters = YouTube.filter_moist_meters(uploads)

		# If a New Moist Meter is Found, Append It To the List
		if (len(moist_meters)):

			# Load the Data File and make sure it's sorted
			contents = FileOps.load_data()
			Worker.__sort(contents)

			# Iterate Over the New Moist Meters
			notifications = []
			for mm_obj in reversed(moist_meters):

				# Filter Duplicates
				known = False
				for obj in contents:
					if mm_obj == YouTube.Video.from_dict(obj):
						known = True
						break

				if not known:
					# Send "New Moist Meter" Notification
					notifications.append((mm_obj.short_title(), mm_obj.id))

					# Insert a New Object into the List
					for index in range(len(contents)+1):
						if index < len(contents) and mm_obj.date < contents[index]["date"]:
							continue

						video_obj = {
							"title" : mm_obj.title,
							"id" : mm_obj.id,
							"date" : mm_obj.date,
							"category" : "",
							"score" : "",
							"rated" : False
						}
						contents.insert(index, video_obj)
						break

			if len(notifications):

				# Send Pushover Notifications
				for title, id in notifications:
					logger.info("Found New Moist Meter: " + str(title))
					Pushover.send_notification(f"New Moist Meter: {title}", id)

				# Upload the File if Any Changes Were Made
				file = open(FileOps.SOURCE_DIR + ".data.json", 'w')
				if file.writable:
					json.dump(contents, file, indent='\t', separators=(',',' : '))
					file.close()
				else:
					raise Exception("Could Not Write to .data.json")

				notifications.clear()
				logger.info("Sending Updated Data to Server")
				FileOps.save_data(remove_local=False)

			FileOps.delete_file(".data.json")


		# Update last_poll last (this way if errors are encountered the poll will retry from the previous last_poll)
		if custom_start_time >= 0: return # Used by audit()
		Worker.poll_settings["last_poll"] = time.time()
		Worker.__save_config()
		return Worker.poll_settings["last_poll"] + Worker.poll_settings["poll_frequency_seconds"] - time.time()


	# Pulls the data file and makes sure everything is correct
	# (i.e. No Duplicates, Sorted New->Old, Valid Video ID's)
	def audit(logger):

		# Maintain the Desired Audit Frequency
		if time.time() < Worker.audit_settings["last_audit"] + Worker.audit_settings["audit_frequency_seconds"]:
			return Worker.audit_settings["last_audit"] + Worker.audit_settings["audit_frequency_seconds"] - time.time()
		else:
			Worker.audit_settings["last_audit"] = time.time()
			Worker.__save_config()

		logger.debug("Auditing")

		FIRST_MOIST_METER = 1490511599 # Timestamp of First Moist Meter
		altered = False
		notifications = []

		# Do a "Long Poll" to Check for Uncatalogued Moist Meters
		Worker.poll(logger, FIRST_MOIST_METER)

		# Load the Data File
		contents = FileOps.load_data()

		# Sort the List (Newest -> Oldest)
		if (Worker.__sort(contents)):
			logger.warning("List Was Out of Order")
			altered = True

		# Pull Uploads
		moist_meters = Worker.__filter_moist_meters(YouTube.pull_uploads(FIRST_MOIST_METER))

		# Iterate Over Uploads
		for index, data_obj in enumerate(contents):

			# Check For Duplicates in .data.json
			for i, o in enumerate(contents[index+1:]):
				if data_obj["id"] == o["id"]:
					logger.warning("Found Duplicate. Id=" + data_obj["id"] + ". Deleting...")
					notifications.append(("Found Duplicate. Id=" + data_obj["id"] + ". Deleting...", data_obj["id"]))
					del contents[index + i + 1]
					altered = True

			# Find the Video with Matching Upload Timestamp from Uploads
			for mm_obj in moist_meters:
				if mm_obj == YouTube.Video.from_dict(data_obj):

					# Correct Date
					if mm_obj.date != data_obj["date"]:
						logger.warning("Corrected Date For \"" + str(data_obj["title"]) + ".\" " + str(data_obj["date"]) + " -> " + str(mm_obj.date))
						contents[index]["date"] = mm_obj.date
						altered = True

					# Correct ID
					if mm_obj.id != data_obj["id"]:
						logger.warning("ID Changed for " + str(data_obj["title"]) + ": " + str(data_obj["id"]) + " -> " + str(mm_obj.id))
						notifications.append(("ID Changed for " + str(data_obj["title"]) + ": " + str(data_obj["id"]) + " -> " + str(mm_obj.id), mm_obj.id))
						contents[index]["id"] = mm_obj.id
						altered = True

					# Correct Title
					if mm_obj.title != data_obj["title"]:
						logger.warning("Title Changed for " + str(data_obj["title"]) + ". New Title: " + str(mm_obj.title))
						notifications.append(("Title Changed for " + str(data_obj["title"]) + ". New Title: " + str(mm_obj.title), mm_obj.id))
						contents[index]["title"] = mm_obj.title
						altered = True

					break
			else:
				logger.warning(f"Found No Matching Video for {data_obj['title']}")
				notifications.append((f"Found No Matching Video for {data_obj['title']}", data_obj["id"]))

		if altered:

			# Upload the File if Any Changes Were Made
			file = open(FileOps.SOURCE_DIR + ".data.json", 'w')
			if file.writable:
				json.dump(contents, file, indent='\t', separators=(',',' : '))
				file.close()
			else:
				raise Exception("Could Not Write to .data.json")

			logger.info("Sending Updated Data to Server")
			FileOps.save_data()

		# Send Notifications
		for msg, id in notifications:
			Pushover.send_notification(msg, id)
		else:
			notifications.clear()

		# Back Up the Data File
		logger.debug("Backing Up Data File")
		FileOps.back_up_data()

		return Worker.audit_settings["last_audit"] + Worker.audit_settings["audit_frequency_seconds"] - time.time()


	# Updates last_poll and last_audit Fields in config.json
	def __save_config():

		# Read the Config File
		file = open(FileOps.SOURCE_DIR + 'config.json', 'r')
		if file.readable:
			contents = json.load(file)
			file.close()
		else:
			raise Exception("config.json Could Not be Read")

		# Alter the last poll/audit variables
		contents["poll_settings"]["last_poll"] = Worker.poll_settings["last_poll"]
		contents["audit_settings"]["last_audit"] = Worker.audit_settings["last_audit"]

		# Replace the Contents of the Config File
		file = open(FileOps.SOURCE_DIR + 'config.json', 'w')
		if file.writable:
			json.dump(contents, file, indent='\t', separators=(',',' : '))
			file.close()
		else:
			raise Exception("config.json Could Not be Written To")


	# Perform a simple selection sort
	# Post Condition: Objects ordered from newest to oldest
	def __sort(contents):

		lindex = 0
		altered = False
		end = len(contents)
		while (lindex < end):

			# Search for highest date
			highest_date  = contents[lindex]["date"]
			highest_index = lindex
			rindex = lindex + 1
			while (rindex < end):
				if (contents[rindex]["date"] > highest_date):
					highest_date = contents[rindex]["date"]
					highest_index = rindex
					altered = True

				rindex += 1

			# Swap elements if necessary
			temp = contents[highest_index]
			contents[highest_index] = contents[lindex]
			contents[lindex] = temp
			lindex += 1

		return altered
