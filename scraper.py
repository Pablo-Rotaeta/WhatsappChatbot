# scraper.py
import time
from modules.database import crear_tabla_mensajes, mensaje_ya_existe, insertar_mensaje_bd, obtener_mensajes_del_dia
from modules.llm_extractor import extraer_campos_con_llm
from modules.automation import inicializar_navegador, abrir_whatsapp_web, abrir_canal, extraer_mensajes
from modules.config import CANAL_ORIGEN, DEBUG


def ejecutar_scraping_completo():
    crear_tabla_mensajes()
    driver = inicializar_navegador()
    try:
        abrir_whatsapp_web(driver)
        if not abrir_canal(driver, CANAL_ORIGEN):
            return False
        mensajes = extraer_mensajes(driver)
        nuevos = 0
        for mensaje in mensajes:
            if mensaje_ya_existe(mensaje):
                continue
            datos = extraer_campos_con_llm(mensaje)
            if insertar_mensaje_bd(mensaje, CANAL_ORIGEN, datos):
                nuevos += 1
        if DEBUG:
            print(f"[SCRAPER] {nuevos} nuevos mensajes procesados.")
        return True
    except Exception as e:
        print(f"[SCRAPER] Error: {e}")
        return False
    finally:
        driver.quit()


def scraping_hasta_no_haber_nuevos(max_intentos=3):
    anteriores = len(obtener_mensajes_del_dia())
    for i in range(max_intentos):
        ejecutar_scraping_completo()
        actuales = len(obtener_mensajes_del_dia())
        if actuales == anteriores:
            break
        anteriores = actuales
        time.sleep(3)
