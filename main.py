import pytube
import os


def dl_from_list():
    links = []

    with open("links.txt") as f:
        lines = f.readlines()
        for line in lines:
            links.append(line.strip())
        print(f'Read {len(links)} link(s)')

    if not os.path.exists("Downloads"):
        os.mkdir("Downloads")

    for (i, link) in enumerate(links):
        youtube = pytube.YouTube(link)
        print(f'Download {i+1}/{len(links)}. {youtube.title}')
        video = youtube.streams.get_highest_resolution()
        # video = youtube.streams.get_by_resolution(resolution="720p")
        video.download("Downloads")

    return print("Downloaded")


def main():
    dl_from_list()


if __name__ == "__main__":
    main()
