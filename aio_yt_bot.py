from os import getenv
# from async_main import collect_data
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import Text
from aiofiles import os
import pytube
import config

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


async def dl_from_link(link):
    youtube = pytube.YouTube(link)
    print(f'Download {youtube.title}')
    video = youtube.streams.get_highest_resolution()
    video.download(filename=f'{youtube.title}.mp4', output_path="Downloads")
    file = f"Downloads/{youtube.title}.mp4"
    return file


async def send_data(link, chat_id):
    file = await dl_from_link(link)
    await bot.send_document(chat_id=chat_id, document=open(file, 'rb'))
    # await bot.send_video(chat_id=chat_id, video=open(file, 'rb'))
    # video send with bugs


if __name__ == '__main__':
    executor.start_polling(dp)
