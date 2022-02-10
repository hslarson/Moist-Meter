from datetime import datetime, timezone
import requests
import json
import time
import os



class YouTube():

	class Video():
		def __init__(self, title, date, id):
			self.title = title
			self.date = date
			self.id = id

		def __eq__(self, other):
			TITLE_MATCH_MARGIN = 259200 # 3 Days

			# First Try to Match By ID
			if self.id == other.id:
				return True

			# Next See if the Videos Have the Same Title AND Were Uploaded Around the Same Time
			elif self.title == other.title:
				if (self.date >= other.date - TITLE_MATCH_MARGIN) and (self.date <= other.date + TITLE_MATCH_MARGIN):
					return True

			return False

		def from_dict(video_obj: dict):
			return YouTube.Video(video_obj["title"], video_obj["date"], video_obj["id"])

		def is_moist_meter(self):
			return ("Moist Meter |" in self.title) or ("Moist Meter:" in self.title)


	rqst = requests.session()
	API_BASE_URL = "https://www.googleapis.com/youtube/v3/"

	def __init__(self):
		file = open(os.path.dirname(os.path.realpath(__file__)) + '/secrets.json', 'r')
		if file.readable:
			YouTube.API_KEY = json.load(file)["youtube_api_key"]
			file.close()
		else:
			raise Exception("Failed to Read secrets.json")


	# Returns a List of Every Video Uploaded by Penguinz0
	def pull_uploads(after):

		window = time.time() - (after if after else 0)
		max_extries = 50
		if window < 3600 * 8:
			max_extries = 3
		elif window < 3600 * 24 * 7:
			max_extries = 20

		return YouTube.get_videos_by_playlist(after=after, block_size=max_extries)


	# Returns All of the Videos in a Given Playlist as Video Objects
	def get_videos_by_playlist(username="penguinz0", playlist_name="uploads", before=None, after=None, block_size=20):

		if (before and (after > before)):
			raise Exception("In get_videos_by_playlist(): 'after' should not be greater then 'before'")

		big_list = []
		running = True
		first = True

		# Get Playlist id
		response = YouTube.rqst.get(YouTube.API_BASE_URL + "channels?part=contentDetails&forUsername={u}&key={key}".format(key=YouTube.API_KEY, u=username))
		playlist_id = response.json()["items"][0]["contentDetails"]["relatedPlaylists"][playlist_name]

		while running:

			# Make the Request
			url = YouTube.API_BASE_URL + "playlistItems?part=snippet"
			url += "&maxResults=" + str(block_size)
			url += "&playlistId=" + str(playlist_id)
			url += "&key=" + str(YouTube.API_KEY)

			if first:
				first = False
			else:
				url += "&pageToken=" + str(next_token)

			response = YouTube.rqst.get(url)
			if response.status_code != 200:
				raise Exception("Bad Response Status Code: " + str(response.status_code))

			response = response.json()

			# Get Next
			try:
				next_token = response["nextPageToken"]
			except KeyError:
				running = False
			except:
				raise

			# Save Details
			for item in response["items"]:

				tm = YouTube.__str2timestamp(item["snippet"]["publishedAt"])
				
				if before and tm > before:
					continue
				elif after and tm < after:
					running = False
					break

				title = item["snippet"]["title"]
				vid_id = item["snippet"]["resourceId"]["videoId"]
				big_list.append(YouTube.Video(title, tm, vid_id))

		return big_list


	# Converts YouTube's Time String into a UTC Timestamp
	def __str2timestamp(date_string):
		
		# Example date_string: "2021-07-15T14:12:16Z"
		date = date_string[:date_string.find("T")]
		time = date_string[date_string.find("T")+1:-1]

		year, month, day = date.split("-")
		hour, minute, second = time.split(":")

		return int(datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc).timestamp())