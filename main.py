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


def dl_from_link():
    link = input('Input link: ')
    youtube = pytube.YouTube(link)
    print(f'Download {youtube.title}')
    video = youtube.streams.get_highest_resolution()
    video.download("Downloads")

    return print("Downloaded")


def main():
    print("---YouTube downloader---\n1. Download from list\n2. Download from link\n0. Exit")
    ch = int(input('Input number: '))
    if ch == 1:
        dl_from_list()
    elif ch == 2:
        dl_from_link()
    elif ch == 0:
        print('Exit')
        exit()
    else:
        print("Wrong choice!")
        exit()


if __name__ == "__main__":
    main()
