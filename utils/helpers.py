# utils/helpers.py

from pathlib import Path
from telethon.tl.types import DocumentAttributeFilename
from mimetypes import guess_extension

# Generate the filename from the message
def get_filename_from_message(message):
    # If it's a document with attributes, we try to get the filename
    if message.document:
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name

        # If there's no filename, we try to guess it from the mime_type
        ext = guess_extension(message.document.mime_type or "")
        return f"file_{message.id}{ext or ''}"

    if message.photo:
        return f"photo_{message.id}.jpg"

    # Fallback: use text content if it exists
    if message.message:
        name = message.message.strip()
        if len(name) < 64:  # avoid text being too long
            return name + ".txt"

    # Last resort
    return f"file_{message.id}"

# Checks if the file name already exists and if so, modifies it
def generate_unique_name(filename, context):
    dest_folder = context["current_path"]
    temp_folder = context["temp_path"]

    new_name = Path(filename)
    name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1

    dest_folder = Path(dest_folder)
    temp_folder = Path(temp_folder)

    while (dest_folder / new_name).exists():
        new_name = Path(f"{name} ({counter}){extension}")
        counter += 1

    while (temp_folder / new_name).exists():
        new_name = Path(f"{name} ({counter}){extension}")
        counter += 1

    return new_name.name

# Get the queue status, how many files are in the queue
async def get_queue_status(queue, current_path, temp_path):
    queue_size = queue.qsize()
    output = ""
    filename = None
    if queue_size > 0:
        output += f"\n⏳ Files in queue: {queue_size}\n"
        for i, (c, m, cid) in enumerate(queue._queue, start=1):
            try:
                filename = get_filename_from_message(m)
                filename = generate_unique_name(current_path, temp_path, filename)
            except:
                filename = "File"
            output += f"  {i}. {filename}\n"
    return output