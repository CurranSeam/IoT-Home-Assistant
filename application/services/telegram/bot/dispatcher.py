import hashlib
import requests

from telegram import Update
from telegram.ext import ContextTypes

from application.services import svc_common
from application.services import security as vault

from application.services.telegram.bot import device as Device
from application.services.telegram.bot import trivia as Trivia

from application.repository import user as User

from application.utils.exception_handler import log_exception
from functools import wraps

def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in User.get_telegram_chat_ids():
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        params = update.message.text.split(" ")[1].split("-")
        value = params[0]
        hash_data = params[1]

        tg_identity = vault.get_value_encrypted("APP", "config", "telegram_identity")
        hash_object = hashlib.sha1(tg_identity)
        hash_data_new = hash_object.hexdigest()

        if (hash_data_new == hash_data):
            if (value == "g"):
                msg = svc_common.get_bot_greet_msg()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
                return

            msg = svc_common.get_bot_welcome_msg()
            gif = open("application/static/waving_dog.gif", 'rb')

            User.update_telegram_chat_id(value, update.effective_chat.id)

            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            await context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif)
    except Exception:
        data = f'Error in /start command\nTelegram update: {update.message.from_user}'
        log_exception(data)
        return

@restricted
async def toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await Device.toggle(update, context)

@restricted
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await Device.status(update, context)

@restricted
async def trivia(update: Update, _):
    await Trivia.start(update)

@restricted
async def server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_msg = "<strong>" + svc_common.get_bot_stats_msg() + "</strong>"
    stats = svc_common.get_server_stats(False)
    msg = """{}\n\n{}""".format(bot_msg, stats)

    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text=svc_common.get_bot_confirm_msg(),
                                  reply_to_message_id=update.message.message_id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="HTML")

@restricted
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joke = get_joke()

    if len(joke) > 0:
        await update.message.reply_text(joke)
    else:
        error_msg = svc_common.get_bot_error_message()
        await update.message.reply_text(error_msg)

@restricted
async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fact_url = vault.get_value("EXTERNAL_API", "fact", "url")
    response = requests.get(fact_url)

    if response.status_code == 200:
        fact = response.json()["text"]
        await update.message.reply_text(f"Did you know?\n\n{fact}")
    else:
        error_msg = svc_common.get_bot_error_message()
        await update.message.reply_text(error_msg)

def get_joke():
    joke_url = vault.get_value("EXTERNAL_API", "joke", "url")
    response = requests.get(joke_url)
    joke_parts = ""

    if response.status_code == 200:
        data = response.json()
        joke_parts = f"{data['setup']}\n\n{data['punchline']}"

    return joke_parts
