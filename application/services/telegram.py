import requests
import logging
import socket

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters

from application.services import svc_common
from application.services import security as vault
from application.services import sms_service

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = svc_common.get_bot_greet_msg()
    gif = open("application/static/waving_dog.gif", 'rb')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_msg = "<strong>" + svc_common.get_bot_stats_msg() + "</strong>"

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    host = s.getsockname()[0]
    port = vault.get_value("app", "config", "port")

    stats_url = f'http://{host}:{port}/get_stats?snapshot'
    stats = (requests.get(stats_url).content).decode("utf-8")
    msg = """{}\n\n{}""".format(bot_msg, stats)

    await context.bot.sendMessage(chat_id=update.effective_chat.id, 
                                  text=svc_common.get_bot_confirm_msg(), 
                                  reply_to_message_id=update.message.message_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="HTML")

def start_bot():
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    application = ApplicationBuilder().token(bot_token).build()

    logging.info("Starting telegram bot...")

    commands = [start, stats]
    for func in commands:
        application.add_handler(CommandHandler(func.__name__, func, __white_listed_users()))

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
            # Send SMS as a fallback option in case of an error.
            sms_service.send_message(camera, timestamp, feed_url, img_filename)

            raise requests.HTTPError(response=response)

def request(method, endpoint, params, files):
    """
    Function to make requests to Telegram's bot API.

    params:
        method: 'post' or 'get' HTTP methods
        endpoint: Any Telegram bot API endpoint. i.e 'sendMessage'
        params: dict of url params
        files: dict of files
    """
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    api_url = vault.get_value("external_api", "telegram", "url")
    url = f'{api_url}{bot_token}/{endpoint}'

    response = {"post" : __post,
                "get" : __get
                }.get(method.lower(), __invalid_method)(url, params, files=files)

    return response

def __get(url, params, **__):
    return requests.get(url, params)

def __post(url, params, files=None):
    return requests.post(url, params, files=files)

def __invalid_method(*_, **__):
    bad_request = requests.Response()
    bad_request.status_code = 400
    return bad_request

def __white_listed_users():
    wl_users = filters.User()
    allowed_chat_ids = svc_common.get_active_users_value("chat_id")
    for chat_id in allowed_chat_ids:
        wl_users._add_chat_ids(int(chat_id))
    return wl_users
