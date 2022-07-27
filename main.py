import pytube
import os

url = input("Input video url: ")

if not os.path.exists("Downloads"):
    os.mkdir("Downloads")

youtube = pytube.YouTube(url)

video = youtube.streams.get_highest_resolution()
# video = youtube.streams.get_by_resolution(resolution="720p")
video.download("Downloads")
