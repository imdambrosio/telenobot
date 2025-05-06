# telegram-download-daemon aka telenobot

Fork of the original work by Alfonso E.M. <alfonso@el-magnifico.org>

# Original Daemon README

A Telegram Daemon (not a bot) for file downloading automation [for channels where you have admin privileges].

If you have an Internet-connected computer or NAS and want to automate file downloading from Telegram channels, this daemon is for you.

Telegram bots are limited to 20MB file size downloads. So I wrote this agent or daemon to allow larger downloads (limited to 2GB by Telegram APIs).

## Extended Features Compared to the Original Daemon

| Feature                                | Description |
|----------------------------------------|-------------|
| **Configuration loading from JSON files** | Allows loading configuration from a `.json` file, making script execution easier. |
| **Download from public links**          | Enables downloading files from messages linked like `https://t.me/channel/1234`, not just from the channel. |
| **Dynamic folder management**           | You can change the download path during execution and easily create/use subfolders. |
| **Support for multiple destination paths** | Allows selection between multiple folders (`list paths`, `change path`) and even saving new ones. |
| **Change path per active file**         | With the command `change download path`, you can change the destination of an active download without affecting others. |
| **Disk check and mount support**        | Commands like `hard drive` or `mount disk` help ensure storage is mounted before moving files. |
| **Move completed files support**        | `move completed` command allows manually moving files that have reached 100% and haven't been transferred yet. |
| **System services management**          | Commands like `service status` and `restart service <name>` let you control external services like `minidlna`. |
| **Folder watcher**                      | Watches a folder defined in the code and notifies if anything is added or deleted. |
| **Clean message history**               | With `clear history`, all previous messages from the bot in the channel are deleted. |
| **Full `status` command**               | Shows active downloads and queued items, including progress and path. |
| **Automatic persistent logs**           | Redirects `stdout` and `stderr` to daily log files inside the `logs/` folder. |
| **Embedded help**                       | `help` command shows detailed descriptions of all features, loaded from a JSON file. |
| **Multi-user support (optional)**       | The structure is easily extendable to support multiple sessions/chats in the future. |
| **Decompression of downloaded files**        | Includes a `decompress` command to extract compressed archives after download. |
| **Future multi-language support**            | Structured to allow localization and support for multiple languages. |
## Installation

You need Python 3 (3.6 works fine, 3.5 will crash randomly).

Install dependencies by running:

```bash
pip install -r requirements.txt
```

(If you don’t want to install `cryptg` and its dependencies, you can just install `telethon`)

**Warning:** If you get a `File size too large` message, check the version of the Telethon library you're using. Older versions have a 1.5GB file size limit.

Get your own API ID: https://core.telegram.org/api/obtaining_api_id

## Usage

You need to configure the following environment variables:

| Configuration Variable | Description | Example Value |
|-------------------------|-------------|----------------|
| `api_id` | Your Telegram API ID obtained from https://core.telegram.org/api/obtaining_api_id | `28815430` |
| `api_hash` | Your Telegram API hash obtained from the same page as API ID | `73713f2f964088ddf2c850dbbd83df49` |
| `channel_id` | The ID of the channel from which to download files | `-1002390741468` |
| `session_path` | Custom session file path for persistent login (optional) | `None` |
| `dest` | Path to the directory where files will be downloaded | `/mnt/HDD` |
| `temp` | Path to store files temporarily during download | `/home/dietpi/tmp/telegram-temp` |
| `duplicates` | How to handle duplicate files: ignore, overwrite, or rename | `rename` |
| `workers` | Number of simultaneous download workers | `4` |
| `lang` | Language used for localization | `en` |

To start downloading, just resend a file link to the channel. This daemon can manage multiple downloads simultaneously.

You can also interact with the daemon via your Telegram client:

## Command List
**NOTE:** I use this daemon personally on a Raspberry Pi, so some commands may not suit everyone's needs.

| Command | Description |
|---------|-------------|
| `status` | Shows the bot's status and active downloads. |
| `history` | Displays download history. |
| `clear temp` | Cleans the temp folder defined by TELEGRAM_DAEMON_TEMP. |
| `clear download history` | Deletes the download history. |
| `move completed` | Moves files with 100% completion to the final destination. |
| `download path` | Displays the current download path. |
| `ping` | Checks if the bot is responsive. |
| `decompress` | Starts decompression of compressed files. |
| `download link` | Downloads a message with a file from a Telegram link (e.g., https://t.me/...). |
| `current path` | Displays the current working directory. |
| `list contents` | Lists subfolders and files in the current directory. |
| `list subfolders` | Lists only subfolders in the current directory. |
| `list routes` | Shows available download destination directories. |
| `set route` | Sets a specific download route. |
| `disk status` | Checks if the disk is correctly mounted. |
| `mount disk` | Manually mounts the disk drive. |
| `restart service` | Restarts the specified system service. |
| `reboot` | Reboots the device. |
| `service status` | Displays the status of services like ps3netsrv, minidlna, etc. |
| `status`                    | Shows the bot's status and active downloads. |