@echo off
:restart
python telegram_bot.py
timeout /t 5
goto restart