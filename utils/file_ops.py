# utils/file_ops.py

import shutil

from pathlib import Path

def clear_tmp_dir(tmp_path):
    try:
        tmp_path = Path(tmp_path)
        for entry in tmp_path.iterdir():
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                shutil.rmtree(entry)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to clear temp dir: {e}")
        return False


def move_finished_downloads(context):
    downloads = context["downloads_active"]
    completed = context["downloads_completed"]
    temp_path = Path(context["temp_path"])

    moved = 0
    errors = []

    for name, info in list(downloads.items()):
        if info.get("progress") == 100:
            source = temp_path / name
            destination_dir = Path(info.get("path"))
            destination = destination_dir / name

            if source.exists():
                try:
                    destination_dir.mkdir(parents=True,exist_ok=True)
                    shutil.move(source, destination)
                    completed[name] = {"path": str(destination)}
                    downloads.pop(name)
                    moved += 1
                except Exception as e:
                    errors.append(f"❌ Failed to move `{name}`: {e}")
            else:
                errors.append(f"⚠️ File not found: `{source}`")

    return moved, errors
