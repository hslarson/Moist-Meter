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
	
	data_file_path = None
	min_file_path = None 


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
			S3.data_file_path = config["aws_settings"]["data_file_path"]
			S3.min_file_path = config["aws_settings"]["min_file_path"]
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
	def put_data(remote_file, json_str):
		"""
		Send a JSON file to the S3 server

		Parameters:
		- remote_file (str): The file path of the data in the S3 bucket
		- json_str (str): The JSON contents to put in the remote file
		"""
		try:
			S3._logger.debug(f"Sending data to S3 {remote_file}...")
			response = S3._s3_client.put_object(
				Bucket=S3._bucket_name,
				Key=remote_file,
				Body=json_str.encode('utf-8'),
				Metadata={'ContentType': 'application/json'}
			)
			# TODO: Check response?
			S3._logger.debug(f"File uploaded successfully. Response={response}")
		except:
			S3._logger.error("Failed to upload file to S3")
			raise


	@staticmethod
	def list_data():
		"""
		Get the contents of the data file as a list.

		Returns (tuple): 
		- (list): The contents of the data file
		- (int): The last modified timestamp
		"""
		try:
			S3._logger.debug("Downloading data file from S3...")

			# Get the object and its metadata
			response = S3._s3_client.get_object(
				Bucket=S3._bucket_name, 
				Key=S3.data_file_path
			)
			S3._logger.debug(f"Data downloaded successfully. Response={response}")

			# Read and decode the contents of the file
			file_content = response['Body'].read().decode('utf-8')
			return list(json.loads(file_content))
		except:
			S3._logger.error("Failed to load data file from S3")
			raise


	@staticmethod
	def last_modified(remote_path):
		"""
		Get the last modified timestamp of a remote file.
		
		Parameters:
		- remote_path (str): The location of the file in the S3 bucket

		Returns (int): The epoch timestamp indicating when the file was last modified
		"""

		# Fetch file header from S3
		try:
			S3._logger.debug(f"Reading last modified timestamp for {remote_path}")
			response = S3._s3_client.head_object(
				Bucket=S3._bucket_name, 
				Key=remote_path
			)
			S3._logger.debug(f"Got header. Response={response}")

			# TODO: Check response?
			return int(response['LastModified'].timestamp())
		except:
			S3._logger.error("Failed to read last modified timestamp")
			raise
