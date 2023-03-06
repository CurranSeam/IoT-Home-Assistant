import requests
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters

from application.services import svc_common
from application.services import security as vault
from application.services import sms_service

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

API_URL = "https://api.telegram.org/bot"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = svc_common.bot_greet_message()
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
    text = svc_common.get_detection_message(camera, timestamp, feed_url);
    allowed_chat_ids = svc_common.get_active_users_value("chat_id")

    for chat_id in allowed_chat_ids:
        params = {
            'chat_id' : chat_id,
            'caption' : text
        }

        response = request("post", "sendPhoto", params, file)

        if not response.ok:
            logging.error(f"Telegram ERROR: {response}")

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

    return response

def get(url, params, **__):
    return requests.get(url, params)

def post(url, params, files=None):
    return requests.post(url, params, files=files)

def invalid_method(*_, **__):
    bad_request = requests.Response()
    bad_request.status_code = 400
    return bad_request

def __white_listed_users():
    wl_users = filters.User()
    allowed_chat_ids = svc_common.get_active_users_value("chat_id")
    for chat_id in allowed_chat_ids:
        wl_users._add_chat_ids(int(chat_id))
    return wl_users
