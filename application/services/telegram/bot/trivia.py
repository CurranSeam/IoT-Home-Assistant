import requests

from application.services import security as vault
from application.services import svc_common

from html import unescape
from random import shuffle

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def start(update, context):
    trivia_url = vault.get_value("EXTERNAL_API", "trivia", "url")
    response = requests.get(trivia_url)

    if response.status_code == 200:
        res = response.json()["results"][0]
        correct = unescape(res["correct_answer"])
        all_answers = [unescape(answer) for answer in res["incorrect_answers"]]
        all_answers.append(correct)
        shuffle(all_answers)

        await update.message.reply_text(unescape(res["question"]))
        await __display_trivia_buttons(update, context, correct, all_answers)
    else:
        error_msg = svc_common.get_bot_error_message()
        await update.message.reply_text(error_msg)

async def button_cb(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    _, answer, incorrect = callback_data.split("_")

    if not int(incorrect):
        msg = f"{answer} is correct! ✅"
    else:
        msg = f"Incorrect. ❌\n\nThe correct answer is {answer}."

    await context.bot.editMessageText(chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      text=msg, parse_mode="HTML")

async def __display_trivia_buttons(update, context, answer, options):
    buttons = []
    for choice in options:
        if choice == answer:
            button = InlineKeyboardButton(text=choice, callback_data=f"trivia_{choice}_0")
        else:
            button = InlineKeyboardButton(text=choice, callback_data=f"trivia_{answer}_-1")
        buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(text="Choices:", reply_markup=keyboard)
