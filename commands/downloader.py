#downloader.py

import asyncio
import time
import shutil

from utils.helpers import get_filename_from_message
from utils.helpers import generate_unique_name

from telethon.errors import FloodWaitError
from telethon.tl.types import PeerChannel
from pathlib import Path

async def add_to_the_queue(message, context):
    queue = context["queue"]
    await queue.put((message, context["client"], context["chat_id"]))
    filename = get_filename_from_message(message)
    filename = generate_unique_name(filename, context)
    return f"📥 {filename} added to the download queue"

async def download_link_command(event, context):
    command = context.get('command')
    parts = command.split()
    if len(parts) < 3:
        return "❌ Wrong format. Use: download link https://t.me/channel/1234"
    else:
        link = parts[2]
        message, error = await get_message_from_link(link, context["client"])

        if error:
            return error
        elif message and message.media:
            return await add_to_the_queue(message, context)

async def get_message_from_link(link, client):
    if "t.me/" not in link:
        return None, "❌ Invalid link."

    route = link.split("t.me/")[1]
    parts = route.strip("/").split("/")

    if len(parts) == 2:
        return await get_by_channel_username(parts, client)
    elif len(parts) == 3 and parts[0] == "c":
        return await get_by_channel_id(parts, client)
    else:
        return None, "❌ Unrecognized link format."

async def get_by_channel_username(parts, client):
    channel_username = parts[0]

    try:
        message_id = int(parts[1])
        await asyncio.sleep(0.5)
        message = await client.get_messages(channel_username, ids=message_id)
        return message, None
    except ValueError:
        return None, "❌ Invalid message ID."

async def get_by_channel_id(parts, client):
    try:
        channel_id = int(parts[1])
        message_id = int(parts[2])
        entity = PeerChannel(channel_id)
        await asyncio.sleep(0.5)
        message = await client.get_messages(entity, ids=message_id)
        return message, None
    except ValueError:
        return None, "❌ Invalid channel or message ID."

async def worker(context):
    queue = context["queue"]
    while True:
        message, client, chat_id = await queue.get()
        try:
            await download_message(message, client, chat_id, context)
        except Exception as e:
            print(f"❌ Error en worker: {e}")
        finally:
            queue.task_done()

async def update_status(current, total, msg, filename, context):
        lastUpdate = 0
        updateFrequency = 30
        downloads_active = context.get('downloads_active')
        
        progress = int(current * 100 / total)
        last_progress = downloads_active[filename]["last_progress"]
        downloads_active[filename]["progress"] = progress

        try:
            currentTime=time.time()
            if (currentTime - lastUpdate) > updateFrequency and (progress - last_progress) > 2:
                await msg.edit(f"📥 Downloading {filename}... {progress}%")
                lastUpdate=currentTime
                downloads_active[filename]["last_progress"] = progress
        except FloodWaitError as e:
            print(f"⏳ FloodWait: waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            currentTime=time.time()
            if (currentTime - lastUpdate) > updateFrequency:
                await msg.edit(f"📥 Downloading {filename}... {progress}%")
                lastUpdate=currentTime
        except Exception as e:
            if "Content of the message was not modified" not in str(e):
                raise e

async def download_message(message, client, chat_id, context):

    downloads_active = context["downloads_active"]
    downloads_completed = context["downloads_completed"]

    try:
        current_path = Path(context["current_path"])

        # 1. To obtain the filename from the message
        filename = get_filename_from_message(message)
        filename = generate_unique_name(filename, context)

        temp_path = Path(context["temp_path"]) / filename

        # 2. Send progress message
        msg = await client.send_message(chat_id, f"📥 Downloading {filename}... 0%")

        # 3. Download while keeping progress
        downloads_active[filename] = {
            "progress": 0,
            "last_progress": 0,
            "path": current_path
        }

        start_time = time.time()

        await client.download_media(
            message,
            temp_path.as_posix(),
            progress_callback=lambda c, t: asyncio.create_task(
                update_status(c, t, msg, filename, context)
            )
        )

        # 4. Check if the downloaded file exists
        if not temp_path.is_file():
            await client.send_message(chat_id, f"❌ Error: the file was not downloaded correctly")
            return
        
        # 5. Move the file
        final_path = downloads_active[filename]["path"] / filename
        if not temp_path.exists():
            await client.send_message(chat_id, f"❌ Temporal file not found in {temp_path.parent.as_posix()}")
        if not final_path.parent.exists():
            await client.send_message(chat_id, f"⚠️ Destination path does not exist.\nThe file stayed in {temp_folder.as_posix()}")
            return

        try:
            shutil.move(temp_path.as_posix(), final_path.as_posix())
            downloads_active.pop(filename, None)
            downloads_completed[filename] = {
                "path": final_path.as_posix()
            }
        except Exception as e:
            await client.send_message(chat_id, f"❌ Error: The file cannot be moved\n`{str(e)}`\nThe file stayed in :\n`{temp_path.as_posix()}`")

        # 6. Compute download speed and time elapsed
        end_time = time.time()
        elapsed = end_time - start_time # in seconds
        size_MB = final_path.stat().st_size / (1024 * 1024)
        if elapsed > 0:
            speed_MBps = size_MB / elapsed
        else:
            speed_MBps = 0
        await client.send_message(
            chat_id,
            f"✅ `{filename}` downloaded and moved correctly."
            f"\n⏱️ Time elapsed: `{elapsed:.1f}` s"
            f"\n📦 Size: `{size_MB:.2f}` MB"
            f"\n🚀 Speed: `{speed_MBps:.2f}` MB/s"
            f"\n📁 Saved at:"
            f"\n`{final_path.as_posix()}`"
        )

    except Exception as e:
        await client.send_message(chat_id, f"❌ Error al procesar el archivo: {str(e)}")  
