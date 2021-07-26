import requests
import os
import speech_recognition as sr
import scipy
from scipy.io import wavfile
from math import ceil
from datetime import datetime
from datetime import timezone
import subprocess
import json

r = sr.Recognizer()
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

"""
def url2wav(video_id):
    print("Downloading Video...")
    os.system(
        "youtube-dl --id --quiet --geo-bypass -f mp4 https://www.youtube.com/watch?v={id}".format(id=video_id))
    #os.system("youtube-dl --id https://www.youtube.com/watch?v={id}".format(id=video_id))
    print("Converting to WAV...")
    os.system(
        "ffmpeg -y -hide_banner -loglevel error -i ./{id}.mp4 -ac 2 -f wav ./{id}.wav".format(id=video_id))


def clean_up(video_id):
    os.system("del /q {id}.*".format(id=video_id))


def to_number(text_block):
    ONES = {"one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
    TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
             "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "hundred": 100, "zero": 0}
    TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
            "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}

    out = None
    text_block = text_block.strip()
    #print("Got Block: " + str(text_block))
    while 1:
        index = text_block.rfind(" ")
        word = text_block[index+1:]
        # print(word)
        text_block = text_block[:index]

        if word in TEENS:
            return TEENS[word]
        elif word in TENS:
            return (out + TENS[word]) if out else (TENS[word])
        elif word in ONES:
            out = ONES[word]
        else:
            return out


def parse_wav(filename, block_size=None):

    with sr.AudioFile(filename) as source:
        audio_text = r.listen(source)
        dur = source.DURATION

    if block_size:
        iterations = ceil(dur / block_size)

        for i in reversed(range(iterations)):
            end_t = ((i+1)*1000*block_size) if i+1 != iterations else None
            print("Scanning Clip: " + str(i*block_size) + "s - " + (str(end_t/1000) + "s" if end_t else "End"))

            audio_clip = audio_text.get_segment(
                start_ms=(i*1000*block_size), end_ms=end_t)
            text = get_text(audio_clip)
            if has_percent(text):
                return has_percent(text)

    print("All Failed: Scanning Whole Clip")
    text = get_text(audio_text)
    if has_percent(text):
        return has_percent(text)
    else:
        return None


def has_percent(text):
    if "percent" in text:
        #print("found percent")
        index = text.rfind("percent")
        return text[:index - 1]
    else:
        return None


def get_text(audio_data):

    try:
        text = r.recognize_sphinx(audio_data)
        return text

    except BaseException as err:
        print(err)
        return ""


def str2timestamp(date_string):
    # Example: "2021-07-15T14:12:16Z"

    date = date_string[:date_string.find("T")]
    time = date_string[date_string.find("T")+1:-1]

    year, month, day = date.split("-")
    hour, minute, second = time.split(":")

    return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), tzinfo=timezone.utc).timestamp()

def insert_row(number, date, title, id, rating):

    with open("index.html", "r") as f:
        contents = f.readlines()
        f.close()
    
    index = None
    for i, line in enumerate(contents):
        if "<tbody>" in line:
            index = i+1
            break
    
    for i, line in enumerate(contents):
        if "id=\"last_update\"" in line:
            last_time = line[ line.find("Last Updated: ")+14 : line.rfind("<") ]
            contents[i] = line.replace(last_time, datetime.utcnow().strftime("%A, %B %d, %Y"))
            break
    
    T = "\t\t\t"
    row =  T + "<tr>\n"
    row += T + "\t<td>" + str(number) + "</td>\n"
    row += T + "\t<td>" + datetime.utcfromtimestamp(date).strftime("%m/%d/%y") + "</td>\n"
    row += T + "\t<td>" + str(title) + "%%%" + str(id) + "</td>\n"
    row += T + "\t<td>" + str(rating) + "%</td>\n"
    row += T +"</tr>\n"
    contents.insert(index, row)

    f = open("index.html", "w")
    temp = "".join(contents)
    f.write(temp)
    f.close()

"""

def update_website():
    subprocess.check_output("ftp -s:update_index.txt ftpupload.net", shell=True)



def known(id):
    with open("known.json", "r") as f:
        known = json.load(f)
        f.close()

    for item in known:
        if item["id"] == id:
            return True
    else:
        return False



def add_to_known(title, id):
    value = {
        "title" : title,
        "id" : id,
        "verified" : False
    }

    with open("known.json", "r") as f:
        known = json.load(f)
        f.close()

    known.insert(0, value)
    with open("known.json", "w") as f:
        json.dump(known, f, indent='\t', separators=(',',' : '))

        f.close()
    return len(known)

update_website()
exit()

moist_meters = get_moist_meters(get_videos(
    get_uploads_id("penguinz0")))
for title, id, date in reversed(moist_meters):
    print("\n" + title + "\n" + "-"*len(title))
    if known(id):
        print("Already Scanned")
        continue
    
    """
    try:
        url2wav(id)
        text = parse_wav(str(id)+".wav", 60)
        clean_up(id)
    except KeyboardInterrupt:
        break
    except BaseException as err:
        print(err)
        continue

    rating = -1
    if text:
        rating = str(to_number(text))
        print("Mr. Moist Gave it " + rating + "%")
    else:
        print("Coudln't Find Rating")
    """
    rating = -1
    num = add_to_known(title, id)
    #insert_row(num, date, title, id, rating)

update_website()