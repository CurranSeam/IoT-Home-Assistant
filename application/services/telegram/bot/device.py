from application.services import mqtt
from application.services import svc_common

from application.repository import user as User
from application.repository import device as Device

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

async def toggle(update, context):
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text=svc_common.get_bot_confirm_msg(),
                                  reply_to_message_id=update.message.message_id)

    await __prompt_user_for_device(update, context, "toggle")

async def status(update, context):
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text=svc_common.get_bot_confirm_msg(),
                                  reply_to_message_id=update.message.message_id)

    await __prompt_user_for_device(update, context, "status")

async def button_cb(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data

    _, function, device_id = callback_data.split("_")
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

async def __prompt_user_for_device(update, context, action):
    user = User.get_user(telegram_chat_id=update.effective_chat.id)

    buttons = []
    for device in user.devices:
        button = InlineKeyboardButton(text=device.name, callback_data=f"device_{action}_{device.id}")
        buttons.append([button])

    # Create an inline keyboard with the list of buttons
    keyboard = InlineKeyboardMarkup(buttons)

    # Send the message with the inline keyboard
    await context.bot.sendMessage(chat_id=update.effective_chat.id,
                                  text="Select a device:",
                                  reply_markup=keyboard)
