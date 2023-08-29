from email import message
from os import getenv
# from async_main import collect_data
from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher.filters import Text
from aiofiles import os
import pytube
import config
import os
import ffmpeg
bot = Bot(token=config.token)
dp = Dispatcher(bot)


@dp.message_handler(commands='start')
async def start(message: types.Message):
    # start_buttons = ['Download video']
    # keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # keyboard.add(*start_buttons)
    # await message.answer('Hello', reply_markup=keyboard)
    await message.answer("Hello! Just send me link like '/link https://'")


@dp.message_handler(commands='link')
async def link(message: types.Message):
    await message.answer('Please waiting...')
    chat_id = message.chat.id
    link = message.text.split(" ")[1]
    await send_data(link=link, chat_id=chat_id)


async def dl_from_link(link, chat_id):
    youtube = pytube.YouTube(link)
    print(f'Download {youtube.title}')
    await bot.send_message(chat_id=chat_id, text=f'Downloading {youtube.title}')
    video = youtube.streams.get_highest_resolution()
    video.download(filename=f'{youtube.title}.mp4', output_path="Downloads")
    file = f"Downloads/{youtube.title}.mp4"
    return file


async def dl_low_res(link):
    youtube = pytube.YouTube(link)
    video = youtube.streams.get_by_resolution('480p')
    video.download(filename=f'{youtube.title}.mp4', output_path="Downloads")
    file = f"Downloads/{youtube.title}.mp4"
    return file


async def send_data(link, chat_id):
    file = await dl_from_link(link, chat_id)
    try:
        if os.path.getsize(file) >= 50000000:
            low_res_file = await dl_low_res(link)
            if os.path.getsize(low_res_file) >= 50000000:
                print('File to big. Converting.')
                await bot.send_message(chat_id=chat_id, text="File to big. Converting.")
                new_file = await compress_video(file, 49 * 1000)
                await bot.send_document(chat_id=chat_id, document=open(new_file, 'rb'))
        else:
            await bot.send_document(chat_id=chat_id, document=open(file, 'rb'))
    except utils.exceptions.NetworkError:
        print("NetworkError")
        await bot.send_message(chat_id=chat_id, text="NetworkError. File to big.")
        
    # await bot.send_video(chat_id=chat_id, video=open(file, 'rb'))
    # video send with bugs


async def compress_video(video_full_path, size_upper_bound, two_pass=True, filename_suffix='cps_'):
    """
    Compress video file to max-supported size.
    :param video_full_path: the video you want to compress.
    :param size_upper_bound: Max video size in KB.
    :param two_pass: Set to True to enable two-pass calculation.
    :param filename_suffix: Add a suffix for new video.
    :return: out_put_name or error
    """
    filename, extension = os.path.splitext(video_full_path)
    extension = '.mp4'
    output_file_name = filename + filename_suffix + extension

    # Adjust them to meet your minimum requirements (in bps), or maybe this function will refuse your video!
    total_bitrate_lower_bound = 11000
    min_audio_bitrate = 32000
    max_audio_bitrate = 256000
    min_video_bitrate = 100000

    try:
        # Bitrate reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
        probe = ffmpeg.probe(video_full_path)
        # Video duration, in s.
        duration = float(probe['format']['duration'])
        # Audio bitrate, in bps.
        audio_bitrate = float(next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])
        # Target total bitrate, in bps.
        target_total_bitrate = (size_upper_bound * 1024 * 8) / (1.073741824 * duration)
        if target_total_bitrate < total_bitrate_lower_bound:
            print('Bitrate is extremely low! Stop compress!')
            return False

        # Best min size, in kB.
        best_min_size = (min_audio_bitrate + min_video_bitrate) * (1.073741824 * duration) / (8 * 1024)
        if size_upper_bound < best_min_size:
            print('Quality not good! Recommended minimum size:', '{:,}'.format(int(best_min_size)), 'KB.')
            # return False

        # Target audio bitrate, in bps.
        audio_bitrate = audio_bitrate

        # target audio bitrate, in bps
        if 10 * audio_bitrate > target_total_bitrate:
            audio_bitrate = target_total_bitrate / 10
            if audio_bitrate < min_audio_bitrate < target_total_bitrate:
                audio_bitrate = min_audio_bitrate
            elif audio_bitrate > max_audio_bitrate:
                audio_bitrate = max_audio_bitrate

        # Target video bitrate, in bps.
        video_bitrate = target_total_bitrate - audio_bitrate
        if video_bitrate < 1000:
            print('Bitrate {} is extremely low! Stop compress.'.format(video_bitrate))
            return False

        i = ffmpeg.input(video_full_path)
        if two_pass:
            ffmpeg.output(i, os.devnull,
                          **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
                          ).overwrite_output().run()
            ffmpeg.output(i, output_file_name,
                          **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac', 'b:a': audio_bitrate}
                          ).overwrite_output().run()
        else:
            ffmpeg.output(i, output_file_name,
                          **{'c:v': 'libx264', 'b:v': video_bitrate, 'c:a': 'aac', 'b:a': audio_bitrate}
                          ).overwrite_output().run()

        if os.path.getsize(output_file_name) <= size_upper_bound * 1024:
            return output_file_name
        elif os.path.getsize(output_file_name) < os.path.getsize(video_full_path):  # Do it again
            return compress_video(output_file_name, size_upper_bound)
        else:
            return False
    except FileNotFoundError as e:
        print('You do not have ffmpeg installed!', e)
        print('You can install ffmpeg by reading https://github.com/kkroening/ffmpeg-python/issues/251')
        return False


if __name__ == '__main__':
    executor.start_polling(dp)
