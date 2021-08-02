import requests
import os
from math import ceil
from datetime import datetime
from datetime import timezone
import subprocess
import json


rqst = requests.session()
api_key = "AIzaSyAFqP5ih0-qMGFWuqeuERMT9JzZgA_QfZI"
api_base_url = "https://www.googleapis.com/youtube/v3/"



def get_uploads_id(username):
    response = rqst.get(
        api_base_url + "channels?part=contentDetails&forUsername={u}&key={key}".format(key=api_key, u=username))
    return response.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]




def get_videos(playlist_id, before=None, after=None):

    big_list = []
    running = True
    first = True

    while running:

        # Make the Request
        url = api_base_url + "playlistItems?part=snippet&maxResults=50"
        url += "&playlistId=" + str(playlist_id)
        url += "&key=" + str(api_key)

        if first:
            first = False
        else:
            url += "&pageToken=" + str(next_token)

        try:
            response = rqst.get(url)
            if response.status_code != 200:
                print("Code: " + str(response.status_code))
                raise Exception

            response = response.json()
        except:
            print("Bad Response")
            exit()

        # Get Next
        try:
            next_token = response["nextPageToken"]
        except KeyError:
            running = False
        except:
            running = False
            raise

        # Save Details
        for item in response["items"]:

            tm = str2timestamp(item["snippet"]["publishedAt"])
            if before and tm > before:
                running = False
                break
            elif after and tm < after:
                continue

            title = item["snippet"]["title"]
            vid_id = item["snippet"]["resourceId"]["videoId"]
            big_list.append((title, vid_id, tm))

    return big_list



def get_moist_meters(uploads):
    out = []
    mm_count = 0
    for title, id, date in uploads:
        if "Moist Meter: " in title or "Moist Meter | " in title:
            mm_count += 1
            title = title.replace("Moist Meter: ", "").replace(
                "Moist Meter | ", "")
            out.append((title, id, date))

    print("Found " + str(mm_count) + " Moist Meters")
    return out



def str2timestamp(date_string):
    # Example: "2021-07-15T14:12:16Z"

    date = date_string[:date_string.find("T")]
    time = date_string[date_string.find("T")+1:-1]

    year, month, day = date.split("-")
    hour, minute, second = time.split(":")

    return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc).timestamp()




def update_website():
    subprocess.check_output("ftp -s:update_index.txt ftpupload.net", shell=True)



def known(id):
    with open(".data.json", "r") as f:
        known = json.load(f)
        f.close()

    for item in known:
        if item["id"] == id:
            return True
    else:
        return False



def add_to_known(timestamp, title, id):
    value = {
        "date" : timestamp,
        "title" : title,
        "id" : id,
        "score" : "",
        "rated" : False
    }

    with open(".data.json", "r") as f:
        known = json.load(f)
        f.close()

    known.insert(0, value)
    with open(".data.json", "w") as f:
        json.dump(known, f, indent='\t', separators=(',',' : '))
        f.close()



def sort_known():
    pass



moist_meters = get_moist_meters(get_videos(get_uploads_id("penguinz0")))

for title, id, date in reversed(moist_meters):
    #print("\n" + title + "\n" + "-"*len(title))
    if known(id):
        continue

    add_to_known(date, title, id)
    

# update_website()