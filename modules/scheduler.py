# scheduler.py
import schedule
import time
from modules.scraper import ejecutar_scraping_completo
from modules.sender import enviar_mensajes_individuales, generar_y_enviar_resumen_diario
from modules.config import HORARIOS_SCRAPING, HORARIOS_ENVIO, HORARIO_RESUMEN, DEBUG


def configurar_horarios_automaticos():
    for hora in HORARIOS_SCRAPING:
        schedule.every().day.at(hora).do(ejecutar_scraping_completo)
        if DEBUG:
            print(f"[SCHEDULE] Scraping programado: {hora}")

    for hora in HORARIOS_ENVIO:
        schedule.every().day.at(hora).do(enviar_mensajes_individuales)
        if DEBUG:
            print(f"[SCHEDULE] Envío programado: {hora}")

    schedule.every().day.at(HORARIO_RESUMEN).do(generar_y_enviar_resumen_diario)
    if DEBUG:
        print(f"[SCHEDULE] Resumen programado: {HORARIO_RESUMEN}")


def ejecutar_bucle_automatico():
    print("[AUTO] Iniciando bot automático...")
    while True:
        schedule.run_pending()
        time.sleep(30)
