# sender.py
import time
from datetime import datetime
from modules.database import obtener_mensajes_del_dia
from modules.automation import inicializar_navegador, abrir_whatsapp_web, abrir_canal, enviar_mensaje
from modules.utils import limpiar_texto_unicode
from modules.config import CANAL_DESTINO, DEBUG


def enviar_mensajes_individuales():
    mensajes = obtener_mensajes_del_dia()
    if not mensajes:
        print("[ENVIAR] No hay mensajes para enviar.")
        return False
    driver = inicializar_navegador()
    try:
        abrir_whatsapp_web(driver)
        if not abrir_canal(driver, CANAL_DESTINO):
            return False
        for m in mensajes:
            enviar_mensaje(driver, m[2])
            time.sleep(2)
        return True
    finally:
        driver.quit()


def generar_y_enviar_resumen_diario():
    mensajes = obtener_mensajes_del_dia()
    if not mensajes:
        print("[RESUMEN] No hay mensajes hoy.")
        return False

    resumen = ["**RESUMEN DE OPORTUNIDADES DEL DÍA**",
               f"Fecha: {datetime.now().strftime('%d/%m/%Y')}",
               f"Total: {len(mensajes)}", ""]

    for i, m in enumerate(mensajes, 1):
        resumen.extend([
            f"OPORTUNIDAD {i}",
            f"- País: {m[3] or 'No especificado'}",
            f"- Ciudad: {m[4] or 'No especificado'}",
            f"- Fecha Inicio: {m[5] or 'No especificada'}",
            f"- Fecha Fin: {m[6] or 'No especificada'}",
            f"- Fecha Límite: {m[7] or 'No especificada'}",
            f"- Temática: {m[8] or 'No especificada'}",
        ])
        if m[9]: resumen.append(f"- Infopack: {m[9]}")
        if m[10]: resumen.append(f"- Formulario: {m[10]}")
        if m[11]: resumen.append(f"- Contacto: {m[11]}")
        resumen.append("".join(["-" * 20, "\n"]))

    resumen.append("Generado automáticamente por el bot.")
    resumen_txt = limpiar_texto_unicode("\n".join(resumen))

    driver = inicializar_navegador()
    try:
        abrir_whatsapp_web(driver)
        if not abrir_canal(driver, CANAL_DESTINO):
            return False
        enviar_mensaje(driver, resumen_txt)
        return True
    finally:
        driver.quit()
