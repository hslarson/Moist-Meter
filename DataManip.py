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


	def poll():

		if time.time() > DataTools.poll_settings["last_poll"] + DataTools.poll_settings["poll_frequency_seconds"]:

			# Pull Youtube Data
			uploads = DataTools.yt_obj.pull_uploads(after=DataTools.poll_settings["last_poll"])
			moist_meters = DataTools.__filter_moist_meters(uploads)


			# If a New Moist Meter is Found, Append It To the List
			if (len(moist_meters)):

				# Load the Data File
				FileOps.pull()
				with open(FileOps.SOURCE_DIR + ".data.json", 'r') as file:
					contents = json.load(file)
					file.close()

				# Iterate Over the New Moist Meters
				for title, id, date in reversed(moist_meters):

					print((title, id, date))

					# Filter Duplicates
					known = False
					for obj in contents:
						print("- " + str((obj["title"], obj["id"], obj["date"])))
						if obj["date"] <= date:
							
							known = (obj["date"] == date)
							if (known): print("Known")
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
				FileOps.delete_file(".data.json")

				# Send Pushover Notifications
				for title, id, _ in reversed(moist_meters):
					DataTools.__send_notification(title, id)
			
			# Update Last Poll Variable
			DataTools.poll_settings["last_poll"] = time.time()
		else:
			return

		


	def audit():
		pass
		

	def edit_entry():
		pass

	def back_up():
		
		temp = FileOps()
		backups_folder = FileOps.SOURCE_DIR + "Data_Backups\\"

		# Pull Data & Move it To Backups Folder
		temp.pull(destination_dir="Data_Backups")

		# Rename it to Include Time and Date Info
		print("rename " + backups_folder + ".data.json" + " backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")
		os.system("rename " + backups_folder + ".data.json" + " backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")
		
		# Cound Backups in Dir and Delete Some Until There is Only 10
		files = [ name for name in os.listdir(backups_folder) if ".json" in name and "backup_" in name ]
		print(files)	
		while (len(files) > 10):
			os.system("del " + backups_folder + files.pop(0))
			del files[0]


	def __sort():
		pass
	
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

	def __send_notification(title, id):
		pass
	