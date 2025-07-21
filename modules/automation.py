# automation.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
from modules.config import RUTA_SESION_CHROME, DEBUG

def inicializar_navegador():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={RUTA_SESION_CHROME}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1200, 800)
    if DEBUG:
        print("[SELENIUM] Navegador iniciado.")
    return driver

def abrir_whatsapp_web(driver):
    driver.get("https://web.whatsapp.com")
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']"))
        )
        if DEBUG:
            print("[WHATSAPP] WhatsApp Web cargado correctamente.")
    except Exception:
        print("[WHATSAPP] No se pudo cargar la interfaz de WhatsApp.")

def abrir_canal(driver, nombre):
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, f"//span[contains(text(), '{nombre}')]"))
        ).click()
        if DEBUG:
            print(f"[WHATSAPP] Canal '{nombre}' abierto.")
        time.sleep(2)
        return True
    except Exception:
        print(f"[WHATSAPP] No se pudo abrir el canal: {nombre}")
        return False

def extraer_mensajes(driver):
    try:
        elems = driver.find_elements(By.XPATH, "//div[contains(@class, 'copyable-text')]")
        mensajes = [e.text.strip() for e in elems if len(e.text.strip()) > 10]
        if DEBUG:
            print(f"[WHATSAPP] {len(mensajes)} mensajes extra\u00eddos.")
        return mensajes
    except Exception as e:
        print(f"[WHATSAPP] Error extrayendo mensajes: {e}")
        return []

def enviar_mensaje(driver, texto):
    try:
        caja = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//footer//div[@contenteditable='true']"))
        )
        caja.click()
        for linea in texto.splitlines():
            caja.send_keys(linea)
            caja.send_keys(Keys.SHIFT + Keys.ENTER)
        caja.send_keys(Keys.ENTER)
        if DEBUG:
            print("[WHATSAPP] Mensaje enviado.")
        return True
    except Exception as e:
        print(f"[WHATSAPP] Error enviando mensaje: {e}")
        return False
