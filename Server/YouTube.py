"""Classes for interacting with YouTube's API"""

from datetime import datetime, timezone
import requests
import logging
import time


class Video():
	"""Encapsulates data related to a YouTube video"""

	def __init__(self, title, date, id):
		self.title = title
		self.date = date
		self.id = id

	def __eq__(self, other):
		TITLE_MATCH_MARGIN = 3*24*60*60 # 3 Days

		# First, try to match by ID
		if self.id == other.id:
			return True

		# Next, see if the videos have the same title 
		# AND were uploaded around the same time
		elif self.title == other.title:
			if (self.date >= other.date - TITLE_MATCH_MARGIN) and (self.date <= other.date + TITLE_MATCH_MARGIN):
				return True

		return False

	def short_title(self):
		"""For Moist Meters, deletes the 'Moist Meter' prefix from the title"""
		return str(self.title).replace("Moist Meter:", "").replace("Moist Meter |", "").strip()

	def from_dict(video_obj: dict):
		"""Constructs a Video object from a dictionary containing 'title, 'data,' and 'id' keys"""
		return Video(video_obj["title"], video_obj["date"], video_obj["id"])

	def is_moist_meter(self):
		"""Returns true if this video is a Moist Meter"""
		return self.short_title() != self.title



class YouTube():
	"""Class for interacting with the YouTube API"""

	# Static method
	_logger = None
	_rqst = None
	_api_key = None
	_api_base_url = "https://www.googleapis.com/youtube/v3/"

	@staticmethod
	def begin(secrets):
		"""
		Initialize the module
		
		Parameters:
		- secrets (dict): Dictionary of secret information
		"""

		# Configure logger
		YouTube._logger = logging.getLogger(__name__)
		YouTube._logger.setLevel(logging.DEBUG)

		# Initialize requests session
		if isinstance(YouTube._rqst, requests.Session):
			YouTube._rqst.close()
		YouTube._rqst = requests.session()

		# Read the YouTube API key from secrets
		try:
			YouTube._api_key = secrets["youtube_api_key"]
		except KeyError:
			YouTube._logger.error("secrets.json missing info")
			raise

	
	@staticmethod
	def pull_uploads(after):
		"""
		Fetch a list of penguinz0/Moist Charlie Clips videos.

		Parameters:
		- after (int): Epoch timestamp to start the search from

		Returns (list): List of Video objects uploaded after the given timestamp
		"""

		# Set the block size based on the window duration
		# Block size is the number of videos to request in a single API call
		window = time.time() - (after if after else 0)
		max_extries = 50
		if window < 3600 * 8:
			max_extries = 3
		elif window < 3600 * 24 * 7:
			max_extries = 20

		# Pull penguinz0 videos
		YouTube._logger.debug("Pulling penginz0 videos")
		vids = YouTube._get_videos_by_playlist("UCq6VFHwMzcMXbuKyG7SQYIg", "uploads", after=after, block_size=max_extries)

		# Pull 'Moist Charlie Clips' videos
		YouTube._logger.debug("Pulling Moist Charlie Clips videos")
		vids += YouTube._get_videos_by_playlist("UC4EQHfzIbkL_Skit_iKt1aA", "uploads", after=after, block_size=max_extries)

		# Sort by date
		vids.sort(key=lambda v: v.date, reverse=True)
		return vids


	@staticmethod
	def _get_videos_by_playlist(channel_id, playlist_name, before=None, after=None, block_size=20):
		"""
		Fetch a list of all videos for a given channel_id and playlist

		Parameters:
		- channel_id (str): The youtube channel ID
		- playlist_name (str): The name of the playlist to retrieve videos from
		- before (int): Get videos from before this epoch timestamp
		- after (int): Get videos from after this epoch timestamp
		- block_size (int): The number of entries to pull at a given time

		Return (list): List of Video objects
		"""

		# Check timestamp
		if (before and (after > before)):
			YouTube._logger.warning("'after' should not be greater then 'before'")
			return

		# Get playlist ID
		try:
			YouTube._logger.debug("Getting playlist ID")
			url = f"{YouTube._api_base_url}channels?part=contentDetails&id={channel_id}&key={YouTube._api_key}"
			response = YouTube._rqst.get(url)
			if response.status_code != 200:
				raise StatusCodeError(response.status_code)
			playlist_id = response.json()["items"][0]["contentDetails"]["relatedPlaylists"][playlist_name]
			YouTube._logger.debug("Got playlist ID")
		except:
			YouTube._logger.error("Could not retrieve playlist ID")
			raise

		big_list = []
		count = 0

		while count >= 0:
			# Request the next block
			url = YouTube._api_base_url + "playlistItems?part=snippet"
			url += "&maxResults=" + str(block_size)
			url += "&playlistId=" + str(playlist_id)
			url += "&key=" + str(YouTube._api_key)

			# Don't add token for first request
			if count != 0:
				url += "&pageToken=" + str(next_token)
			count += 1

			try:
				# Make the request
				YouTube._logger.debug(f"Pulling playlist block {count}")
				response = YouTube._rqst.get(url)
				if response.status_code != 200:
					raise StatusCodeError(response.status_code)

				# Parse JSON
				response = response.json()
			except:
				YouTube._logger.error("Failed to read playlist data")
				raise

			# Get next block token
			if isinstance(response, dict) and ("nextPageToken" in response):
				next_token = response["nextPageToken"]
			else: count = -1

			for item in response["items"]:
				# Get timestamp
				tm = YouTube._str2timestamp(item["snippet"]["publishedAt"])

				# Only append to list if the timestamp
				# is within the specified range
				if before and tm > before:
					continue
				elif after and tm < after:
					count = -1
					break

				# Append Video to list
				title = item["snippet"]["title"]
				vid_id = item["snippet"]["resourceId"]["videoId"]
				big_list.append(Video(title, tm, vid_id))

		return big_list


	@staticmethod
	def _str2timestamp(date_string):
		"""
		Converts YouTube's time string into a UTC timestamp.

		Parameters:
		- date_string (str): The date string that YouTube provides (Ex. 2021-07-15T14:12:16Z)

		Returns (int): Epoch timestamp corresponding to date_string
		"""
		date = date_string[:date_string.find("T")]
		time = date_string[date_string.find("T")+1:-1]

		year, month, day = date.split("-")
		hour, minute, second = time.split(":")

		return int(datetime(
			int(year), 
			int(month), 
			int(day), 
			int(hour), 
			int(minute), 
			int(second), 
			tzinfo=timezone.utc
		).timestamp())


class StatusCodeError(BaseException):
    """Exception noting when a request fails"""
    def __init__(self, code):
        self.msg = "Bad Status Code: " + str(code)
