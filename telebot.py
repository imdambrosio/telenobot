#!/home/dietpi/environments/my_env/bin/python3
# Telegram Download Daemon
# Original author: Alfonso E.M. <alfonso@el-magnifico.org>
# Edited and manteined by Kevin S. D'Ambrosio

import os
import json
import sys
import logging
import asyncio
import multiprocessing

from datetime import datetime
from datetime import timezone

from telethon import TelegramClient, events, __version__
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    DocumentAttributeFilename,
    DocumentAttributeVideo
)

from sessionManager import getSession, saveSession
from dispatcher import handle, helloMessage
from utils.localization import register_language_listener
from commands.downloader import worker

# Version
TDD_VERSION = "3.0.0"

# Logs system
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = datetime.now().strftime("telenobot_%Y-%m-%d_%H-%M-%S.log")
log_path = os.path.join(LOG_DIR, log_filename)

log_file = open(log_path, "a", encoding="utf-8", buffering=1)  # line-buffered
sys.stdout = log_file
sys.stderr = log_file

print("\n🟢 Logging started:", datetime.now())

# Load configuration from files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DIRECTORY_PATH = os.path.join(BASE_DIR, "directorios.json")
COMMANDS_PATH = os.path.join(BASE_DIR, "comandos.json")

# Functions
def load_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            CONFIG = json.load(f)
    else:
        print("\n ERROR: CONFIG FILE NOT FOUND")

def save_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(CONFIG, f, indent=4)
    else:
        print("\n ERROR: CONFIG FILE NOT FOUND")

def load_directory():
    if os.path.exists(DIRECTORY_PATH):
        with open(DIRECTORY_PATH, "r") as f:
            return json.load(f)
    else:
        return {}

def on_language_change(lang):
    global CONFIG
    CONFIG["lang"] = lang
    save_config()

# Message editor
async def log_reply(message, reply):
    print(reply)
    await message.edit(reply)

# Hello message
async def sendHelloMessage(client, chat_id):
    print(f"Telegram Download Daemon {TDD_VERSION} using Telethon {__version__}")
    message = helloMessage(TDD_VERSION, TELEGRAM_DAEMON_DEST)
    await client.send_message(
        chat_id,
        message
    )


load_config()
register_language_listener(on_language_change)
ROUTES = load_directory()

if os.path.exists(COMMANDS_PATH):
    with open(COMMANDS_PATH, "r", encoding="utf-8") as f:
        COMMANDS_JSON = json.load(f)
else:
    print("\n ERROR: COMMANDS FILE NOT FOUND")

# Credentials and routes values
TELEGRAM_DAEMON_API_ID = CONFIG.get("api_id", "")
TELEGRAM_DAEMON_API_HASH = CONFIG.get("api_hash", "")
TELEGRAM_DAEMON_CHANNEL = CONFIG.get("channel_id", "")

TELEGRAM_DAEMON_SESSION_PATH = CONFIG.get("session_path")
TELEGRAM_DAEMON_DEST = CONFIG.get("dest", "/telegram_downloads")
TELEGRAM_DAEMON_TEMP = CONFIG.get("temp", "/tmp")

TELEGRAM_DAEMON_DUPLICATES = CONFIG.get("duplicates", "rename")
TELEGRAM_DAEMON_WORKERS = CONFIG.get("workers", multiprocessing.cpu_count())

TELEGRAM_DAEMON_LANG = CONFIG.get("lang", "en")

# Create necessary folders
os.makedirs(TELEGRAM_DAEMON_TEMP, exist_ok=True)
os.makedirs(TELEGRAM_DAEMON_DEST, exist_ok=True)

# Variables
proxy = None
context = {
    "command": "",
    "original_text": "",
    "mode": "",

    "downloads_active": {},
    "downloads_completed": {},

    "available_routes": ROUTES,
    "current_path": TELEGRAM_DAEMON_DEST,
    "temp_path": TELEGRAM_DAEMON_TEMP,
    "new_route_candidate": "",
    "base_route": "",

    "compressed_files": {},

    "selected_file": "",

    "queue": asyncio.Queue(),
    "client": "",
}

# End of interesting parameters

# MESSAGE HANDLER
with TelegramClient(getSession(), TELEGRAM_DAEMON_API_ID, TELEGRAM_DAEMON_API_HASH,
                    proxy=proxy).start() as client:

    saveSession(client.session)
    start_time = datetime.now(timezone.utc)

    context["client"] = client

    print(f"[DEBUG] hora inicio: {start_time}")
    @client.on(events.NewMessage(chats=[TELEGRAM_DAEMON_CHANNEL]))
    async def handler(event):
        global context

        context["original_text"] = event.message.message
        context["command"] = context["original_text"].lower()
        print(f"[DEBUG] Command received: {context['command']} Original text: {context['original_text']}")

        # Ignore previous messages or not from the channel
        if event.message.date < start_time or event.to_id.channel_id != context["chat_id"]:
            return

        try:
            output = await handle(event, context)

            if output:
                await log_reply(event.message, output)

        except Exception as e:
                print('Events handler error: ', e)

    # Start function
    async def start():
        client = context["client"]
        
        entity = await client.get_entity(TELEGRAM_DAEMON_CHANNEL)
        context["chat_id"] = entity.id

        # 1. Welcome message
        await sendHelloMessage(context["client"], context["chat_id"])

        # 2. Launch tasks in parallel
        task_worker = asyncio.create_task(worker(context))

        # 3. Wait client desconection
        await context["client"].run_until_disconnected()

        for task in task_worker:
            task.cancel()
        
        await asyncio.gather(task_worker, task_monitor, return_exceptions=True)

    client.loop.run_until_complete(start())