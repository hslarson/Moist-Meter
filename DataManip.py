from datetime import datetime
import json
from posixpath import relpath
import subprocess
import os
import time
from YouTube import YouTube

class FileOps():

	PULL = "get"
	PUSH = "put"
	FTP_SCRIPT_NAME = "ftp_script.txt"
	SOURCE_DIR = os.path.dirname(os.path.realpath(__file__)) + '\\'

	def __init__(self):
		with open(FileOps.SOURCE_DIR + 'secrets.json') as file:
			json_obj = json.load(file)

			FileOps.ftp_host = json_obj["ftp_host"]
			FileOps.ftp_username = json_obj["ftp_username"]
			FileOps.ftp_password = json_obj["ftp_password"]

			file.close()


	# A Special Destructor to Make Sure the FTP Script Gets Deleted
	def __del__(self):
		FileOps.delete_file(FileOps.FTP_SCRIPT_NAME)


	# A Helper Function to Remove the Temporary FTP Script
	def delete_file(rel_path):
		if os.path.isfile(FileOps.SOURCE_DIR + rel_path):
			os.system("del " + FileOps.SOURCE_DIR + rel_path)
	

	# Performs an ftp operation by creating a script file and running it in the terminal
	def __ftp_operation(operation, filename, ftp_filepath="htdocs"):

		with open(FileOps.SOURCE_DIR + FileOps.FTP_SCRIPT_NAME, 'w') as file:
			file.write(FileOps.ftp_username + "\n")
			file.write(FileOps.ftp_password + "\n")
			file.write("cd " + str(ftp_filepath) + "\n")
			file.write("lcd " + FileOps.SOURCE_DIR[:-1] + "\n")
			file.write(str(operation) + " " + str(filename) + "\n")
			file.write("close\n")
			file.write("quit\n")
			file.close()

		# subprocess.check_output("ftp -s:ftp_script.txt " + self.ftp_host, shell=True)
		os.system("ftp -s:" + FileOps.SOURCE_DIR + FileOps.FTP_SCRIPT_NAME + " " + FileOps.ftp_host)
		FileOps.delete_file(FileOps.FTP_SCRIPT_NAME)


	# Pulls the data File from the FTP server
	def pull(filename=".data.json", destination_dir="", ftp_dir="htdocs"):
		FileOps.__ftp_operation(FileOps.PULL, filename, ftp_dir)
		
		if len(destination_dir) and os.path.isfile(FileOps.SOURCE_DIR + ".data.json"):

			print("move " + FileOps.SOURCE_DIR + ".data.json" + " " + FileOps.SOURCE_DIR + destination_dir)
			os.system("move " + FileOps.SOURCE_DIR + ".data.json" + " " + FileOps.SOURCE_DIR + destination_dir)


	# Pushes the data File to the FTP server
	def put(filename=".data.json", dir="htdocs"):
		FileOps.__ftp_operation(FileOps.PUSH, filename, dir)



from pathlib import Path, PurePath

class DataTools():

	def __init__(self):
		DataTools.yt_obj = YouTube()
		DataTools.file_ops = FileOps()

		secrets_file = open(FileOps.SOURCE_DIR + 'secrets.json')
		config_file  = open(FileOps.SOURCE_DIR + 'config.json')

		secrets_obj = json.load(secrets_file)
		config_obj = json.load(config_file)

		DataTools.pushover_settings = config_obj["pushover_settings"]
		DataTools.pushover_secrets = secrets_obj["pushover"]
		DataTools.poll_settings = config_obj["poll_settings"]
		DataTools.audit_settings = config_obj["audit_settings"]

		secrets_file.close()
		config_file.close()


	def __del__(self):

		config = {}
		config["pushover_settings"] = DataTools.pushover_settings
		config["poll_settings"] = DataTools.poll_settings
		config["audit_settings"] = DataTools.audit_settings
		print(config)

		with  open(FileOps.SOURCE_DIR + 'config.json', 'w') as file:
			json.dump(config, file, indent='\t', separators=(',',' : '))
			file.close()

		FileOps.delete_file(".data.json")


	def poll():

		if time.time() > DataTools.poll_settings["last_poll"] + DataTools.poll_settings["poll_frequency_seconds"]:

			# Pull YouTube Data
			uploads = DataTools.yt_obj.pull_uploads(after=DataTools.poll_settings["last_poll"])
			moist_meters = DataTools.__filter_moist_meters(uploads)

			# If a New Moist Meter is Found, Append It To the List
			if (len(moist_meters)):

				# Load the Data File
				contents = DataTools.__load_data()

				# Iterate Over the New Moist Meters
				notifications = []
				for title, id, date in reversed(moist_meters):

					# Filter Duplicates
					known = False
					for obj in contents:
						if obj["date"] <= date:

							if obj["date"] != date: notifications.append(obj)	
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
						contents.insert(0, payload)

				# Upload the Updated Config File
				with open(FileOps.SOURCE_DIR + ".data.json", "w") as file:
					json.dump(contents, file, indent='\t', separators=(',',' : '))
					file.close()	
				FileOps.put()

				# Send Pushover Notifications
				for title, id, _ in notifications:
					DataTools.__send_notification(f"New Moist Meter: {title}", id)
			
			# Update Last Poll Variable
			DataTools.poll_settings["last_poll"] = time.time()
		else:
			return

		
	def audit():

		# Load the Data File
		contents = DataTools.__load_data()

		# Pull Uploads
		last_date = contents[:-1]["date"]
		uploads = DataTools.yt_obj.pull_uploads(after=last_date)

		# Iterate Over Uploads
		altered = False
		notifications = []
		for index, obj in enumerate(contents):
			
			# Check For Duplicates in .data.json
			for i, o in enumerate(contents[index+1:]):
				if obj["id"] == o["id"]:
					print("Found Duplicate. Id for object\n\t" + obj + "\nmatches the id for\n\t" + o)
					notifications.append("Found Duplicate. Id for object\n\t" + obj + "\nmatches the id for\n\t" + o)
					del contents[index + i + 1]
					altered = True

			# Find the Video with Matching Upload Timestamp from Uploads
			for title, id, date in uploads:
				if date == obj["date"]:

					# Compare Title
					if title != obj["title"]:
						print("Title Changed: " + str(obj["title"]) + " -> " + str(title))
						notifications.append("Title Changed: " + str(obj["title"]) + " -> " + str(title))
						obj["title"] = title
						altered = True

					# Compare ID
					if id != obj["id"]:
						print("ID Changed for " + str(obj["title"]) + ": " + str(obj["id"]) + " -> " + str(id))
						notifications.append("ID Changed for " + str(obj["title"]) + ": " + str(obj["id"]) + " -> " + str(id))
						obj["id"] = id
						altered = True

		# Sort the List (Newest -> Oldest)
		if (DataTools.__sort(contents)):
			altered = True
		
		if altered:
			# Upload the File if Any Changes Were Made
			with open(FileOps.SOURCE_DIR + ".data.json", "w") as file:
				json.dump(contents, file, indent='\t', separators=(',',' : '))
				file.close()	
			FileOps.put()

			# Send Notifications
			for msg in notifications:
				DataTools.__send_notification(msg)
		
		# Back Up the Data File
		DataTools.back_up()


	# Creates a Local Copy of the .data.json
	def back_up():
		
		temp = FileOps()
		backups_folder = FileOps.SOURCE_DIR + "Data_Backups\\"

		# Pull Data & Move it To Backups Folder
		temp.pull(destination_dir="Data_Backups")

		# Rename it to Include Time and Date Info
		print("rename " + backups_folder + ".data.json" + " backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")
		os.system("rename " + backups_folder + ".data.json" + " backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")
		
		# Count Backups in Dir and Delete Some Until There is Only 10
		files = [ name for name in os.listdir(backups_folder) if ".json" in name and "backup_" in name ]
		print(files)	
		while (len(files) > 10):
			os.system("del " + backups_folder + files.pop(0))
			del files[0]


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
				title = title.replace("Moist Meter: ", "").replace(
					"Moist Meter | ", "")
				out.append((title, id, date))

		print("Found " + str(mm_count) + " Moist Meters")
		return out


	def __send_notification(msg , id):
		pass
	

	# Returns the contents of .data.json as a list
	def __load_data():

		# Check if the file exists. If not, pull it
		if not os.path.isfile(FileOps.SOURCE_DIR + ".data.json"):
			FileOps.pull()

		# Load the file contents into a list
		with open(FileOps.SOURCE_DIR + ".data.json", 'r') as file:
			contents = json.load(file)
			file.close()

		return list(contents)	
