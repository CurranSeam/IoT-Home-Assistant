import hashlib
import logging
import requests
import json

from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler)

from application.services import svc_common
from application.services import security as vault
from application.services import sms_service

from application.services.telegram.bot import dispatcher
from application.services.telegram.bot import device
from application.services.telegram.bot import trivia as Trivia

from application.repository import user as User

from application.utils.exception_handler import try_exec

# Utility functions
def start_bot():
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    application = ApplicationBuilder().token(bot_token).build()

    logging.info("Starting telegram bot...")
    moniker = vault.get_value("APP", "config", "moniker")

    # Add new bot commands here
    commands = {
        dispatcher.server : f"Get {moniker}Net server stats",
        dispatcher.toggle : "Toggle your device power",
        dispatcher.status : "Get your device status",
        dispatcher.joke : f"Get {moniker}Bot to tell you a joke",
        dispatcher.fact : f"Get {moniker}bot to tell you a fact",
        dispatcher.trivia : f"Play trivia with {moniker}Bot"
    }

    bot_commands = []

    for func in commands:
        application.add_handler(CommandHandler(func.__name__, func))
        bot_commands.append({'command' : func.__name__, 'description' : commands[func]})

    request("post", "setMyCommands", {"commands" : json.dumps(bot_commands)})

    # Add the callbacks for buttons
    application.add_handler(CallbackQueryHandler(device.button_cb, pattern='^device_'))
    application.add_handler(CallbackQueryHandler(Trivia.multiple_choice_buttons_cb, pattern='^trivia_'))
    application.add_handler(CallbackQueryHandler(Trivia.configuration_buttons_cb, pattern='^trivia-'))

    application.run_polling()

def send_detection_message(camera, timestamp, feed_url, img_filename):
    file = {'photo' : open(img_filename, 'rb')}
    feed_url = f"<a href='{feed_url}'>Feed</a>"
    text = svc_common.get_detection_message(camera, timestamp, feed_url)
    active_chat_ids = User.get_telegram_chat_ids(active=1)

    for chat_id in active_chat_ids:
        params = {
            'chat_id' : chat_id,
            'caption' : text,
            'parse_mode' : "HTML"
        }

        response = request("post", "sendPhoto", params, file)

        try_exec(__handle_error, response, sms_service.send_detection_message, camera, timestamp, chat_id)

def send_opt_message(user_id, user_first_name, opt_in, service, settings_url):
    settings_url = f"<a href='{settings_url}'>Settings</a>"
    text = svc_common.get_opt_message(user_first_name, opt_in, service, settings_url)

    chat_id = User.get_telegram_chat_id(user_id)

    if chat_id:
        params = {
            'chat_id' : chat_id,
            'text' : text,
            'parse_mode' : "HTML"
        }

        response = request("post", "sendMessage", params)
        try_exec(__handle_error, response, sms_service.send_opt_message, user_id, user_first_name, opt_in, service)

    else:
        sms_service.send_opt_message(user_id, user_first_name, opt_in, service)

def send_reminder(user_id, message):
    chat_id = User.get_telegram_chat_id(user_id)
    modified_msg = "<strong>Reminder!</strong>\n\n" + message

    params = {
        'chat_id' : chat_id,
        'text' : modified_msg,
        'parse_mode' : "HTML"
    }

    response = request("post", "sendMessage", params)

    recipient = User.get_phone_number(chat_id, 1)
    try_exec(__handle_error, response, sms_service.send_message, message, recipient)

def send_morning_message():
    active_chat_ids = User.get_telegram_chat_ids(active=1)
    joke = dispatcher.get_joke()

    for chat_id in active_chat_ids:
        user = User.get_user(telegram_chat_id=chat_id)
        message = "<strong>" + svc_common.get_bot_morning_msg(user.first_name) + "</strong>"

        if len(joke) > 0:
            message = f"{message}\n\n{joke}"

        params = {
            'chat_id' : chat_id,
            'text' : message,
            'parse_mode' : "HTML"
        }

        request("post", "sendMessage", params)

def request(method, endpoint, params=None, files=None):
    """
    Function to make requests to Telegram's bot API.

    params:
        method: 'post' or 'get' HTTP methods
        endpoint: Any Telegram bot API endpoint. i.e 'sendMessage'
        params: dict of url params
        files: dict of files
    """
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    api_url = vault.get_value("EXTERNAL_API", "telegram", "url")
    url = f'{api_url}{bot_token}/{endpoint}'

    response = {"post" : __post,
                "get" : __get
                }.get(method.lower(), __invalid_method)(url, params, files=files)

    return response

def __get(url, params, **__):
    return requests.get(url, params)

def __post(url, params, files=None):
    return requests.post(url, params=params, files=files)

def __invalid_method(*_, **__):
    bad_request = requests.Response()
    bad_request.status_code = 400
    return bad_request

# Error handling
def __handle_error(response, func, *args):
    if not response.ok:
        # Send SMS as a fallback option in case of an error.
        func(*args)

        # Raise exception for exception handler.
        raise Exception(f"HTTPError: {response}")
