from datetime import datetime, timezone
import requests
import json
import os



class YouTube():

	rqst = requests.session()
	API_BASE_URL = "https://www.googleapis.com/youtube/v3/"

	def __init__(self):
		with open(os.path.dirname(os.path.realpath(__file__)) + '/secrets.json', 'r') as file:
			self.API_KEY = json.load(file)["youtube_api_key"]
			file.close()


	# Returns a List of Every Video Uploaded by a Specific Youtuber
	def pull_uploads(self, username="penguinz0", before=None, after=None):
		return YouTube.get_videos_by_playlist(self, YouTube.get_playlist_id(self, username), before, after )


	# Get Playlist ID for a Specific Channel
	def get_playlist_id(self, username, playlist_name="uploads"):

		response = YouTube.rqst.get(YouTube.API_BASE_URL + "channels?part=contentDetails&forUsername={u}&key={key}".format(key=self.API_KEY, u=username))
		return response.json()["items"][0]["contentDetails"]["relatedPlaylists"][playlist_name]


	# Returns all of the Videos in a Given Playlist
	# Videos Represented by a Tuple with the Format: (title, video id, utc timestamp)
	def get_videos_by_playlist(self, playlist_id, before=None, after=None):

		if (before and (after > before)):
			raise Exception("In get_videos_by_playlist(): 'after' should not be greater then 'before'")

		big_list = []
		running = True
		first = True

		while running:

			# Make the Request
			url = YouTube.API_BASE_URL + "playlistItems?part=snippet&maxResults=50"
			url += "&playlistId=" + str(playlist_id)
			url += "&key=" + str(self.API_KEY)

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
				big_list.append((title, vid_id, tm))

		return big_list


	# Converts YouTube's Time String into a UTC Timestamp
	def __str2timestamp(date_string):
		# Example: "2021-07-15T14:12:16Z"

		date = date_string[:date_string.find("T")]
		time = date_string[date_string.find("T")+1:-1]

		year, month, day = date.split("-")
		hour, minute, second = time.split(":")

		return int(datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc).timestamp())