# telegram-download-daemon aka telenobot

Fork del trabajo original de Alfonso E.M. <alfonso@el-magnifico.org>

## Funcionalidades extendidas respecto al daemon original

| Funcionalidad                       | Descripción |
|------------------------------------|-------------|
| **Descarga desde enlaces públicos** | Permite descargar archivos desde mensajes enlazados tipo `https://t.me/canal/1234`, no solo desde el canal. |
| **Gestión dinámica de carpetas**    | Podés cambiar la ruta de descarga durante la ejecución y crear/usar subcarpetas fácilmente. |
| **Soporte para múltiples rutas de destino** | Se puede seleccionar entre múltiples carpetas (`listar rutas`, `cambiar ruta`) e incluso guardar nuevas. |
| **Cambio de ruta por archivo activo** | Con el comando `cambiar ruta de descarga`, podés cambiar el destino de un archivo en descarga sin afectar al resto. |
| **Comprobación y montaje de disco** | Comandos como `disco duro` o `montar disco` permiten asegurar que el almacenamiento esté montado antes de mover archivos. |
| **Soporte para mover archivos completados** | Comando `mover completados` para mover manualmente archivos que hayan llegado al 100% y no se hayan trasladado. |
| **Gestión de servicios del sistema** | Comandos como `estado servicios` y `reiniciar servicio <nombre>` permiten controlar servicios externos como `minidlna`. |
| **Watcher de carpeta** | Observa una carpeta definida en el código y notifica si se sube o borra algo. |
| **Historial de mensajes limpio** | Con `borrar historial`, eliminás todos los mensajes anteriores del bot en el canal. |
| **Comando `status` completo** | Muestra descargas activas y elementos en cola, incluyendo su progreso y ruta. |
| **Logs persistentes automáticos** | Redirección de `stdout` y `stderr` a archivos de log diarios en la carpeta `logs/`. |
| **Ayuda embebida** | Comando `ayuda` con descripción detallada de todas las funcionalidades, cargadas desde un archivo JSON. |
| **Soporte para múltiples usuarios (opcional)** | La estructura permite fácilmente extender a múltiples sesiones/chat si se desea en el futuro. |

# README original del daemon

A Telegram Daemon (not a bot) for file downloading automation [for channels of which you have admin privileges]

If you have got an Internet connected computer or NAS and you want to automate file downloading from Telegram channels, this
daemon is for you.

Telegram bots are limited to 20Mb file size downloads. So I wrote this agent
or daemon to allow bigger downloads (limited to 2GB by Telegram APIs).

# Installation

You need Python3 (3.6 works fine, 3.5 will crash randomly).

Install dependencies by running this command:

    pip install -r requirements.txt

(If you don't want to install `cryptg` and its dependencies, you just need to install `telethon`)

Warning: If you get a `File size too large message`, check the version of Telethon library you are using. Old versions have got a 1.5Gb file size limit.


Obtain your own api id: https://core.telegram.org/api/obtaining_api_id

# Usage

You need to configure these values:

| Environment Variable     | Description                                                  | Default Value       |
|--------------------------|--------------------------------------------------------------|---------------------|
| `TELEGRAM_DAEMON_API_ID`   | api_id from https://core.telegram.org/api/obtaining_api_id   |                     |
| `TELEGRAM_DAEMON_API_HASH` | api_hash from https://core.telegram.org/api/obtaining_api_id |                     |
| `TELEGRAM_DAEMON_DEST`     | Destination path for downloaded files                       | `/telegram-downloads` |
| `TELEGRAM_DAEMON_TEMP`     | Destination path for temporary (download in progress) files                       | use --dest |
| `TELEGRAM_DAEMON_CHANNEL`  | Channel id to download from it                               |                     |
| `TELEGRAM_DAEMON_DUPLICATES`  | What to do with duplicated files: ignore, overwrite or rename them | rename                     |
| `TELEGRAM_DAEMON_WORKERS`  | Number of simultaneous downloads | Equals to processor cores                     |

Finally, resend any file link to the channel to start the downloading. This daemon can manage many downloads simultaneously.

You can also 'talk' to this daemon using your Telegram client:

# Lista de comandos
NOTA: Este daemon lo uso en mi Raspberry-Pi de forma personal, por lo que hay comandos que a lo mejor no se adaptan a la necesidad de todo el mundo

| comando                     | descripcion                                                               |
|:----------------------------|:--------------------------------------------------------------------------|
| borrar historial            | Borra el historial de mensajes del bot en el chat.                        |
| cambiar ruta                | Permite elegir una nueva ruta de descarga desde el listado de destinos.   |
| cambiar ruta de descarga    | Permite cambiar la ruta de descarga de un archivo activo individualmente. |
| descargar enlace <URL>      | Descarga un mensaje con archivo desde un enlace tipo https://t.me/.../    |
| disco duro                  | Comprueba si el disco está montado correctamente.                         |
| estado servicios            | Muestra el estado de servicios como ps3netsrv, minidlna, smbd, apache2.   |
| limpiar temp                | Limpia la carpeta temporal definida en TELEGRAM_DAEMON_TEMP.              |
| listar contenido            | Lista subcarpetas y archivos dentro de la ruta actual.                    |
| listar rutas                | Muestra los directorios disponibles como destinos de descarga.            |
| listar subcarpetas          | Lista subcarpetas dentro de la ruta actual.                               |
| montar disco                | Monta el disco duro manualmente (alias: montar disco duro).               |
| mover completados           | Mueve archivos con descarga 100% al destino final configurado.            |
| reiniciar                   | Reinicia la Raspberry Pi.                                                 |
| reiniciar servicio <nombre> | Reinicia el servicio especificado.                                        |
| ruta de descarga            | Muestra la ruta actual configurada para las descargas.                    |
| status                      | Muestra el estado del bot y las descargas activas.                        |
