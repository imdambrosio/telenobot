# commands/system.py

import subprocess
import shutil
import os

def check_disk_energy():
    try:
        result = subprocess.run("sudo hdparm -C /dev/sda", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode("utf-8")
        if "standby" in output:
            return "🛌 *Standby*"
        elif "active/idle" in output:
            return "💡 *Active*"
        else:
            return "❓ Unknown state"
    except Exception as e:
        return f"⚠️ Error checking disk energy: {e}"

def get_disk_space(path):
    try:
        total, used, free = shutil.disk_usage(path)
        percent = (used / total) * 100 if total else 0
        return f"💾 Disk space:\n" \
               f"• Total: {total // (1024**3)} GB\n" \
               f"• Used: {used // (1024**3)} GB\n" \
               f"• Free: {free // (1024**3)} GB\n" \
               f"• Usage: {percent:.1f}%"
    except Exception as e:
        return f"⚠️ Error getting disk space: {e}"

async def disk_status(event, context):
    commandos = 'lsblk -o UUID,MOUNTPOINT | grep /mnt/HDD'
    result = subprocess.run([commandos], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pic = result.stdout.decode('utf-8')
    path = "/mnt/HDD"
    output = ""

    if not pic:
        commandos = 'lsblk -o UUID,MOUNTPOINT | grep 01D4196A967D2A40'
        result = subprocess.run([commandos], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pic2 = result.stdout.decode('utf-8')
        if not pic2:
            return "❌ Disk missing"
        else:
            return "⚠️ Disk connected but not mounted"
    else:
        output += f"✅ Disk mounted at `{path}`"
        try:
            energy = check_disk_energy()
            output += f"\n🔋 Energy state: {energy}"
        except Exception as e:
            print(f"❌ Error checking disk status: {e}")
        
        try:
            space = get_disk_space(path)
            output += f"\n\n{space}"
        except Exception as e:
            print(f"❌ Error checking disk status: {e}")

    return output


async def mount_disk(event, context):
    mount_path = "/mnt/HDD"
    device = "/dev/sda2"
    try:
        if os.path.ismount(mount_path):
            return f"✅ Disk already mounted at {mount_path}"

        os.makedirs(mount_path, exist_ok=True)
        result = subprocess.run(["sudo", "mount", device, mount_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            return f"✅ Disk mounted successfully at {mount_path}"
        else:
            return f"❌ Failed to mount disk:\n{result.stderr.decode('utf-8')}"
    except Exception as e:
        return f"❌ Exception while mounting disk: {e}"


async def restart_service(event, context):
    parts = context["command"].split()
    if len(parts) < 3:
        return "❌ Specify a service name. Example: `restart service apache2`"

    service = parts[2]
    try:
        subprocess.run(["sudo", "systemctl", "restart", service], check=True)
        return f"✅ Service `{service}` restarted."
    except subprocess.CalledProcessError:
        return f"❌ Failed to restart service `{service}`."


async def service_status(event, context):
    services = ["ps3netsrv", "minidlna", "smbd", "apache2"]
    lines = []
    for svc in services:
        try:
            result = subprocess.run(["sudo", "systemctl", "is-active", svc], capture_output=True, text=True)
            state = result.stdout.strip()
            if state == "active":
                lines.append(f"✅ {svc} is active.")
            else:
                lines.append(f"❌ {svc} is inactive or failed.")
        except Exception as e:
            lines.append(f"⚠️ Error checking {svc}: {e}")

    return "\n".join(lines)

async def reboot_device(event, context):
    try:
        await event.message.edit("🔁 Rebooting system...")
        subprocess.run(["sudo", "reboot"], check=True)
        return "♻️ Reboot command sent."
    except Exception as e:
        return f"❌ Failed to reboot: {e}"
