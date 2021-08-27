from datetime import datetime
from YouTube import YouTube
import subprocess
import json
import time
import os



class FileOps():

	SOURCE_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'


	# Constructor
	def __init__(self):

		file = open(FileOps.SOURCE_DIR + 'secrets.json', 'r')
		if file.readable:
			json_obj = json.load(file)

			FileOps.ftp_host = json_obj["ftp_host"]
			FileOps.ftp_username = json_obj["ftp_username"]
			FileOps.ftp_password = json_obj["ftp_password"]

			file.close()
		else:
			raise Exception("Could not Read secrets.json")


	# A Helper Function for Removing Files
	def delete_file(rel_local_path):
		if os.path.isfile(FileOps.SOURCE_DIR + rel_local_path):
			p = subprocess.run(["rm", FileOps.SOURCE_DIR + rel_local_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			if os.path.isfile(FileOps.SOURCE_DIR + rel_local_path) or p.returncode:
				raise Exception("Failed to Delete Local File: " + str(rel_local_path) + ". Args='" + " ".join(p.args) + "'")
	

	# Used to pull files from FTP server
	# Gets the Data File by Default
	def pull_file(absolute_remote_path="/htdocs/.data.json", rel_local_path=".data.json"):

		ftp_url = 'ftp://' + FileOps.ftp_username + ':' + FileOps.ftp_password + '@' + FileOps.ftp_host + absolute_remote_path
		p = subprocess.run(["wget", "-O", FileOps.SOURCE_DIR + rel_local_path, ftp_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		
		if not os.path.isfile(FileOps.SOURCE_DIR + rel_local_path) or p.returncode:
			raise Exception("Unable to Pull File " + str(absolute_remote_path) + " from Server. Args='" + " ".join(p.args) + "'")


	# Pushes the data File to the FTP server
	def put_file(absolute_remote_path="/htdocs/", rel_local_path=".data.json", remove_local_file=True):
		
		ftp_url = 'ftp://' + FileOps.ftp_username + ':' + FileOps.ftp_password + '@' + FileOps.ftp_host + absolute_remote_path
		p = subprocess.run(["wput", "--reupload", "-A", "--basename=" + FileOps.SOURCE_DIR, FileOps.SOURCE_DIR + rel_local_path, ftp_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		
		if (p.returncode):
			raise Exception("Unable to Send File to Server. Args='" + " ".join(p.args) + "'")
		elif remove_local_file:
			FileOps.delete_file(rel_local_path)



class DataTools():

	# Constructor
	def __init__(self):
		DataTools.yt_obj = YouTube()
		DataTools.file_ops = FileOps()

		# Clear Lingering Data Files
		FileOps.delete_file(".data.json")

		# Load the secrets file
		secrets_file = open(FileOps.SOURCE_DIR + 'secrets.json')
		if secrets_file.readable:
			secrets_obj = json.load(secrets_file)
			DataTools.pushover_secrets = secrets_obj["pushover"]
			secrets_file.close()
		else:
			raise Exception("Failed to Read secrets.json")

		# Load the config file
		config_file = open(FileOps.SOURCE_DIR + 'config.json')
		if config_file.readable:
			config_obj = json.load(config_file)

			DataTools.pushover_settings = config_obj["pushover_settings"]
			DataTools.poll_settings = config_obj["poll_settings"]
			DataTools.audit_settings = config_obj["audit_settings"]
		
			config_file.close()
		else:
			raise Exception("Failed to Load config.json")


	# Saves the Local Config File
	def save_config():

		# Read the Config File
		file = open(FileOps.SOURCE_DIR + 'config.json', 'r')
		if file.readable:
			contents = json.load(file)
			file.close()
		else:
			raise Exception("config.json Could Not be Read")

		# Alter the last poll/audit variables
		contents["poll_settings"]["last_poll"] = DataTools.poll_settings["last_poll"] 
		contents["audit_settings"]["last_audit"] = DataTools.audit_settings["last_audit"] 

		# Replace the Contents of the Config File
		file = open(FileOps.SOURCE_DIR + 'config.json', 'w')
		if file.writable:
			json.dump(contents, file, indent='\t', separators=(',',' : '))
			file.close()
		else:
			raise Exception("config.json Could Not be Written To")


	# Gets YoutTube Data and Checks for New Moist Meters
	# If Found, Add Entry to Data File 
	def poll(logger):

		# Maintain the Desired Poll Frequency
		if time.time() < DataTools.poll_settings["last_poll"] + DataTools.poll_settings["poll_frequency_seconds"]:
			return DataTools.poll_settings["last_poll"] + DataTools.poll_settings["poll_frequency_seconds"] - time.time()

		logger.info("Polling")

		# Pull YouTube Data
		uploads = YouTube.pull_uploads(after=DataTools.poll_settings["last_poll"])
		moist_meters = DataTools.__filter_moist_meters(uploads)

		# If a New Moist Meter is Found, Append It To the List
		if (len(moist_meters)):

			# Load the Data File and make sure it's sorted
			contents = DataTools.__load_data()
			DataTools.__sort(contents)

			# Iterate Over the New Moist Meters
			notifications = []
			for title, id, date in reversed(moist_meters):

				# Filter Duplicates
				known = False
				for obj in contents:
					if obj["date"] <= date:
						known = obj["date"] == date
						break
					
				# Insert a New Object into the List
				if not known:
					payload = {
						"date" : date,
						"title" : title,
						"id" : id,
						"category" : "",
						"score" : "",
						"rated" : False
					}
					notifications.append((title, id))
					contents.insert(0, payload)
				
			if len(notifications):
				# Send Pushover Notifications
				for title, id in notifications:
					logger.info("Found New Moist Meter: " + str(title))
					DataTools.__send_notification(f"New Moist Meter: {title}", id)

				# Upload the File if Any Changes Were Made
				file = open(FileOps.SOURCE_DIR + ".data.json", 'w')
				if file.writable:
					json.dump(contents, file, indent='\t', separators=(',',' : '))
					file.close()
				else:
					raise Exception("Could Not Write to .data.json")
				
				notifications.clear()
				logger.info("Sending Updated Data to Server")
				FileOps.put_file(remove_local_file=False)
		
			FileOps.delete_file(".data.json")

		# Update last_poll last (this way if errors are encountered the poll will retry from the previous last_poll)
		DataTools.poll_settings["last_poll"] = time.time()
		DataTools.save_config()
		return DataTools.poll_settings["last_poll"] + DataTools.poll_settings["poll_frequency_seconds"] - time.time()

	
	# Pulls te data file and makes sure everything is correct
	# (i.e. No Duplicates, Sorted New->Old, Valid Video ID's)
	def audit(logger):

		# Maintain the Desired Audit Frequency
		if time.time() < DataTools.audit_settings["last_audit"] + DataTools.audit_settings["audit_frequency_seconds"]:
			return DataTools.audit_settings["last_audit"] + DataTools.audit_settings["audit_frequency_seconds"] - time.time()
		else:
			DataTools.audit_settings["last_audit"] = time.time()
			DataTools.save_config()

		logger.info("Auditing")

		# Load the Data File
		contents = DataTools.__load_data()

		# Pull Uploads
		last_date = contents[-1]["date"]
		uploads = YouTube.pull_uploads(after=last_date)
		
		altered = False
		notifications = []

		# Sort the List (Newest -> Oldest)
		if (DataTools.__sort(contents)):
			logger.warning("List Was Out of Order")
			altered = True

		# Iterate Over Uploads
		for index, obj in enumerate(contents):
			
			# Check For Duplicates in .data.json
			for i, o in enumerate(contents[index+1:]):
				if obj["id"] == o["id"]:
					logger.warning("Found Duplicate. Id=" + obj["id"] + ". Deleting...")
					notifications.append(("Found Duplicate. Id=" + obj["id"] + ". Deleting...", obj["id"]))
					del contents[index + i + 1]
					altered = True

			# Find the Video with Matching Upload Timestamp from Uploads
			for _, id, date in uploads:
				if date == obj["date"]:

					# Compare ID
					if id != obj["id"]:
						logger.warning("ID Changed for " + str(obj["title"]) + ": " + str(obj["id"]) + " -> " + str(id))
						notifications.append(("ID Changed for " + str(obj["title"]) + ": " + str(obj["id"]) + " -> " + str(id), obj["id"]))
						obj["id"] = id
						altered = True
					
					break
			else:
				logger.warning(f"Found No Matching Video for {obj['title']}")
				notifications.append((f"Found No Matching Video for {obj['title']}", obj["id"]))
		
		if altered:
			# Upload the File if Any Changes Were Made
			file = open(FileOps.SOURCE_DIR + ".data.json", 'w')
			if file.writable:
				json.dump(contents, file, indent='\t', separators=(',',' : '))
				file.close()
			else:
				raise Exception("Could Not Write to .data.json")

			logger.info("Sending Updated Data to Server")
			FileOps.put_file()

		# Send Notifications
		for msg, id in notifications:
			DataTools.__send_notification(msg, id)
		else:
			notifications.clear()
		
		# Back Up the Data File
		logger.info("Backing Up Data File")
		DataTools.back_up()

		return DataTools.audit_settings["last_audit"] + DataTools.audit_settings["audit_frequency_seconds"] - time.time()


	# Creates a Local Copy of the .data.json
	def back_up():
		
		# Pull Data, Move it To Backups Folder, and Rename it
		FileOps.pull_file(rel_local_path="Data_Backups/backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")

		# Count Backups in Dir and Delete Some Until There is Only 10
		backups_folder_name = "Data_Backups/"
		files = [ name for name in os.listdir(FileOps.SOURCE_DIR + backups_folder_name) if ".json" in name and "backup_" in name ]
		while (len(files) > 10):
			FileOps.delete_file(backups_folder_name + files.pop(0))


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
	

	# Separate Moist Meters from Normal Uploads
	def __filter_moist_meters(upload_list):
		out = []
		mm_count = 0
		for title, id, date in upload_list:
			if "Moist Meter: " in title or "Moist Meter | " in title:
				mm_count += 1
				title = title.replace("Moist Meter: ", "").replace("Moist Meter | ", "")
				out.append((title, id, date))

		return out


	# Sends a Pushover Notification 
	def __send_notification(msg , id=None):
		if not DataTools.pushover_settings["allow_pushover_notifications"]:
			return
		
		payload = {
			"token" : DataTools.pushover_secrets["app_token"],
			"user" : DataTools.pushover_secrets["user_key"],
			"message" : msg
		}
		if type(id) == str:
			payload["url"] = ("https://www.youtube.com/watch?v=" + id if "New Moist Meter:" not in msg else "http://www.moistmeter.42web.io/form/")
			payload["url_title"] = ("Watch Video" if "New Moist Meter:" not in msg else "Go To Form")

		YouTube.rqst.post("https://api.pushover.net/1/messages.json", params=payload)
	

	# Returns the contents of .data.json as a list
	def __load_data():

		# Delete Old Files and Pull the New One
		FileOps.delete_file(".data.json")
		FileOps.pull_file()

		# Load the file contents into a list
		file = open(FileOps.SOURCE_DIR + ".data.json", 'r')
		if file.readable:
			contents = json.load(file)
			file.close()
		else:
			raise Exception("Could Not Read .data.json")

		return list(contents)
