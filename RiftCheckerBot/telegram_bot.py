import os
import json
import aiohttp
import asyncio
import random
import threading
import telebot
from io import BytesIO
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
from epic_auth import EpicUser, EpicGenerator, EpicEndpoints
from user import RiftUser
from cosmetic import FortniteCosmetic
from commands import command_start, command_help, command_login, command_style, command_badges, command_stats, send_style_message, send_badges_message, available_styles, avaliable_badges

import epic_auth
import cosmetic
import commands
import utils

# your telegram bot's api token
TELEGRAM_API_TOKEN = ""

# locker categories we render in the checker
telegram_bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

telegram_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Setup your user to start skinchecking."),
    telebot.types.BotCommand("/help", "Display Basic Info and the commands."),
    telebot.types.BotCommand("/login", "Skincheck your Epic Games account."),
    telebot.types.BotCommand("/badges", "Toggle your owned badges."),
    telebot.types.BotCommand("/stats", "View your stats.")
])

auth_code = None
@telegram_bot.message_handler(commands=['start'])
def handle_start(message):
    command_start(telegram_bot, message)

@telegram_bot.message_handler(commands=['help'])
def handle_help(message):
    command_help(telegram_bot, message)

@telegram_bot.message_handler(commands=['login'])
def handle_login(message):
    asyncio.run(command_login(telegram_bot, message))

@telegram_bot.message_handler(commands=['badges'])
def handle_badges(message):
    asyncio.run(command_badges(telegram_bot, message))
    
@telegram_bot.message_handler(commands=['stats'])
def handle_stats(message):
    asyncio.run(command_stats(telegram_bot, message))

@telegram_bot.callback_query_handler(func=lambda call: call.data.startswith("badge_") or call.data.startswith("toggle_"))
def handle_badge_navigation(call):
    data = call.data
    user = RiftUser(call.from_user.id, call.from_user.username)
    user_data = user.load_data()

    if not user_data:
        telegram_bot.reply_to(call.message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
    
    if data.startswith("badge_"):
        new_index = int(data.split("_")[1])
        telegram_bot.delete_message(call.message.chat.id, call.message.message_id)
        send_badges_message(telegram_bot, call.message.chat.id, new_index, user_data)

    elif data.startswith("toggle_"):
        badge_index = int(data.split("_")[1])
        badge = avaliable_badges[badge_index]
        current_status = user_data.get(badge['data2'], False)
        user_data[badge['data2']] = not current_status

        user.update_data()
        telegram_bot.answer_callback_query(call.id, f"{badge['name']} is now {'Enabled' if not current_status else 'Disabled'}!")
        telegram_bot.delete_message(call.message.chat.id, call.message.message_id)
        send_badges_message(telegram_bot, call.message.chat.id, badge_index, user_data)

print("starting rift checker...")          
if __name__ == '__main__':
    telegram_bot.infinity_polling()