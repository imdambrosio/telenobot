# dispatcher.py

import json

from commands import core, decompression, downloader, routes, system
from utils.localization import register_language_listener, _
from pathlib import Path

COMMAND_HANDLERS = {
    "status": {
        "handler": core.status
    },
    "history": {
        "handler": core.download_history
    },
    "clear temp": {
        "handler": core.clear_temp,
        "edit_before": "🧹 Cleaning temp folder..."
    },
    "clear download history": {
        "handler": core.clean_download_history,
        "edit_before": "🗑️ Cleaning download history..."
    },
    "move completed": {
        "handler": core.move_completed,
        "edit_before": "📂 Moving completed files..."
    },
    "download path": {
        "handler": core.download_path
    },
    "ping": {
        "handler": core.ping
    },

    "decompress": {
        "handler": decompression.start_decompression
    },

    "download link": {
        "handler": downloader.download_link_command
    },

    "current path": {
        "handler": routes.get_current_path
    },
    "list contents": {
        "handler": routes.list_directory_contents
    },
    "list subfolders": {
        "handler": routes.list_subfolders
    },
    "list routes": {
        "handler": routes.list_available_routes
    },
    "set route": {
        "handler": routes.set_route
    },

    "disk status": {
        "handler": system.disk_status
    },
    "mount disk": {
        "handler": system.mount_disk
    },
    "restart service": {
        "handler": system.restart_service,
        "edit_before": "⏳ Trying to restart service..."
    },
    "reboot": {
        "handler": system.reboot_device,
        "edit_before": "🔄 Rebooting system..."
    },
    "service status": {
        "handler": system.service_status
    }
    # add more commands here
}


MODE_HANDLERS = {
    "choose_compressed": {
        "handler": decompression.choose_file
    },
    "choose_decompression_folder": {
        "handler": decompression.choose_folder
    },
    "changing_routes": {
        "handler": routes.set_route
    },
    "select_base_route": {
        "handler": routes.select_base_route
    },
    "choose_or_create_sub": {
        "handler": routes.choose_or_create_sub
    },
    "offer_to_save_route": {
        "handler": routes.offer_to_save_route
    }
    # add more mode handlers
}


async def handle(event, context):
    if event.media:
        return await downloader.add_to_the_queue(event.message, context)
    
    command = context.get('command')
    mode = context.get('mode')
    entry = None
    print(f"command: {command} mode:{mode}")

    if not mode or mode == "":
        for cmd_key in sorted(COMMAND_HANDLERS.keys(), key=len, reverse=True):
            if command.startswith(cmd_key):
                entry = COMMAND_HANDLERS.get(cmd_key)
                print(f"{cmd_key}")
                break
    else:
        entry = MODE_HANDLERS.get(mode)
    if not entry:
        return "❌ Unknown command."
    
    handler = entry["handler"]
    initial_msg = entry.get("edit_before")

    if initial_msg:
        await edit_then_replace(event, initial_msg)

    if handler:
        return await handler(event, context)

    return "❌ Unknown command."

async def edit_then_replace(event, reply):
    print(reply)
    await event.message.edit(reply)

def load_commands(lang):
    global COMMAND_HANDLERS 
    commands_path = Path(f"utils/locales/{lang}/commands.json")
    if commands_path.exists():
        with open(commands_path, "r", encoding="utf-8") as f:
            COMMAND_HANDLERS = json.load(f)
    else:
        print("\n❌ ERROR: COMMANDS FILE NOT FOUND")

def on_language_change(lang):
    load_commands(lang)

async def helloMessage(version, download_path):
    return _("messages.startup", version=version, path=download_path)


register_language_listener(on_language_change)
load_commands("en")