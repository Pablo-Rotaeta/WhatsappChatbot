# config.py
import os
from dotenv import load_dotenv

load_dotenv()

CANAL_ORIGEN = os.getenv("CANAL_ORIGEN", "CanalOrigen")
CANAL_DESTINO = os.getenv("CANAL_DESTINO", "CanalDestino")
RUTA_SESION_CHROME = os.getenv("RUTA_SESION_CHROME", "./whatsapp_data")
RUTA_DB = os.getenv("RUTA_DB", "./data/mensajes.db")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

HORARIOS_SCRAPING = os.getenv("HORARIOS_SCRAPING", "08:00,13:00,17:00").split(",")
HORARIOS_ENVIO = os.getenv("HORARIOS_ENVIO", "08:10,13:10,17:10").split(",")
HORARIO_RESUMEN = os.getenv("HORARIO_RESUMEN", "20:00")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-1.5-flash-8b"
