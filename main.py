import pytube
import os


def dl_from_list():
    links = []

    with open("links.txt") as f:
        lines = f.readlines()
        for line in lines:
            links.append(line.strip())

    if not os.path.exists("Downloads"):
        os.mkdir("Downloads")

    for link in links:
        youtube = pytube.YouTube(link)
        video = youtube.streams.get_highest_resolution()
        # video = youtube.streams.get_by_resolution(resolution="720p")
        video.download("Downloads")

    return print("Downloaded")


def main():
    dl_from_list()


if __name__ == "__main__":
    main()
