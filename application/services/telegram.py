import requests
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, ContextTypes, CommandHandler,
                          filters, CallbackContext, CallbackQueryHandler)

from application.services import svc_common
from application.services import security as vault
from application.services import sms_service
from application.services import mqtt
from application.utils.exception_handler import try_exec
from application.repository import user as User
from application.repository import device as Device

# Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = svc_common.get_bot_greet_msg()
    gif = open("application/static/waving_dog.gif", 'rb')
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_msg = "<strong>" + svc_common.get_bot_stats_msg() + "</strong>"
    stats = svc_common.get_server_stats(False)
    msg = """{}\n\n{}""".format(bot_msg, stats)

    await context.bot.sendMessage(chat_id=update.effective_chat.id, 
                                  text=svc_common.get_bot_confirm_msg(), 
                                  reply_to_message_id=update.message.message_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="HTML")

async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text=svc_common.get_bot_confirm_msg(),
                                  reply_to_message_id=update.message.message_id)

    await __prompt_user_for_device(update, context, "toggle")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text=svc_common.get_bot_confirm_msg(),
                                  reply_to_message_id=update.message.message_id)

    await __prompt_user_for_device(update, context, "status")

# Utility functions
def start_bot():
    bot_token = vault.get_value("EXTERNAL_API", "telegram", "token")
    application = ApplicationBuilder().token(bot_token).build()

    logging.info("Starting telegram bot...")

    commands = [start, stats, toggle, status]
    for func in commands:
        application.add_handler(CommandHandler(func.__name__, func, __white_listed_users()))

    # Add the callback for device buttons
    application.add_handler(CallbackQueryHandler(__devices_button_cb))

    application.run_polling()

def send_detection_message(camera, timestamp, feed_url, img_filename):
    file = {'photo' : open(img_filename, 'rb')}
    feed_url = f"<a href='{feed_url}'>Feed</a>"
    text = svc_common.get_detection_message(camera, timestamp, feed_url);
    active_chat_ids = User.get_telegram_chat_ids(active=1)

    for chat_id in active_chat_ids:
        params = {
            'chat_id' : chat_id,
            'caption' : text,
            'parse_mode' : "HTML"
        }

        response = request("post", "sendPhoto", params, file)

        try_exec(__handle_error, response, sms_service.send_detection_message, camera, timestamp, chat_id)
 
def send_opt_message(user, opt_in, service, settings_url):
    settings_url = f"<a href='{settings_url}'>Settings</a>"
    text = svc_common.get_opt_message(user, opt_in, service, settings_url)

    chat_id = User.get_telegram_chat_id(user)

    params = {
        'chat_id' : chat_id,
        'text' : text,
        'parse_mode' : "HTML"
    }

    response = request("post", "sendMessage", params)

    try_exec(__handle_error, response, sms_service.send_opt_message, user, opt_in, service)

def request(method, endpoint, params, files=None):
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
    return requests.post(url, params, files=files)

def __invalid_method(*_, **__):
    bad_request = requests.Response()
    bad_request.status_code = 400
    return bad_request

def __white_listed_users():
    wl_users = filters.User()
    allowed_chat_ids = User.get_telegram_chat_ids()
    for chat_id in allowed_chat_ids:
        if chat_id is not None:
            wl_users._add_chat_ids(chat_id)
    return wl_users

async def __prompt_user_for_device(update, context, action):
    user = User.get_user(telegram_chat_id=update.effective_chat.id)

    buttons = []
    for device in user.devices:
        button = InlineKeyboardButton(text=device.name, callback_data=f"{action}_{device.id}")
        buttons.append([button])

    # Create an inline keyboard with the list of buttons
    keyboard = InlineKeyboardMarkup(buttons)

    # Send the message with the inline keyboard
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text="Select a device:",
                                  reply_markup=keyboard)

# Callbacks
async def __devices_button_cb(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    function, device_id = callback_data.split("_")
    device = Device.get_device(id=device_id)

    # Dispatch action for the selected device via MQTT protocol.
    # When new device commands are added, add the dispatch here.
    dispatch = {
        "toggle" : [mqtt.power_toggle, f'{device.name} toggled!'],
        "status" : [lambda device: device.status,
                    f'<strong>Here are the stats for {device.name}</strong>:']
    }.get(function.lower())

    data = dispatch[0](device)

    # Relay data to user if any
    msg = dispatch[1] + "\n\n" + data if data else dispatch[1]

    # Edit the message to remove the inline keyboard
    await context.bot.editMessageText(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=msg, parse_mode="HTML")

# Error handling
def __handle_error(response, func, *args):
    if not response.ok:
        # Send SMS as a fallback option in case of an error.
        func(*args)

        # Raise exception for exception handler.
        raise Exception(f"HTTPError: {response}")
