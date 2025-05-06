# commands/decompression.py

import asyncio

from pathlib import Path

async def start_decompression(event, context):
    files = list_compressed_files(Path(context["current_path"]))
    if not files:
        return f"❌ No compressed files found in `{context['current_path']}`"

    context["mode"] = "choose_compressed"
    message = "🗃️ Compressed files found:\n\n"
    for i, file in enumerate(files, 1):
        message += f"{i}. `{file.name}`\n"
    message += "\n📥 Type the number of the file to decompress or `cancel` to exit."

    context["compressed_files"] = files
    return message


async def choose_file(event, context):
    command = context.get('command')
    if command == "cancel":
        context["mode"] = None
        return "❌ Decompression cancelled."

    try:
        index = int(command.strip()) - 1
        files = context.get("compressed_files", [])
        if index < 0 or index >= len(files):
            raise ValueError
        context["selected_file"] = files[index]
        context["mode"] = "choose_decompression_folder"
        return (
            f"📦 Selected: `{files[index].name}`\n"
            "Where do you want to decompress it?\n"
            "- Type `here` to decompress in current path\n"
            "- Type `new:folder_name` to create a new folder\n"
            "- Or `cancel` to exit"
        )
    except ValueError:
        return "❌ Invalid selection. Type a valid number or `cancel`."


async def choose_folder(event, context):
    command = context.get('command')
    if command == "cancel":
        context["mode"] = None
        return "❌ Decompression cancelled."

    selected = context.get("selected_file")
    path = Path(context["current_path"])

    if not selected:
        context["mode"] = None
        return "⚠️ No file selected. Please start again."

    if command.startswith("new:"):
        original_text = context["original_text"]
        folder_name = original_text[4:].strip()
        dest_path = path / folder_name
        dest_path.mkdir(parents=True, exist_ok=True)
    elif command == "here":
        dest_path = path
    else:
        return "❌ Invalid option. Use `here`, `new:folder` or `cancel`."

    context["mode"] = None
    archive_path = path / selected
    await decompress_archive(archive_path, dest_path, event, context)


# Helpers

def list_compressed_files(directory):
    return [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() in ['.zip', '.rar', '.7z']]


async def decompress_archive(source, destination, event, context):
    client = context["client"]
    chat_id = context["chat_id"]
    if not source.is_file():
        await event.message.edit(f"❌ File not found: `{source}`")
        return

    if not destination.is_dir():
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            await event.message.edit(f"❌ Could not create destination folder: {e}")
            return

    ext = source.suffix

    if ext == ".rar":
        cmd = ["unrar", "x", "-y", str(source), str(destination)]
    elif ext == ".zip":
        cmd = ["unzip", "-o", str(source), "-d", str(destination)]
    elif ext == ".7z":
        cmd = ["7z", "x", str(source), f"-o{str(destination)}"]
    else:
        await event.message.edit("❌ File type not supported.")
        return

    await event.message.edit(f"🧰 Decompressing `{source.name}` to `{destination}`...")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        await client.send_message(chat_id, f"✅ Archive `{source.name}` decompressed to `{destination}`")
    else:
        error_msg = stderr.decode().strip()
        await client.send_message(chat_id, f"❌ Decompression failed:\n```\n{error_msg}\n```")
