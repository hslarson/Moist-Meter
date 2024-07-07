"""Class for handling remote file operations via AWS S3"""

import logging
import boto3
import json
import os


class S3():
	"""Class for handling remote file operations via AWS S3"""
	
	# Static members
	_logger = None
	_s3_client = None
	_bucket_name = None
	
	data_file_name = None
	min_file_name = None
	module_dir = os.path.dirname(os.path.realpath(__file__)) 


	@staticmethod
	def begin(config, secrets):
		"""
		Initialize the module
		
		Parameters:
		- config (dict): Dictionary of config information
		- secrets (dict): Dictionary of secret information
		"""

		# Configure logger
		S3._logger = logging.getLogger(__name__)
		S3._logger.setLevel(logging.DEBUG)

		# Retrieve bucket and file names from config
		try:
			S3._bucket_name = config["aws_settings"]["bucket_name"]
			S3.data_file_name = config["aws_settings"]["data_file_name"]
			S3.min_file_name = config["aws_settings"]["min_file_name"]
		except KeyError:
			S3._logger.error("config.json missing info")
			raise

		# Read API key info from secrets
		try:
			access_key = secrets["aws"]["access_key"]
			secret_key = secrets["aws"]["secret_access_key"]
			region     = secrets["aws"]["default_region"]
		except KeyError:
			S3._logger.error("secrets.json missing info")
			raise

		# Set log levels for boto3
		logging.getLogger('boto3').setLevel(logging.INFO)
		logging.getLogger('botocore').setLevel(logging.INFO)
		logging.getLogger('s3transfer').setLevel(logging.INFO)

		# Initialize the AWS S3 wrapper module
		try:
			S3._logger.debug("Starting AWS S3 session")
			session = boto3.Session(
				aws_access_key_id=access_key,
				aws_secret_access_key=secret_key,
				region_name=region
			)

			# Create an S3 client
			S3._s3_client = session.client('s3')
			S3._logger.debug("AWS S3 session started")
		except:
			S3._logger.error("Failed to initialize AWS S3 session")
			raise


	@staticmethod
	def get_data():
		"""Download the data file from S3 and save it locally"""
		try:
			S3._logger.debug("Downloading data file from S3...")
			response = S3._s3_client.download_file(
				S3._bucket_name,
				f"table-data/{S3.data_file_name}",
				os.path.join(S3.module_dir, S3.data_file_name)
			)
			S3._logger.debug(f"Data downloaded successfully. Response={response}")
			# TODO: Check response?
		except:
			S3._logger.error("Failed to load data file from S3")
			raise


	@staticmethod
	def put_data(file_name):
		"""
		Send a file to the S3 server

		Parameters:
		- file_name (str): The name of the file to upload
		"""
		try:
			local_path = os.path.join(S3.module_dir, file_name)
			assert S3.file_exists(local_path), f"Could not find the local file {local_path}"

			remote_path = f"table-data/{file_name}"
			S3._logger.debug(f"Sending {local_path} to S3 {remote_path}...")
			response = S3._s3_client.upload_file(
				Filename=local_path, 
				Bucket=S3._bucket_name, 
				Key=remote_path,
				ExtraArgs={'ContentType': 'application/json'}
			)
			# TODO: Check response?
			S3._logger.debug(f"File uploaded successfully. Response={response}")
		except:
			S3._logger.error("Failed to upload file to S3")
			raise
	

	@staticmethod
	def file_exists(rel_path):
		"""
		Check if a file exists

		Parameters:
		- rel_path (str): The relative path to the file

		Returns (bool): True if the file exists
		"""
		return os.path.isfile(os.path.join(S3.module_dir, rel_path))


	@staticmethod
	def list_data(pull=True):
		"""
		Get the contents of the data file as a list.

		Parameters:
		- pull (bool): If True, retrieve new data from the server

		Returns (list): The contents of the data file
		"""
		# Relative path to the data
		data_path = os.path.join(S3.module_dir, S3.data_file_name)

		# Get fresh data from server
		if pull or not S3.file_exists(data_path):
			S3.get_data()

		try:
			# Return the data as a list
			with open(data_path, "r") as file:
				contents = json.load(file)
				return list(contents)
		except:
			S3._logger.error("Failed to read list from data file")
			raise
