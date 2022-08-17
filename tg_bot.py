import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def down_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Give me yotube video link')

if __name__ == '__main__':
    application = ApplicationBuilder().token(config.token).build()

    start_handler = CommandHandler('start', start)
    link_handler = CommandHandler('link', down_video)

    application.add_handler(start_handler)
    application.add_handler(link_handler)

    application.run_polling()
