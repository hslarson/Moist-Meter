"""Class for interacting with the CloudFlare API"""

from s3 import S3
import requests
import logging


class CloudFlare():
	"""Class for interacting with the CloudFlare API"""

	# Static members
	_logger = None
	_api_key = None
	_zone = None

	@staticmethod
	def begin(secrets):
		"""
		Initialize the module
		
		Parameters:
		- secrets (dict): Dictionary of secret information
		"""
		
		# Configure logger
		CloudFlare._logger = logging.getLogger(__name__)
		CloudFlare._logger.setLevel(logging.DEBUG)

		# Read the Cloudflare API key and website zone from secrets
		try:
			CloudFlare._api_key = secrets["cloudflare"]["api_key"]
			CloudFlare._zone    = secrets["cloudflare"]["zone"]
		except KeyError:
			CloudFlare._logger.error("secrets.json missing info")
			raise


	@staticmethod
	def purge_cache():
		"""Invalidate the data file in the cloudflare cache"""

		# Check if module has been initialized
		assert CloudFlare._api_key and CloudFlare._zone, "Module not initialized. Call begin()"

		# Headers for the API request
		headers = {
			"Authorization" : f"Bearer {CloudFlare._api_key}",
			"Content-Type" : "application/json",
		}

		# Request payload
		data = {"files" : [
			f"https://moistmeter.org/{S3.min_file_path}",
			f"https://www.moistmeter.org/{S3.min_file_path}",
		]}

		# Request URL
		url = f"https://api.cloudflare.com/client/v4/zones/{CloudFlare._zone}/purge_cache/"
			
		# Send POST request
		try:
			CloudFlare._logger.debug("Invalidating cached data file...")
			response = requests.post(url, headers=headers, json=data)
			assert response.status_code == 200, f"Bad response code: {response.status_code}"
			# TODO: Check success flag?
		except:
			CloudFlare._logger.error("Failed to invalidate cached file")
			raise
		else:
			CloudFlare._logger.debug(f"Cache purged successfully. Response={response}")
