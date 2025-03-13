from dotenv import load_dotenv
import os
import telebot
from telebot import types

# Load the token from .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Initialize the bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Define a command handler
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to KurdCheckerBot!")

# Start the bot
bot.polling()