import requests
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters

from application.services import common
from application.services import security as vault
from application.services import sms_service

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ALLOWED_CHAT_IDS = common.get_active_users_value("chat_id")
API_URL = "https://api.telegram.org/bot"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = common.bot_greet_message()
    gif = open("application/static/waving_dog.gif", 'rb')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif)

def start_bot():
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    application = ApplicationBuilder().token(bot_token).build()

    logging.info("Starting telegram bot...")

    commands = [start]
    for cmd in commands:
        application.add_handler(CommandHandler(cmd.__name__, cmd, __white_listed_users()))

    application.run_polling()

def send_detection_message(camera, timestamp, feed_url, img_filename):
    file = {'photo' : open(img_filename, 'rb')}
    text = common.get_detection_message(camera, timestamp, feed_url);

    for chat_id in ALLOWED_CHAT_IDS:
        params = {
            'chat_id' : chat_id,
            'caption' : text
        }

        status, _ = request("post", "sendPhoto", params, file)

        if status == "error":
            # Send SMS as a fallback option in case of an error.
            sms_service.send_message(camera, timestamp, feed_url, img_filename)

def request(method, endpoint, params, files):
    """
    Function to make requests to Telegram.

    params:
        method: 'post' or 'get' HTTP methods
        endpoint: Any Telegram API endpoint. i.e 'sendMessage'
        params: dict of url params
        files: dict of files
    """
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")

    url = f'{API_URL}{bot_token}/{endpoint}'

    response = {"post" : post,
                "get" : get
                }.get(method.lower(), invalid_method)(url, params, files=files)

    if response == "invalid HTTP method" or response.status_code != 200:
        logging.error(f"Telegram ERROR: {response}")
        return "error", response

    return "ok", response

def get(url, params, **__):
    return requests.get(url, params)

def post(url, params, files=None):
    return requests.get(url, params, files=files)

def invalid_method(*_, **__):
    return "invalid HTTP method"

def __white_listed_users():
    wl_users = filters.User()
    for chat_id in ALLOWED_CHAT_IDS:
        wl_users._add_chat_ids(int(chat_id))
    return wl_users
