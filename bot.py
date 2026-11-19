import os
import json
import requests
from datetime import datetime, timezone

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_KEY = os.environ.get("FOOTBALL_API_KEY", "")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
FOOTBALL_URL = "https://v3.football.api-sports.io/fixtures"

def enviar(mensaje):
    requests.post(
        TELEGRAM_URL,
        data={"chat_id": CHAT_ID, "text": mensaje},
        timeout=20
    ).raise_for_status()

def consultar_partidos():
    if not API_KEY:
        print("Falta configurar FOOTBALL_API_KEY")
        return

    hoy = datetime.now().strftime("%Y-%m-%d")

    respuesta = requests.get(
        FOOTBALL_URL,
        headers={"x-apisports-key": API_KEY},
        params={"date": hoy},
        timeout=30
    )
    respuesta.raise_for_status()

    partidos = respuesta.json().get("response", [])

    for partido in partidos:
        estado = partido["fixture"]["status"]
        minuto = estado.get("elapsed")
        estado_corto = estado.get("short")

        if minuto == 75 and estado_corto == "2H":
            local = partido["teams"]["home"]["name"]
            visitante = partido["teams"]["away"]["name"]
            goles_local = partido["goals"]["home"]
            goles_visitante = partido["goals"]["away"]

            enviar(
                f"⚽ MINUTO 75\n\n"
                f"{local} {goles_local} - "
                f"{goles_visitante} {visitante}"
            )

if __name__ == "__main__":
    consultar_partidos()

