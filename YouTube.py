from datetime import datetime, timezone
import requests
import json
import time
import os



class YouTube():

	rqst = requests.session()
	API_BASE_URL = "https://www.googleapis.com/youtube/v3/"

	def __init__(self):
		file = open(os.path.dirname(os.path.realpath(__file__)) + '/secrets.json', 'r')
		if file.readable:
			YouTube.API_KEY = json.load(file)["youtube_api_key"]
			file.close()
		else:
			raise Exception("Failed to Read secrets.json")


	# Returns a List of Every Video Uploaded by a Specific Youtuber
	def pull_uploads(username="penguinz0", before=None, after=None):

		window =  (before if before else time.time())
		window -= (after if after else 0)

		max_extries = 50
		if window < 3600 * 8:
			max_extries = 3
		elif window < 3600 * 24 * 7:
			max_extries = 20

		return YouTube.get_videos_by_playlist(YouTube.get_playlist_id(username), before, after, max_extries)


	# Get Playlist ID for a Specific Channel
	def get_playlist_id(username, playlist_name="uploads"):

		print(YouTube.API_BASE_URL + "channels?part=contentDetails&forUsername={u}&key={key}".format(key=YouTube.API_KEY, u=username))
		response = YouTube.rqst.get(YouTube.API_BASE_URL + "channels?part=contentDetails&forUsername={u}&key={key}".format(key=YouTube.API_KEY, u=username))
		return response.json()["items"][0]["contentDetails"]["relatedPlaylists"][playlist_name]


	# Returns all of the Videos in a Given Playlist
	# Videos Represented by a Tuple with the Format: (title, video id, utc timestamp)
	def get_videos_by_playlist(playlist_id, before=None, after=None, block_size=20):

		if (before and (after > before)):
			raise Exception("In get_videos_by_playlist(): 'after' should not be greater then 'before'")

		big_list = []
		running = True
		first = True

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

			print(url)
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

		print()
		return big_list


	# Converts YouTube's Time String into a UTC Timestamp
	def __str2timestamp(date_string):
		# Example: "2021-07-15T14:12:16Z"

		date = date_string[:date_string.find("T")]
		time = date_string[date_string.find("T")+1:-1]

		year, month, day = date.split("-")
		hour, minute, second = time.split(":")

		return int(datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc).timestamp())