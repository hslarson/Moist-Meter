"""Main worker that handles polling and auditing"""

from pushover import Pushover
from youtube import *
from s3 import S3
import logging
import json
import time
import os


class Worker():
	"""Main worker that handles polling and auditing"""

	# Static members
	_logger = None
	_last_modified = None
	_poll_settings = None
	_audit_settings = None


	def begin(config):
		"""
		Initialize the module
		
		Parameters:
		- config (dict): Dictionary of config information
		"""

		# Configure logging
		Worker._logger = logging.getLogger(__name__)
		Worker._logger.setLevel(logging.DEBUG)

		# Read from config file
		try:
			Worker._last_modified = config["data_last_modified"]
			Worker._poll_settings = config["poll_settings"]
			Worker._poll_settings["last_vid"] = Worker._poll_settings["last_poll"]
			Worker._audit_settings = config["audit_settings"]
		except KeyError:
			Worker._logger.error("config.json missing info")
			raise


	@staticmethod
	def poll(custom_start_time=-1):
		"""
		Gets YouTube Data and Checks for New Moist Meters\n
		If Found, Add Entry to Data File
		"""

		# Maintain the desired poll frequency
		if custom_start_time < 0 and time.time() < Worker._poll_settings["last_poll"] + Worker._poll_settings["poll_frequency_seconds"]:
			return Worker._poll_settings["last_poll"] + Worker._poll_settings["poll_frequency_seconds"] - time.time()

		Worker._logger.debug("Polling")

		# Pull YouTube Data
		start = Worker._poll_settings["last_vid"]
		if custom_start_time >= 0:
			start = custom_start_time

		uploads = YouTube.pull_uploads(start)
		if len(uploads):
			Worker._poll_settings["last_vid"] = uploads[0].date + 1
		
		moist_meters = [vid for vid in uploads if vid.is_moist_meter()]

		# Load the data file and make sure it's sorted
		contents = S3.list_data()
		contents.sort(key=lambda v: v["date"], reverse=True)

		# Check modified time and update minified file if needed
		remote_last_modified = int(os.path.getmtime(os.path.join(S3.module_dir, S3.data_file_name)))
		if remote_last_modified > Worker._last_modified:
			Worker._logger.info("Remote file was modified, updating minified data file")
			Worker._optimize_json(contents)
			S3.put_data(S3.min_file_name)

		# If a new Moist Meter is found, append it to the list
		if len(moist_meters):
			Worker._handle_moist_meters(moist_meters, contents)

		# Update last_poll last 
		# This way if errors are encountered the poll will retry from the previous last_poll
		if custom_start_time >= 0: return # Used by audit()
		Worker._poll_settings["last_poll"] = time.time()
		Worker._save_config()
		return Worker._poll_settings["last_poll"] + Worker._poll_settings["poll_frequency_seconds"] - time.time()


	@staticmethod
	def audit():
		"""
		Pulls the data file and makes sure everything is correct 
		(i.e. No Duplicates, Sorted New->Old, Valid Video IDs)
		"""
		# Maintain the Desired Audit Frequency
		if time.time() < Worker._audit_settings["last_audit"] + Worker._audit_settings["audit_frequency_seconds"]:
			return Worker._audit_settings["last_audit"] + Worker._audit_settings["audit_frequency_seconds"] - time.time()
		else:
			Worker._audit_settings["last_audit"] = time.time()
			Worker._save_config()

		Worker._logger.debug("Auditing")

		FIRST_MOIST_METER = 1490511599 # Timestamp of First Moist Meter
		altered = False
		notifications = []

		# Do a "long poll" to check for uncatalogued Moist Meters
		Worker.poll(FIRST_MOIST_METER)

		# Load the data file
		contents = S3.list_data()

		# Sort the list (newest -> oldest)
		sorted_contents = sorted(contents, key=lambda v: v["date"], reverse=True)
		if (contents != sorted_contents):
			Worker._logger.warning("List Was Out of Order")
			altered = True
		contents = sorted_contents

		# Pull uploads
		uploads = YouTube.pull_uploads(FIRST_MOIST_METER)
		moist_meters = [vid for vid in uploads if vid.is_moist_meter()]

		# Iterate over uploads
		for index, data_obj in enumerate(contents):
			# Check for duplicates in .data.json
			for i, o in enumerate(contents[index+1:]):
				if data_obj["id"] == o["id"]:
					Worker._logger.warning("Found Duplicate. Id=" + data_obj["id"] + ". Deleting...")
					notifications.append(("Found Duplicate. Id=" + data_obj["id"] + ". Deleting...", data_obj["id"]))
					del contents[index + i + 1]
					altered = True

			# Find the video with matching upload timestamp from uploads
			for mm_obj in moist_meters:
				if mm_obj == Video.from_dict(data_obj):
					# Correct date
					if mm_obj.date != data_obj["date"]:
						Worker._logger.warning("Corrected Date For \"" + str(data_obj["title"]) + ".\" " + str(data_obj["date"]) + " -> " + str(mm_obj.date))
						contents[index]["date"] = mm_obj.date
						altered = True

					# Correct ID
					if mm_obj.id != data_obj["id"]:
						Worker._logger.warning("ID Changed for " + str(data_obj["title"]) + ": " + str(data_obj["id"]) + " -> " + str(mm_obj.id))
						notifications.append(("ID Changed for " + str(data_obj["title"]) + ": " + str(data_obj["id"]) + " -> " + str(mm_obj.id), mm_obj.id))
						contents[index]["id"] = mm_obj.id
						altered = True

					# Correct title
					if mm_obj.title != data_obj["title"]:
						Worker._logger.warning("Title Changed for " + str(data_obj["title"]) + ". New Title: " + str(mm_obj.title))
						notifications.append(("Title Changed for " + str(data_obj["title"]) + ". New Title: " + str(mm_obj.title), mm_obj.id))
						contents[index]["title"] = mm_obj.title
						altered = True
					break
			else:
				if ("removed" not in Worker._audit_settings) or (data_obj["id"] not in Worker._audit_settings["removed"]):
					Worker._logger.warning(f"Found No Matching Video for {data_obj['title']}")
					notifications.append((f"Found No Matching Video for {data_obj['title']}", data_obj["id"]))

		if altered:
			# Update the file if any changes were made
			try:
				filepath = os.path.join(S3.module_dir, S3.data_file_name)
				with open(filepath, 'w') as file:
					json.dump(contents, file, indent='\t', separators=(',',' : '))
				S3.put_data(S3.data_file_name)
				Worker._last_modified = int(os.path.getmtime(filepath))
			except:
				Worker._logger.error("Failed to update data file")
				raise

		# Send Notifications
		for msg, id in notifications:
			Pushover.send_notification(msg, id)
		else:
			notifications.clear()

		return Worker._audit_settings["last_audit"] + Worker._audit_settings["audit_frequency_seconds"] - time.time()


	@staticmethod
	def _save_config():
		"""Updates last_poll and last_audit fields in config.json"""

		# Read the config file
		try:
			Worker._logger.debug("Reading config file...")
			with open(os.path.join(S3.module_dir, "config.json"), "r") as file:
				contents = json.load(file)
			Worker._logger.debug("Config file read successfully")
		except:
			Worker._logger.error("Could not read config.json")
			raise

		# Alter the last poll/audit variables
		contents["data_last_modified"] = Worker._last_modified
		contents["poll_settings"]["last_poll"]   = Worker._poll_settings["last_poll"]
		contents["audit_settings"]["last_audit"] = Worker._audit_settings["last_audit"]

		# Replace the contents of the config file
		try:
			Worker._logger.debug("Writing to config file...")
			with open(os.path.join(S3.module_dir, "config.json"), "w") as file:
				json.dump(contents, file, indent='\t', separators=(',',' : '))
			Worker._logger.debug("Config file written successfully")
		except:
			Worker._logger.error("Could not write config.json")
			raise
	

	@staticmethod
	def _optimize_json(contents):
		"""
		Converts the regular data file into a minified version that the website can parse easily
		
		Parameters:
		- contents (list): The list of video dicts read from the regular data file
		"""
		min_data = []
		
		for idx, obj in enumerate(contents):
			# Skip unrated videos
			if not obj["rated"]: continue

			# Construct the score string
			# - 3 numeric characters for score. 000 if score has alpha characters
			# - ? characters for text. Usually "N/A" if anything
			# - 3 separator characters: %%%
			# - 2 numeric characters for sorting awards 
			# 	- 01-09 -> "Worst of..."
			# 	- 10    -> No award
			# 	- 11-19 -> "Best of..."
			# - ? characters of award text. Will be displayed in tooltip
			score_str = str(obj["score"])
			if score_str.isdecimal():
				score_str = score_str.zfill(3)
			else:
				score_str = f"000{score_str}"
			score_str += "%%%"

			# Add award indicator to score string
			if "award" in obj:
				award = str(obj["award"]).lower()

				# Determine award type
				best = ("best" in award)
				score_str +=  "1" if best else "0"

				# Add priority to enhance table sorting
				rank = [t in award for t in ("2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th")]
				if any(rank):
					pri = rank.index(True) + 2
					score_str += str(10-pri if best else pri)
				else:
					score_str +=  "9" if best else "1"

				# Add tooltip text
				score_str += str(obj["award"])
			else:
				score_str += "10"

			# Create video dictionary and add it to the array
			vid = Video.from_dict(obj)
			data = {
				"num" : len(contents) - idx,
				"date" : vid.date,
				"category" : obj["category"],
				"title_id" : vid.short_title() + "%%%" + vid.id,
				"score" : score_str
			}
			min_data.append(data)

		# Write data to file
		try:
			Worker._logger.debug("Writing minified data file...")
			with open(os.path.join(S3.module_dir, S3.min_file_name), "w") as file:
				json.dump(min_data, file, separators=(',', ':'))
			Worker._logger.debug("Successfully wrote minified data file")
		except:
			Worker._logger.error("Failed to write minified data file")
			raise


	@staticmethod
	def _handle_moist_meters(new_data, current_data):
		"""
		Helper function for poll. Checks for undiscovered Moist Meters and sends notifications if any were found.

		Parameters:
		- new_data (list): List of Moist Meter Video objects
		- current_data (list) List of video dicts read from the data file
		"""
		notifications = []

		# Iterate over the new Moist Meters
		for mm_obj in reversed(new_data):
			# Filter duplicates
			known = False
			for obj in current_data:
				if mm_obj == Video.from_dict(obj):
					known = True
					break

			if not known:
				# Send "new Moist Meter" notification
				notifications.append((mm_obj.short_title(), mm_obj.id))

				# Insert a new object into the list
				for index in range(len(current_data)+1):
					if index < len(current_data) and mm_obj.date < current_data[index]["date"]:
						continue

					video_obj = {
						"title" : mm_obj.title,
						"id" : mm_obj.id,
						"date" : mm_obj.date,
						"category" : "",
						"score" : "",
						"rated" : False
					}
					current_data.insert(index, video_obj)
					break

		if len(notifications):
			# Send Pushover notifications
			for title, id in notifications:
				Worker._logger.info("Found New Moist Meter: " + str(title))
				Pushover.send_notification(f"New Moist Meter: {title}", id)

			# Update the file if any changes were made
			try:
				Worker._logger.debug("Updating data file")
				filepath = os.path.join(S3.module_dir, S3.data_file_name)
				with open(filepath, 'w') as file:
					json.dump(current_data, file, indent='\t', separators=(',',' : '))
				Worker._logger.debug("Data file updated successfully")
			except:
				Worker._logger.error("Failed to update data file")
				raise

			notifications.clear()
			S3.put_data(S3.data_file_name)
			Worker._last_modified = int(os.path.getmtime(filepath))
