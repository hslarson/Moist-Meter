from datetime import datetime
import subprocess
import json
import os


class FileOps():

	SOURCE_DIR = os.path.dirname(os.path.realpath(__file__)) + '/'

	# Constructor
	def __init__(self):

		# Read Secrets File
		file = open(FileOps.SOURCE_DIR + 'secrets.json', 'r')
		if file.readable:
			json_obj = json.load(file)

			FileOps.ftp_host = json_obj["ftp_host"]
			FileOps.ftp_username = json_obj["ftp_username"]
			FileOps.ftp_password = json_obj["ftp_password"]

			file.close()
		else:
			raise Exception("Could not Read secrets.json")


	# Returns the contents of .data.json as a list
	def load_data():

		# Delete Old Files and Pull the New One
		FileOps.delete_file(".data.json")
		FileOps.__ftp_pull_file("/htdocs/.data.json", ".data.json")

		# Load the file contents into a list
		file = open(FileOps.SOURCE_DIR + ".data.json", 'r')
		if file.readable:
			contents = json.load(file)
			file.close()
		else:
			raise Exception("Could Not Read .data.json")

		return list(contents)
	

	# Public method to save data file to server
	def save_data(remove_local):
		FileOps.__ftp_put_file("/htdocs/.data.json", ".data.json", remove_local_file=remove_local)


	# Creates a Local Copy of the .data.json
	def back_up_data():

		# Pull Data, Move it To Backups Folder, and Rename it
		FileOps.__ftp_pull_file("/htdocs/.data.json", "Data_Backups/backup_" + datetime.utcnow().strftime('%m-%d-%y_%H-%M-%S') + ".json")

		# Count Backups in Dir and Delete Some Until There is Only 10
		backups_folder_name = "Data_Backups/"
		files = [ name for name in os.listdir(FileOps.SOURCE_DIR + backups_folder_name) if ".json" in name and "backup_" in name ]
		while (len(files) > 10):
			FileOps.delete_file(backups_folder_name + files.pop(0))


	# A Helper Function for Removing Files
	def delete_file(rel_local_path):
		if os.path.isfile(FileOps.SOURCE_DIR + rel_local_path):
			p = subprocess.run(["rm", FileOps.SOURCE_DIR + rel_local_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

			if os.path.isfile(FileOps.SOURCE_DIR + rel_local_path) or p.returncode:
				raise Exception("Failed to Delete Local File: " + str(rel_local_path) + ". Args='" + " ".join(p.args) + "'")


	# Used to pull files from FTP server
	# Gets the Data File by Default
	def __ftp_pull_file(absolute_remote_path, rel_local_path):

		ftp_url = 'ftp://' + FileOps.ftp_username + ':' + FileOps.ftp_password + '@' + FileOps.ftp_host + absolute_remote_path
		p = subprocess.run(["wget", "-O", FileOps.SOURCE_DIR + rel_local_path, ftp_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

		if not os.path.isfile(FileOps.SOURCE_DIR + rel_local_path) or p.returncode:
			raise SubprocessError("Unable to Pull File " + str(absolute_remote_path) + " from Server. Args='" + " ".join(p.args) + "'")


	# Pushes the data File to the FTP server
	def __ftp_put_file(absolute_remote_path, rel_local_path, remove_local_file=True):

		ftp_url = 'ftp://' + FileOps.ftp_username + ':' + FileOps.ftp_password + '@' + FileOps.ftp_host + absolute_remote_path
		p = subprocess.run(["wput", "--reupload", "-A", "--basename=" + FileOps.SOURCE_DIR, FileOps.SOURCE_DIR + rel_local_path, ftp_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

		if (p.returncode):
			raise SubprocessError("Unable to Send File to Server. Args='" + " ".join(p.args) + "'")
		elif remove_local_file:
			FileOps.delete_file(rel_local_path)


# Exception noting when a subprocess fails
class SubprocessError(BaseException):
    def __init__(self, message):
        self.msg = message
