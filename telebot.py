#!/home/dietpi/environments/my_env/bin/python3
# Telegram Download Daemon
# Original author: Alfonso E.M. <alfonso@el-magnifico.org>
# Editado y mantenido por Kevin S. D'Ambrosio

import os
import json
import time
import math
import shutil
import logging
import asyncio
import argparse
import subprocess
import multiprocessing

from datetime import datetime
from mimetypes import guess_extension
from shutil import move
from os import getenv, path

from telethon import TelegramClient, events, __version__
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    PeerChannel,
    DocumentAttributeFilename,
    DocumentAttributeVideo
)

from sessionManager import getSession, saveSession
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = datetime.now().strftime("telebot_%Y-%m-%d.log")
log_path = os.path.join(LOG_DIR, log_filename)

log_file = open(log_path, "a", buffering=1)  # line-buffered
sys.stdout = log_file
sys.stderr = log_file

print("🟢 Logging iniciado:", datetime.now())
print("📝 Este print debería aparecer en el log")

# Logging básico
logging.basicConfig(
    format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
    level=logging.WARNING
)

# Versionado
TDD_VERSION = "2.0"

# Cargar configuración desde los archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DIRECTORIOS_JSON_PATH = os.path.join(BASE_DIR, "directorios.json")
COMANDOS_PATH = os.path.join(BASE_DIR, "comandos.json")

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        CONFIG = json.load(f)

with open(COMANDOS_PATH, "r", encoding="utf-8") as f:
    COMANDOS_JSON = json.load(f)

# Se usan funcopnes para los diArectorios debido a su comportamiento dinamico
def cargar_destinos():
    if os.path.exists(DIRECTORIOS_JSON_PATH):
        with open(DIRECTORIOS_JSON_PATH, "r") as f:
            return json.load(f)
    else:
        return {}

def guardar_destinos(destinos):
    with open(DIRECTORIOS_JSON_PATH, "w") as f:
        json.dump(destinos, f, indent=4)

# Credenciales y rutas por entorno o valores por defecto
TELEGRAM_DAEMON_API_ID = CONFIG.get("api_id", "")
TELEGRAM_DAEMON_API_HASH = CONFIG.get("api_hash", "")
TELEGRAM_DAEMON_CHANNEL = CONFIG.get("channel_id", "")

TELEGRAM_DAEMON_SESSION_PATH = CONFIG.get("session_path")
TELEGRAM_DAEMON_DEST = CONFIG.get("dest", "/telegram_downloads")
TELEGRAM_DAEMON_TEMP = CONFIG.get("temp", "/tmp")

TELEGRAM_DAEMON_DUPLICATES = CONFIG.get("duplicates", "rename")
TELEGRAM_DAEMON_WORKERS = CONFIG.get("workers", multiprocessing.cpu_count())

TELEGRAM_DAEMON_TEMP_SUFFIX = "tdd"

# Crear carpetas necesarias
os.makedirs(TELEGRAM_DAEMON_TEMP, exist_ok=True)
os.makedirs(TELEGRAM_DAEMON_DEST, exist_ok=True)

# Rutas de descarga
DESTINOS_DISPONIBLES = cargar_destinos()
RUTA_ACTUAL = TELEGRAM_DAEMON_DEST
DIRECTORIO_TEMPORAL = None
modo = None

# Edit these lines:
proxy = None
updateFrequency = 30 # Para evitar el Flood ShadowBan
lastUpdate = 0
descargas_activas = {}
archivo_en_edicion = None

# End of interesting parameters

#Mensaje inicial
async def sendHelloMessage(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    print("Telegram Download Daemon "+TDD_VERSION+" using Telethon "+__version__)
    await client.send_message(entity, "¡Bot iniciado correctamente, listo para los archivos!\nRuta de descarga: " +RUTA_ACTUAL)
 
#Editor de mensajes
async def log_reply(message, reply):
    print(reply)
    await message.edit(reply)

# Watcher de las copias de seguridad de switch
CARPETA_WATCH = "/var/www/html/jksv"
class SubidaHandler(FileSystemEventHandler):
    def __init__(self, client, entity, loop):
        self.client = client
        self.entity = entity
        self.loop = loop

    def on_created(self, event):
        if not event.is_directory:
            archivo = os.path.relpath(event.src_path, CARPETA_WATCH)
            print(f"📁 Nuevo archivo subido: {archivo}")
            asyncio.run_coroutine_threadsafe(
                self.client.send_message(
                    self.entity,
                    f"📤 Archivo subido al WebDAV:\n`{archivo}`",
                    parse_mode="markdown"
                ),
                self.loop  # <--- ¡Este es el cambio importante!
            )
    
    def on_deleted(self, event):
        if not event.is_directory:
            archivo = os.path.relpath(event.src_path, CARPETA_WATCH)
            print(f"🗑️ Archivo eliminado: {archivo}")
            asyncio.run_coroutine_threadsafe(
                self.client.send_message(
                    self.entity,
                    f"🗑️ Archivo eliminado del WebDAV:\n`{archivo}`",
                    parse_mode="markdown"
                ),
                self.loop  # <--- ¡Este es el cambio importante!
            )

async def iniciar_monitor_subidas(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    loop = asyncio.get_event_loop()
    event_handler = SubidaHandler(client, entity, loop)
    observer = Observer()
    observer.schedule(event_handler, CARPETA_WATCH, recursive=True)
    observer.start()
    await client.send_message(entity, f"👁️ Observando las copias de seguridad de: {CARPETA_WATCH}", parse_mode="markdown")

# Fin del watcher

# GESTORES DE ARCHIVOS Y CARPETAS
# Listar directorios
def listar_subcarpetas(ruta):
    try:
        return [
            nombre for nombre in os.listdir(ruta)
            if os.path.isdir(os.path.join(ruta, nombre))
        ]
    except Exception:
        return []

# Listar archivos
def listar_archivos(carpeta):
    try:
        archivos = [
            archivo for archivo in os.listdir(carpeta)
            if os.path.isfile(os.path.join(carpeta, archivo))
        ]
        return archivos
    except Exception as e:
        print(f"❌ Error al listar archivos en '{carpeta}': {e}")
        return []

# Limpiador de la carpeta tmp
def limpiar_tmp():
    try:
        for archivo in os.listdir(TELEGRAM_DAEMON_TEMP):
            ruta_archivo = os.path.join(TELEGRAM_DAEMON_TEMP, archivo)
            if os.path.isfile(ruta_archivo) or os.path.islink(ruta_archivo):
                os.unlink(ruta_archivo)
            elif os.path.isdir(ruta_archivo):
                shutil.rmtree(ruta_archivo)
        return True
    except Exception as e:
        print(f"Error al limpiar TMP: {e}")
        return False

# Mover los archivos completados que no se hayan pasado al directorio final por X motivo
def mover_archivos_completados():
    global descargas_activas
    contador = 0
    errores = []
    origen_base = TELEGRAM_DAEMON_TEMP

    for nombre, info in list(descargas_activas.items()):
        if info.get("progreso") == 100:
            ruta_origen = os.path.join(origen_base, nombre)

            if os.path.exists(ruta_origen):
                try:
                    # Intentar montar disco si no está montado
                    while not os.path.exists(RUTA_ACTUAL):
                        montar_disco_duro()
                    destino = os.path.join(RUTA_ACTUAL, nombre)
                    shutil.move(ruta_origen, destino)
                    del descargas_activas[nombre]
                    contador += 1

                except Exception as e:
                    errores.append(f"❌ Error al mover `{nombre}`: {e}")
            else:
                errores.append(f"⚠️ Archivo no encontrado: `{ruta_origen}`")

    return contador, errores

#FIN GESTORES DE ARCHIVOS Y CARPETAS

# GESTORES DEL NOMBRE DEL ARCHIVO
# Getter del nombre del archivo enviado
def get_filename_from_message(message):
    # Si es un documento con atributos, tratamos de sacar el filename
    print(message)
    print(message.to_dict())
    if message.document:
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name

        # Si no hay nombre, tratamos de deducirlo por el mime_type
        ext = guess_extension(message.document.mime_type or "")
        return f"archivo_{message.id}{ext or ''}"

    # Si es foto
    if message.photo:
        return f"foto_{message.id}.jpg"

    # Fallback: usar texto si existe
    if message.message:
        nombre = message.message.strip()
        if len(nombre) < 64:  # evitar que el texto sea demasiado largo
            return nombre + ".txt"

    # Último recurso
    return f"archivo_{message.id}"


# Comprueba que el nombre del fichero no exista y si existe, lo modifica
def generar_nombre_unico(ruta_carpeta, ruta_temporal, nombre_archivo):
    nombre, extension = os.path.splitext(nombre_archivo)
    contador = 1
    nuevo_nombre = nombre_archivo

    while os.path.exists(os.path.join(ruta_carpeta, nuevo_nombre)):
        nuevo_nombre = f"{nombre} ({contador}){extension}"
        contador += 1
    
    while os.path.exists(os.path.join(ruta_temporal, nuevo_nombre)):
        nuevo_nombre = f"{nombre} ({contador}){extension}"
        contador += 1

    return nuevo_nombre

# FIN DE LOS GESTORES DEL NOMBRE DEL ARCHIVO

# GESTORES DE SERVICIOS
# Comprobador de servicios en ejecución
def comprobar_servicio(nombre):
    try:
        resultado = subprocess.run(
            ["sudo", "systemctl", "is-active", nombre],
            capture_output=True,
            text=True
        )
        estado = resultado.stdout.strip()
        if estado == "active":
            return f"✅ {nombre} está activo."
        else:
            return f"❌ {nombre} está detenido o fallando."
    except Exception as e:
        return f"⚠️ Error al comprobar {nombre}: {str(e)}"

# Reiniciador de servicios
async def reiniciar_servicio(nombre, event):
    try:
        subprocess.run(["sudo", "systemctl", "restart", nombre], check=True)
        await event.respond(f"✅ Servicio `{nombre}` reiniciado correctamente.")
    except subprocess.CalledProcessError:
        await event.respond(f"❌ Error al reiniciar el servicio `{nombre}`.")

# Montar disco duro
def montar_disco_duro():
    ruta_montaje = "/mnt/HDD"
    dispositivo = "/dev/sda2"
    output = None

    # Comprobar si ya está montado
    if os.path.ismount(ruta_montaje):
        output = "✅ El disco ya está montado en " + ruta_montaje
    else:
        try:
            os.makedirs(ruta_montaje, exist_ok=True)
            result = subprocess.run(["sudo", "mount", dispositivo, ruta_montaje], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                output = "✅ Disco montado correctamente en " + ruta_montaje
            else:
                output = "❌ Error al montar el disco:\n" + result.stderr.decode("utf-8")
        except Exception as e:
            output = f"❌ Excepción al montar el disco: {str(e)}"
    time.sleep(1)
    return output

def comprobar_disco_duro():
    commandos = 'lsblk -o UUID,MOUNTPOINT | grep /mnt/HDD'
    result = subprocess.run([commandos], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pic = result.stdout.decode('utf-8')
    output = None
    
    if not pic:
        commandos = 'lsblk -o UUID,MOUNTPOINT | grep 01D4196A967D2A40'
        result = subprocess.run([commandos], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pic2 = result.stdout.decode('utf-8')
        if not pic2:
            output = "❌ Disco duro no conectado"
        else:
            output = "⚠️ Disco duro conectado pero no montado"
    else:
        output = "✅ Disco montado correctamente en /mnt/HDD"
    return output

#FIN GESTORES


# PSEUDO-MAIN
with TelegramClient(getSession(), TELEGRAM_DAEMON_API_ID, TELEGRAM_DAEMON_API_HASH,
                    proxy=proxy).start() as client:

    saveSession(client.session)
    start_time = datetime.now()

    queue = asyncio.Queue()
    peerChannel = PeerChannel(TELEGRAM_DAEMON_CHANNEL)

    @client.on(events.NewMessage())
    async def handler(event):
        global RUTA_ACTUAL, modo, DIRECTORIO_TEMPORAL, DESTINOS_DISPONIBLES, descargas_activas, archivo_en_edicion
        # Ignorar mensajes antiguos anteriores al arranque
        if event.message.date.replace(tzinfo=None) < start_time:
            return

        if event.to_id != peerChannel:
            return

        print(event)
        output = None
        try:

            if not event.media and event.message:
                texto_original = event.message.message
                command = texto_original.lower()
                print(f"[DEBUG] Comando recibido: '{command}'")

                if command == "status":
                    if not descargas_activas:
                        output = "✅ Bot activo.\n📥 No hay descargas activas."
                    else:
                        output = f"✅ Bot activo.\n📥 Descargas activas ({len(descargas_activas)}):\n"
                        for nombre, info in descargas_activas.items():
                            output += f"• {nombre} – {info['progreso']}%\n--📁 Descargándose en: {info['ruta']}\n"
                    # Mostrar elementos en cola
                    tamaño_cola = queue.qsize()
                    if tamaño_cola > 0:
                        output += f"\n⏳ Archivos en cola: {tamaño_cola}\n"
                        for i, (c, m, cid) in enumerate(queue._queue, start=1):
                            try:
                                archivo = get_filename_from_message(m)
                            except:
                                archivo = "Archivo"
                            output += f"  {i}. {archivo}\n"

                elif command == "estado servicios":
                    estados = [
                        comprobar_servicio("ps3netsrv"),
                        comprobar_servicio("minidlna"),
                        comprobar_servicio("smbd"),
                        comprobar_servicio("apache2")
                    ]
                    output = "\n".join(estados)

                elif command.startswith("reiniciar servicio"):
                    partes = command.split()
                    if len(partes) < 3:
                        await log_reply(event.message, "❌ Especifica un servicio. Ej: `reiniciar servicio telebot`")
                        return
                    nombre_servicio = partes[2]
                    output = f"⏳ Tratando de reiniciar el servicio `{nombre_servicio}`"
                    await log_reply(event.message, output)
                    await reiniciar_servicio(nombre_servicio, event)

                elif command.startswith("👁️ Observando ") or command.startswith("📤 Archivo subido al ") or command.startswith("🗑️ Archivo eliminado "):
                    output = None
                
                elif command == "limpiar temp":
                        if limpiar_tmp():
                            output = "🧹 TMP limpiada correctamente."
                        else:
                            output = "❌ Error al limpiar la carpeta TMP."
                
                elif command == "mover completados":
                    contador, errores = mover_archivos_completados()
                    lineas = []

                    if contador:
                        lineas.append(f"✅ {contador} archivo(s) movido(s) al destino.")
                    else:
                        lineas.append("📁 No hay archivos con progreso del 100% para mover.")

                    if errores:
                        lineas.append("")  # línea en blanco
                        lineas.extend(errores)

                    output = "\n".join(lineas)

                elif command == "disco duro":
                    output = comprobar_disco_duro()
                
                elif command == "montar disco" or command == "montar disco duro":
                    output = montar_disco_duro()
                
                elif command == "reiniciar":
                    await log_reply(event.message, "🔄 Reiniciando Raspberry Pi...")
                    subprocess.run(["sudo", "reboot"])
                
                elif command == "ruta de descarga" or command == "ruta":
                    await log_reply(event.message, f"🛠️ Ruta de descarga actual:`{RUTA_ACTUAL}`")
                
                elif command == "borrar historial":
                    try:
                        await log_reply(event.message, "🧹 Borrando historial del bot...")
                        count = 0
                        async for msg in client.iter_messages(event.chat_id, from_user='me', limit=500):
                            await msg.delete()
                            count += 1
                        await client.send_message(event.chat_id, f"✅ Historial del bot borrado ({count} mensajes).")
                    except Exception as e:
                        await client.send_message(event.chat_id, f"❌ Error al borrar historial: {str(e)}")

                elif command == "cambiar ruta de descarga":
                    if not descargas_activas:
                        output = "✅ Bot activo.\n📥 No hay descargas activas."
                    else:
                        modo = "changing_routes"
                        output = "🛠️ ¿A qué archivo le quieres cambiar la ruta?\n\n"
                        for i, (nombre, info) in enumerate(descargas_activas.items(), start=1):
                            output += f"📥 {i} - {nombre} | {info['progreso']}%\n-- 📁 Descargándose en: {info['ruta']}\n"
                
                elif modo == "changing_routes":
                    archivos_descargandose = list(descargas_activas.keys())
                    output = "❌ Índice no válido"
                    try:
                        index = int(command) - 1
                        if 1 <= index <= len(archivos_descargandose):
                            modo = "waiting_change"
                            archivo_en_edicion = archivos_descargandose[index]
                            ruta_archivo = descargas_activas[archivo_en_edicion]['ruta']
                            output = f"📤 Archivo seleccionado: {archivo_en_edicion}\n📁 Descargándose en: {ruta_archivo}\n🛠️ ¿Dónde quieres que se descargue?\n"
                            lista = "\n".join([f"• `{nombre}` → `{ruta}`" for nombre, ruta in DESTINOS_DISPONIBLES.items()])
                            await event.respond(f"📁 Directorios disponibles:\n\n{lista}")
                    except ValueError:
                        modo = None
                
                elif modo == "waiting_change":
                    nueva_ruta = DESTINOS_DISPONIBLES.get(command)

                    if nueva_ruta:
                        descargas_activas[archivo_en_edicion]["ruta"] = nueva_ruta
                        output = f"✅ Ruta de descarga actualizada a:\n`{nueva_ruta}`"
                    else:
                        output = f"❌ Ruta no válida. Usa un nombre del listado."

                    archivo_en_edicion = None
                    modo = None

                elif command.startswith("descargar enlace"):
                    try:
                        partes = command.split()
                        if len(partes) < 3:
                            output = "❌ Formato incorrecto. Usa: descargar enlace https://t.me/canal/1234"
                        else:
                            enlace = partes[2]
                            if "t.me/" not in enlace:
                                output = "❌ Enlace inválido."
                            else:
                                ruta = enlace.split("t.me/")[1]  # canal/1234 o c/12345678/1234
                                partes_ruta = ruta.strip("/").split("/")

                                if len(partes_ruta) == 2:
                                    # Ej: t.me/mi_canal/1234
                                    canal_nombre = partes_ruta[0]
                                    mensaje_id = int(partes_ruta[1])
                                    mensaje_objetivo = await client.get_messages(canal_nombre, ids=mensaje_id)

                                elif len(partes_ruta) == 3 and partes_ruta[0] == "c":
                                    # Ej: t.me/c/12345678/1234
                                    canal_id = int(partes_ruta[1])
                                    mensaje_id = int(partes_ruta[2])
                                    entity = PeerChannel(canal_id)
                                    mensaje_objetivo = await client.get_messages(entity, ids=mensaje_id)

                                else:
                                    output = "❌ Formato de enlace no reconocido."
                                    mensaje_objetivo = None

                                # Descargar si hay media
                                if mensaje_objetivo and mensaje_objetivo.media:
                                    await event.reply("📥 Archivo añadido a la cola de descargas.")
                                    await queue.put((client, mensaje_objetivo, event.chat_id))
                                else:
                                    output = "⚠️ El mensaje no tiene contenido descargable."
                    except Exception as e:
                        output = f"❌ Error al procesar el enlace: {str(e)}"
                
                elif command == "listar rutas":
                    lista = "\n".join([f"• `{nombre}` → `{ruta}`" for nombre, ruta in DESTINOS_DISPONIBLES.items()])
                    output = f"📁 Directorios disponibles:\n\n{lista}"
                
                elif command == "listar subcarpetas":
                    subcarpetas = listar_subcarpetas(RUTA_ACTUAL)
                    if subcarpetas:
                        lista = "\n• " + "\n• ".join(subcarpetas)
                        output = f"📁 Subcarpetas disponibles en `{RUTA_ACTUAL}`:{lista}\n"
                    else:
                        output = f"ℹ️ No se encontraron subcarpetas en `{RUTA_ACTUAL}`. ¿Quieres crear una nueva?"
                        modo = "subcarpeta alt"
                
                elif command == "listar contenido":
                    subcarpetas = listar_subcarpetas(RUTA_ACTUAL)
                    archivos = listar_archivos(RUTA_ACTUAL)

                    output = f"ℹ️ Contenido de `{RUTA_ACTUAL}`:\n"

                    if subcarpetas:
                        lista_subs = "\n📁 " + "\n📁 ".join(subcarpetas)
                        output += f"\n📁 **Subcarpetas**:{lista_subs}"
                    else:
                        output += "\n📁 No hay subcarpetas."

                    if archivos:
                        lista_archivos = "\n📄 " + "\n📄 ".join(archivos)
                        output += f"\n\n📄 **Archivos**:{lista_archivos}"
                    else:
                        output += "\n\n📄 No hay archivos."

                elif command == "cambiar ruta":
                    modo = "esperando_carpeta"
                    output = f"🛠️ ¿Dónde quieres guardar las descargas?"
                    await log_reply(event.message, output)
                    lista = "\n".join([f"• `{nombre}` → `{ruta}`" for nombre, ruta in DESTINOS_DISPONIBLES.items()])
                    await event.respond(f"📁 Directorios disponibles:\n\n{lista}")

                elif modo == "esperando_carpeta":
                    desti = [key.lower() for key in DESTINOS_DISPONIBLES.keys()]
                    if command in desti:
                        for clave in DESTINOS_DISPONIBLES:
                            if clave.lower() == command:
                                clave_real = clave
                                break
                        nueva_ruta = DESTINOS_DISPONIBLES[clave_real]
                        if os.path.exists(nueva_ruta) and os.path.isdir(nueva_ruta):
                            RUTA_ACTUAL = nueva_ruta
                            output = f"🛠️ Carpeta seleccionada: `{clave_real}` - `{RUTA_ACTUAL}`\n¿Quieres crear, usar una subcarpeta o ahí mismo?"
                            modo = "subcarpeta"
                        else:
                            modo = None
                            output = f"❌ Carpeta no válida. Ruta de descarga establecida en:\n`{RUTA_ACTUAL}`"
                    else:
                        output = f"❌ Carpeta no válida. Ruta de descarga establecida en:\n`{RUTA_ACTUAL}`"
                        modo = None
                
                elif modo and modo.startswith("subcarpeta"):
                    subcarpetas = listar_subcarpetas(RUTA_ACTUAL)
                    if "crear" in command or command == "si":
                        output = "📁 Escribe el nombre de la subcarpeta a crear:"
                        modo = "creando_subcarpeta"
                    
                    elif modo and "alt" in modo:
                        modo = None
                    
                    elif "usar" in command:
                        if subcarpetas:
                            lista = "\n• " + "\n• ".join(subcarpetas)
                            output = f"📁 Subcarpetas disponibles en `{RUTA_ACTUAL}`:{lista}\n\n✏️ Escribe una para usarla, o cualquier cosa para continuar sin subcarpeta."
                        else:
                            output = f"ℹ️ No se encontraron subcarpetas en `{RUTA_ACTUAL}`. ¿Quieres crear una nueva?"
                    
                    else:
                        sub = None
                        for item in subcarpetas:
                            if item.lower() == command:
                                sub = item
                                RUTA_ACTUAL = os.path.join(RUTA_ACTUAL, item)
                                break
                        output = f"✅ Ruta de descarga establecida en:\n`{RUTA_ACTUAL}`"
                        modo = None
                        if not sub == None:
                            output += "\n🛠️ ¿Deseas añadirla al listado de directorios disponibles?"
                            modo = "elegir_guardar_carpeta"
                            DIRECTORIO_TEMPORAL = cargar_destinos().copy()
                            DIRECTORIO_TEMPORAL[sub] = RUTA_ACTUAL

                elif modo == "creando_subcarpeta":
                    sub = texto_original
                    nueva_ruta = os.path.join(RUTA_ACTUAL, sub)
                    output = f"📁 Creando subcarpeta `{sub}` en `{nueva_ruta}`"
                    await log_reply(event.message, output)
                    os.makedirs(nueva_ruta, exist_ok=True)
                    if os.path.exists(nueva_ruta) and os.path.isdir(nueva_ruta):
                        modo = "elegir_guardar_carpeta"
                        RUTA_ACTUAL = nueva_ruta
                        await event.respond(f"✅ Subcarpeta creada y ruta establecida:\n`{RUTA_ACTUAL}`\n🛠️ ¿Deseas añadirla al listado de directorios disponibles?")
                        DIRECTORIO_TEMPORAL = cargar_destinos().copy()
                        DIRECTORIO_TEMPORAL[sub] = RUTA_ACTUAL
                        lista = "\n".join([f"• `{nombre}` → `{ruta}`" for nombre, ruta in DIRECTORIO_TEMPORAL.items()])
                    else:
                        await event.respond(f"❌ Error al crear la carpeta. Ruta de descarga establecida en:\n`{RUTA_ACTUAL}`")
                        modo = None
                
                elif modo == "elegir_guardar_carpeta":
                    if command == "guardar" or command == "añadir":
                        output = "🛠️ Guardando nueva carpeta en el directorio..."
                        await log_reply(event.message, output)
                        if DIRECTORIO_TEMPORAL is None:
                            DIRECTORIO_TEMPORAL = DESTINOS_DISPONIBLES.copy()
                        guardar_destinos(DIRECTORIO_TEMPORAL)
                        DESTINOS_DISPONIBLES = cargar_destinos()
                        lista = "\n".join([f"• `{nombre}` → `{ruta}`" for nombre, ruta in DESTINOS_DISPONIBLES.items()])
                        await event.respond(f"📁 Directorios disponibles:\n\n{lista}")
                    else:
                        output = f"✅ Ruta de descarga establecida en:\n`{RUTA_ACTUAL}`"
                    modo = None
                
                elif command == "ayuda":
                    lista = "\n\n".join([
                        f"📌 `{item['comando']}`\n   └ {item['descripcion']}"
                        for item in COMANDOS_JSON["comandos"]
                    ])
                    output = f"🛠️ *Comandos disponibles:*\n\n{lista}"

                else:
                    output = "⚠️ ¡Comando no válido! Utiliza el comando `ayuda` para ver los comandos disponibles"

                if output:
                    await log_reply(event.message, output)

            if event.media:
                await event.reply("📥 Archivo añadido a la cola de descargas.")
                await queue.put((client, event.message, event.chat_id))


        except Exception as e:
                print('Events handler error: ', e)
   
    async def update_estado(current, total, msg, filename):
        global descargas_activas
        global lastUpdate
        global updateFrequency

        porcentaje = int(current * 100 / total)
        porcentaje_anterior = descargas_activas[filename]["progreso_anterior"]
        descargas_activas[filename]["progreso"] = porcentaje

        try:
            currentTime=time.time()
            if (currentTime - lastUpdate) > updateFrequency and (porcentaje - porcentaje_anterior) > 3:
                await msg.edit(f"📥 Descargando {filename}... {porcentaje}%")
                lastUpdate=currentTime
                descargas_activas[filename]["progreso_anterior"] = porcentaje
        except FloodWait as e:
            print(f"⏳ FloodWait: esperando {e.seconds} segundos...")
            await asyncio.sleep(e.seconds)
            currentTime=time.time()
            if (currentTime - lastUpdate) > updateFrequency:
                await msg.edit(f"📥 Descargando {filename}... {porcentaje}%")
                lastUpdate=currentTime
        except Exception as e:
            if "Content of the message was not modified" not in str(e):
                raise e

    async def worker():
        while True:
            client, mensaje, chat_id = await queue.get()
            try:
                await procesar_mensaje(client, mensaje, chat_id)
            except Exception as e:
                print(f"❌ Error en worker: {e}")
            finally:
                queue.task_done()


    async def procesar_mensaje(client, mensaje, chat_id):
        import time
        global descargas_activas
        try:
            # 1. Obtener nombre del archivo y extensión
            nombre_archivo = get_filename_from_message(mensaje)
            nombre_archivo = generar_nombre_unico(RUTA_ACTUAL, TELEGRAM_DAEMON_TEMP, nombre_archivo)

            temp_path = os.path.join(TELEGRAM_DAEMON_TEMP, nombre_archivo)

            # 2. Mensaje de progreso
            msg = await client.send_message(chat_id, f"📥 Descargando {nombre_archivo}... 0%")

            # 3. Descargar con progreso en Telegram
            descargas_activas[nombre_archivo] = {
                "progreso": 0,
                "progreso_anterior": 0,
                "ruta": RUTA_ACTUAL
            }
            inicio = time.time()
            await client.download_media(
                mensaje,
                temp_path,
                progress_callback=lambda c, t: asyncio.create_task(
                    update_estado(c, t, msg, nombre_archivo)
                )
            )

            # 4. Verificar si existe el archivo descargado
            if not os.path.exists(temp_path):
                await client.send_message(chat_id, f"❌ Error: el archivo no se descargó correctamente.")
                return
            # 5. Mover al destino
            # Chequeo de destino
            
            ruta_destino = descargas_activas[nombre_archivo]["ruta"]
            final_path = os.path.join(ruta_destino, nombre_archivo)
            
            if not os.path.exists(ruta_destino):
                await client.send_message(chat_id, f"⚠️ El disco duro no está montado.\nEl archivo se ha quedado en temporal:\n`{temp_path}`")
                return

            shutil.move(temp_path, final_path)
            descargas_activas.pop(nombre_archivo, None)

            # 5.1 Calcular duración y velocidad
            fin = time.time()
            duracion = fin - inicio  # en segundos
            tamaño_MB = os.path.getsize(final_path) / (1024 * 1024)
            if duracion > 0:
                velocidad_MBps = tamaño_MB / duracion
            else:
                velocidad_MBps = 0
            await client.send_message(chat_id, f"✅ {nombre_archivo} descargado y movido correctamente.\n⏱️ Tiempo: {duracion:.1f} s\n📦 Tamaño: {tamaño_MB:.2f} MB\n🚀 Velocidad media: {velocidad_MBps:.2f} MB/s\n📂 Guardado en:\n`{final_path}`")

        except Exception as e:
            await client.send_message(chat_id, f"❌ Error al procesar el archivo: {str(e)}")

    # Función start
    async def start():
        tasks = []
        loop = asyncio.get_event_loop()
        await sendHelloMessage(client, peerChannel)
        asyncio.create_task(worker())
        asyncio.create_task(iniciar_monitor_subidas(client, peerChannel))
        await client.run_until_disconnected()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    client.loop.run_until_complete(start())
