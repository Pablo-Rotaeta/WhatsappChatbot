# utils.py
import importlib.util
import os
from modules.config import RUTA_DB, DEBUG

def verificar_dependencias():
    print("[VERIF] Verificando dependencias...")
    required = ["selenium", "requests", "schedule", "google.generativeai"]
    missing = []
    for mod in required:
        if not importlib.util.find_spec(mod):
            missing.append(mod)

    if missing:
        print("[VERIF] Faltan: " + ", ".join(missing))
        return False

    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    return True

def limpiar_texto_unicode(texto):
    return ''.join(c for c in texto if ord(c) <= 0xFFFF)

def cargar_configuracion():
    from dotenv import load_dotenv
    load_dotenv()
    if DEBUG:
        print("[CONF] Variables de entorno cargadas.")
