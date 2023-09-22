import requests
import time

from application.services import security as vault
from application.services import svc_common

from html import unescape
from random import shuffle

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def start(update):
    is_online, response = await __request(update, "api_category")

    if is_online:
        categories = response.json()["trivia_categories"]

        await update.message.reply_text("Lets play Trivia!")
        time.sleep(1)
        await __display_category_buttons(update, categories)

async def run_trivia(update, context, difficulty, category_id):
    params = {
        "amount" : 1,
        "category" : category_id,
        "difficulty" : difficulty,
        "type" : "multiple"
    }

    is_online, response = await __request(update, "api", params)

    if is_online:
        res = response.json()["results"][0]
        correct = unescape(res["correct_answer"])
        all_answers = [unescape(answer) for answer in res["incorrect_answers"]]
        all_answers.append(correct)
        shuffle(all_answers)

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=unescape(res["question"]))
        await __display_multiple_choice_buttons(update, context, correct, all_answers)

async def configuration_buttons_cb(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    setting, data, category_id = callback_data.split("_")
    message = ""

    if (setting.endswith("c")):
        await __display_difficulty_buttons(update, context, category_id)
        message = f"Category - {data}"
    else:
        await run_trivia(update, context, data.lower(), category_id)
        message = f"Difficulty - {data}"

    await context.bot.editMessageText(chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=message, parse_mode="HTML")

async def multiple_choice_buttons_cb(update: Update, context: CallbackContext):
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

async def __display_category_buttons(update, categories):
    buttons = []
    for category in categories:
        category_name = category["name"]
        category_id = category["id"]

        button = InlineKeyboardButton(text=category_name, callback_data=f"trivia-c_{category_name}_{category_id}")
        buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(text="Pick a category:", reply_markup=keyboard)

async def __display_difficulty_buttons(update, context, category_id):
    difficulties = ["Easy", "Medium", "Hard"]
    buttons = []
    for difficulty in difficulties:
        button = InlineKeyboardButton(text=difficulty, callback_data=f"trivia-d_{difficulty}_{category_id}")
        buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Select a difficulty:",
                                   reply_markup=keyboard)

async def __display_multiple_choice_buttons(update, context, answer, options):
    buttons = []
    for choice in options:
        if choice == answer:
            button = InlineKeyboardButton(text=choice, callback_data=f"trivia_{choice}_0")
        else:
            button = InlineKeyboardButton(text=choice, callback_data=f"trivia_{answer}_-1")
        buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Choices:", reply_markup=keyboard)

async def __request(update, endpoint, params=None):
    """
    Makes a request to the trivia api

    :param endpoint: trivia api endpoint.
    :param params: a dict of params to send in the request.
    """
    base_url = vault.get_value("EXTERNAL_API", "trivia", "url")
    url = f"{base_url}/{endpoint}.php"

    response = requests.get(url, params)

    if response.status_code == 200:
        return True, response
    else:
        error_msg = svc_common.get_bot_error_message()
        await update.message.reply_text(error_msg)
        return False
