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
from dotenv import load_dotenv

# Local imports
from epic_auth import EpicUser, EpicGenerator, EpicEndpoints
from user import RiftUser
from cosmetic import FortniteCosmetic
from commands import (
    command_start, command_help, command_login, command_style, command_badges, command_stats,
    send_style_message, send_badges_message, available_styles, avaliable_badges
)

# Load environment variables from .env file
load_dotenv()

# Get the Telegram bot token from .env
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Initialize the bot
telegram_bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

# Set bot commands
telegram_bot.set_my_commands([
    telebot.types.BotCommand("/start", "Setup your user to start skinchecking."),
    telebot.types.BotCommand("/help", "Display Basic Info and the commands."),
    telebot.types.BotCommand("/login", "Skincheck your Epic Games account."),
    telebot.types.BotCommand("/style", "Customize your checker's style."),
    telebot.types.BotCommand("/userpaint", "Customize your username color."),
    telebot.types.BotCommand("/badges", "Toggle your owned badges."),
    telebot.types.BotCommand("/stats", "View your stats.")
])

# Command handlers
@telegram_bot.message_handler(commands=['start'])
def handle_start(message):
    command_start(telegram_bot, message)

@telegram_bot.message_handler(commands=['help'])
def handle_help(message):
    command_help(telegram_bot, message)

import asyncio

@telegram_bot.message_handler(commands=['login'])
def handle_login(message):
    # Run the async function in a new event loop
    asyncio.run(command_login(telegram_bot, message))

@telegram_bot.message_handler(commands=['style'])
def handle_style(message):
    asyncio.run(command_style(telegram_bot, message))

@telegram_bot.message_handler(commands=['badges'])
def handle_badges(message):
    asyncio.run(command_badges(telegram_bot, message))

@telegram_bot.message_handler(commands=['stats'])
def handle_stats(message):
    asyncio.run(command_stats(telegram_bot, message))

@telegram_bot.message_handler(commands=['userpaint'])
def handle_userpaint(message):
    user = RiftUser(message.from_user.id, message.from_user.username)
    user_data = user.load_data()
    if not user_data:
        telegram_bot.reply_to(message, "You haven't setup your user yet, please use /start before using this command!")
        return

    # Create a keyboard with color options
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🌈 Rainbow", callback_data="color_rainbow"))
    markup.add(InlineKeyboardButton("🔵 Blue", callback_data="color_blue"))
    markup.add(InlineKeyboardButton("🟡 Yellow", callback_data="color_yellow"))
    markup.add(InlineKeyboardButton("🟢 Green", callback_data="color_green"))
    markup.add(InlineKeyboardButton("🟣 Purple", callback_data="color_purple"))
    markup.add(InlineKeyboardButton("⚪ Default (White)", callback_data="color_default"))

    telegram_bot.reply_to(message, "🎨 Select a color for your username:", reply_markup=markup)

@telegram_bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
def handle_color_selection(call):
    user = RiftUser(call.from_user.id, call.from_user.username)
    user_data = user.load_data()
    if not user_data:
        telegram_bot.answer_callback_query(call.id, "You haven't setup your user yet, please use /start before using this command!")
        return

    # Map callback data to gradient types
    color_map = {
        "color_rainbow": 1,  # Rainbow gradient
        "color_blue": 2,     # Blue gradient
        "color_yellow": 3,   # Yellow gradient
        "color_green": 4,    # Green gradient
        "color_purple": 5,   # Purple gradient
        "color_default": 0   # Default (white)
    }

    selected_color = call.data
    user_data['gradient_type'] = color_map.get(selected_color, 0)  # Default to white if not found
    user.update_data()

    telegram_bot.answer_callback_query(call.id, f"✅ Selected color: {selected_color.split('_')[1].capitalize()}")


@telegram_bot.callback_query_handler(func=lambda call: call.data.startswith("style_") or call.data.startswith("select_"))
def handle_style_navigation(call):
    data = call.data
    user = RiftUser(call.from_user.id, call.from_user.username)
    user_data = user.load_data()

    if not user_data:
        telegram_bot.reply_to(call.message, "You haven't setup your user yet, please use /start before skinchecking!")
        return
    
    if data.startswith("style_"):
        new_index = int(data.split("_")[1])
        telegram_bot.delete_message(call.message.chat.id, call.message.message_id)
        send_style_message(telegram_bot, call.message.chat.id, new_index)

    elif data.startswith("select_"):
        selected_index = int(data.split("_")[1])
        selected_style = available_styles[selected_index]
        user_data['style'] = selected_style['ID']
        user.update_data()
        telegram_bot.send_message(call.message.chat.id, f"✅ Style {selected_style['name']} selected.")

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

# Start the bot
print("Starting Rift Checker Bot...")
if __name__ == '__main__':
    telegram_bot.infinity_polling()