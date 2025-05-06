# commands/routes.py

import json

from pathlib import Path

async def get_current_path(event, context):
    return f"Current download path is {Path(context.get('current_path')).as_posix()}"

async def list_available_routes(event, context):
    try:
        paths = context.get("available_routes", [])
        if not paths:
            return "📁 No routes available in `directorios` file."
        message = "📂 Available download paths:\n\n"
        for name, path in context.get("available_routes", {}).items():
            message += f"- `{name}` → `{path}`\n"
        return message
    except Exception as e:
        return f"❌ Error reading `directorios` file: {e}"

async def list_subfolders(event, context):
    path = Path(context["current_path"])
    try:
        subdirs = [name for name in path.iterdir() if name.is_dir()]
        if not subdirs:
            return "📁 No subfolders in the current path."
        message = f"📁 Subfolders in `{path}`:\n\n"
        for name in subdirs:
            message += f"• `{name}`\n"
        return message
    except Exception as e:
        return f"❌ Error listing subfolders: {e}"

async def list_directory_contents(event, context):
    path = Path(context["current_path"])
    try:
        subfolders = [subfolder.name for subfolder in path.iterdir() if subfolder.is_dir()]
        files = [file.name for file in path.iterdir() if file.is_file()]

        output = f"🗂️ Content of `{path}`:\n"

        if subfolders:
            subfolders_list = "\n📁 " + "\n📁 ".join(subfolders)
            output += f"\n**Subfolders:**{subfolders_list}"
        else:
            output += "\n📁 No subfolders."

        if files:
            files_list = "\n📄 " + "\n📄 ".join(files)
            output += f"\n\n**Files:**{files_list}"
        else:
            output += "\n\n📄 No files."

        return output
    except Exception as e:
        return f"❌ Error reading directory contents: {e}"

async def set_route(event, context):
    paths = context.get("available_routes", [])
    if not paths:
        return "📁 No routes configured."

    context["mode"] = "select_base_route"
    message = "📂 Available base routes:\n\n"
    for path in paths:
        message += f"• `{path}` → `{paths[path]}`\n"
    message += "\nType the full path you want to use."
    return message

async def select_base_route(event, context):
    command = context.get('command')
    print(f"{command}")
    if command == "cancel":
        context["mode"] = None
        return f"❌ Route setting canceled"

    available = context.get("available_routes", [])
    actual_key = None
    
    for key in available.keys():
        if key.lower() == command:
            actual_key = key
            break
    if not actual_key:
        return f"❌ Invalid route. Try again or type `cancel`."
    
    context["base_route"] = Path(available[actual_key])
    context["current_path"] = Path(available[actual_key])
    context["mode"] = "choose_or_create_sub"
    return (
        f"📁 Base route set to `{context['current_path']}`\n"
        "Do you want to:\n"
        "1. Use an existing subfolder (type `use`)\n"
        "2. Create a new subfolder (type `new:subfolder_name`)\n"
        "Or type `cancel` to abort the subfolder selection."
    )

async def choose_or_create_sub(event, context):
    command = context.get('command')
    if command == "cancel":
        context["mode"] = None
        return f"🛠️ Selected folder: '{context['current_path']}'"

    base = context.get("base_route")
    if not base:
        context["mode"] = None
        return "⚠️ No base route found. Start again with `set route`."

    original_text = context.get('original_text')
    if command.startswith("new:"):
        sub = original_text[4:].strip()
        final = base / sub
        final.mkdir(parents=True, exist_ok=True)
    elif command.startswith("use"):
        message = await list_subfolders(event, context)
        message += "\nSelect the desired subfolder"
        return message
    else:
        final = base / original_text
        if not final.is_dir():
            return f"❌ Subfolder `{original_text}` does not exist."

    context["current_path"] = final
    context["mode"] = "offer_to_save_route"
    context["new_route_candidate"] = final

    return (
        f"✅ Download path set to `{final.as_posix()}`\n"
        "💾 Type `save:alias` to store this path in `directorios.json` with the alias, or `cancel` to skip."
    )

async def offer_to_save_route(event, context):
    command = context.get('command')
    original_text = context.get('original_text')
    if command.startswith("save:"):
        alias = original_text[5:].strip()
        new_path = context.get("new_route_candidate")
        if not new_path or not alias:
            context["mode"] = None
            return "⚠️ Invalid name or no route to save."

        data = context.get('available_routes')

        if alias in data:
            msg = f"⚠️ Alias `{alias}` already exists in `directorios.json`."
        else:
            data[alias] = new_path.as_posix()
            try:
                with open("directorios.json", "w") as f:
                    json.dump(data, f, indent=4)
                msg = f"✅ Path `{new_path.as_posix()}` saved as `{alias}` in `directorios.json`."
            except Exception as e:
                msg = f"⚠️ Could not write to `directorios.json`: {e}"

        context["mode"] = None
        context.pop("new_route_candidate", None)
        return msg

    context["mode"] = None
    context.pop("new_route_candidate", None)
    return "❌ Save cancelled."
