Python
import os
import json
import requests
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])
API_KEY = os.environ["FOOTBALL_API_KEY"]

TELEGRAM = f"https://api.telegram.org/bot{TOKEN}"
API = "https://v3.football.api-sports.io"
STATE_FILE = "state.json"


def cargar_estado():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offset": 0, "partidos": [], "avisados": []}


def guardar_estado(estado):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def enviar(mensaje):
    r = requests.post(
        f"{TELEGRAM}/sendMessage",
        json={"chat_id": CHAT_ID, "text": mensaje},
        timeout=20
    )
    r.raise_for_status()


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )


def procesar_comandos(estado):
    r = requests.get(
        f"{TELEGRAM}/getUpdates",
        params={"offset": estado["offset"] + 1, "timeout": 0},
        timeout=20
    )
    r.raise_for_status()

    datos = r.json()

    if not datos.get("ok"):
        raise RuntimeError(str(datos))

    for update in datos.get("result", []):
        estado["offset"] = update["update_id"]

        mensaje = update.get("message", {})
        chat = str(mensaje.get("chat", {}).get("id", ""))

        if chat != CHAT_ID:
            continue

        texto = mensaje.get("text", "").strip()
        if not texto:
            continue

        partes = texto.split(maxsplit=1)
        comando = partes[0].split("@")[0].lower()

        if comando in ("/start", "/ayuda"):
            enviar(
                "¡Hola! ⚽ Soy tu bot de alertas.\n\n"
                "Comandos disponibles:\n"
                "/anadir Equipo - Equipo\n"
                "/lista\n"
                "/borrar NUMERO\n"
                "/ayuda\n\n"
                "Te avisaré de tus partidos."
            )

        elif comando == "/anadir":
            if len(partes) < 2 or " - " not in partes[1]:
                enviar("Usa: /anadir Real Madrid - Barcelona")
                continue

            local, visitante = partes[1].split(" - ", 1)
            local = local.strip()
            visitante = visitante.strip()

            if not local or not visitante:
                enviar("Escribe los dos equipos.")
                continue

            partido = {
                "local": local,
                "visitante": visitante
            }

            if partido not in estado["partidos"]:
                estado["partidos"].append(partido)
                enviar(f"Añadido: {local} - {visitante} ⚽")
            else:
                enviar("Ese partido ya está en tu lista.")

        elif comando == "/lista":
            if not estado["partidos"]:
                enviar("Todavía no tienes partidos añadidos.")
            else:
                lista = "\n".join(
                    f"{i + 1}. {p['local']} - {p['visitante']}"
                    for i, p in enumerate(estado["partidos"])
                )
                enviar("Tus partidos:\n" + lista)

        elif comando == "/borrar":
            if len(partes) < 2 or not partes[1].isdigit():
                enviar("Usa: /borrar NUMERO")
                continue

            numero = int(partes[1]) - 1

            if 0 <= numero < len(estado["partidos"]):
                eliminado = estado["partidos"].pop(numero)
                enviar(
                    f"Eliminado: {eliminado['local']} - "
                    f"{eliminado['visitante']}"
                )
            else:
                enviar("Ese número no existe.")


def comprobar_partidos(estado):
    if not estado["partidos"]:
        return

    hoy = datetime.now(
        ZoneInfo("Europe/Madrid")
    ).strftime("%Y-%m-%d")

    r = requests.get(
        f"{API}/fixtures",
        headers={"x-apisports-key": API_KEY},
        params={"date": hoy, "timezone": "Europe/Madrid"},
        timeout=30
    )
    r.raise_for_status()

    datos = r.json()

    if datos.get("errors"):
        raise RuntimeError(str(datos["errors"]))

    for partido in datos.get("response", []):
        fixture = partido["fixture"]
        equipos = partido["teams"]
        goles = partido["goals"]

        minuto = fixture["status"]["elapsed"] or 0
        estado_partido = fixture["status"]["short"]

        local = equipos["home"]["name"]
        visitante = equipos["away"]["name"]

        for elegido in estado["partidos"]:
            coincide = (
                normalizar(elegido["local"]) in normalizar(local)
                and normalizar(elegido["visitante"]) in normalizar(visitante)
            )

            if not coincide:
                continue

            if minuto >= 75 and estado_partido in ("2H", "ET", "FT"):
                identificador = str(fixture["id"])

                if identificador not in estado["avisados"]:
                    enviar(
                        "⚽ ¡ALERTA MINUTO 75!\n\n"
                        f"{local} {goles['home']} - "
                        f"{goles['away']} {visitante}\n"
                        f"Minuto: {minuto}'"
                    )
                    estado["avisados"].append(identificador)


def main():
    estado = cargar_estado()
    procesar_comandos(estado)
    comprobar_partidos(estado)
    guardar_estado(estado)


if __name__ == "__main__":
    main()

