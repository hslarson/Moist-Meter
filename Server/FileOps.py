import subprocess
import json
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