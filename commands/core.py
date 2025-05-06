# commands/core.py

from utils.helpers import get_queue_status
from utils.file_ops import clear_tmp_dir, move_finished_downloads
from utils.localization import set_language

# Get the current status of the telenobot service
async def status(event, context):
    active = context["downloads_active"]
    queue = context["queue"]
    current_path = context["current_path"]
    temp_path = context["temp_path"]

    if not active:
        return "✅ Bot is active.\n📥 No active downloads."

    message = "✅ Bot is active.\n📥 Active download:\n"
    for name, info in active.items():
        message += f"• {name} – {info['progress']}%\n--📁 Path: {info['path']}\n"

    if queue.qsize() > 0:
        message += await get_queue_status(queue, current_path, temp_path)

    return message

# Ping function in order to check if the telenobot is active or not
async def ping(event, context):
    return "🏓 Pong - the bot is active."

# Get the download history of the current session
async def download_history(event, context):
    completed = context["downloads_completed"]
    if not completed:
        return "📥 No downloads completed in this session."

    message = f"📥 Completed downloads ({len(completed)}):\n"
    for name, info in completed.items():
        message += f"• {name}\n-– 📁 Saved at: {info['path']}\n"
    return message

# Get the current download path
async def download_path(event, context):
    current_path = context["current_path"]
    return f"📂 Current download path:\n`{current_path}`"

# Clean the download history of the current session
async def clean_download_history(event, context):
    completed = context["downloads_completed"]
    if not completed:
        return "📥 No downloads completed in this session."
    else:
        completed.clear()

        if not completed:
            return "✅ Download history cleared."
        else:
            return "❌ Failed to clear download history."

# Delete all the files in the temp folder
async def clear_temp(event, context):
    success = clear_tmp_dir(context["temp_path"])
    if success:
        return "🧹 Temp folder cleaned successfully."
    return "❌ Failed to clean the temp folder."

# Move all the downloaded files to the final path
async def move_completed(event, context):
    moved, errors = move_finished_downloads(context)
    lines = []

    if moved:
        lines.append(f"✅ {moved} file(s) moved to final destination.")
    else:
        lines.append("📁 No files ready to move.")

    if errors:
        lines.append("")
        lines.extend(errors)

    return "\n".join(lines)

async def set_lang(event, context):
    lang = context["lang"]
    set_language(lang)