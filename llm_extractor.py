# llm_extractor.py
import json
import google.generativeai as genai
from modules.config import GEMINI_API_KEY, GEMINI_MODEL_NAME, DEBUG

# Configurar Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
else:
    GEMINI_MODEL = None


def cargar_prompt():
    with open("prompts/extract_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()


def crear_prompt_extraccion(mensaje):
    base_prompt = cargar_prompt()
    return base_prompt.replace("{{MENSAJE}}", mensaje.strip())


def extraer_campos_con_llm(mensaje):
    if not GEMINI_MODEL:
        print("[LLM] No hay modelo Gemini configurado.")
        return {}

    prompt = crear_prompt_extraccion(mensaje)
    try:
        respuesta = GEMINI_MODEL.generate_content(prompt)
        texto = respuesta.text.strip()

        if texto.startswith("```"):
            texto = texto.replace("```json", "").replace("```", "").strip()

        if DEBUG:
            print("[LLM] Respuesta cruda:", texto[:300])

        json_ini = texto.find('{')
        json_fin = texto.rfind('}') + 1
        if json_ini == -1:
            raise ValueError("No se encontró JSON en la respuesta")

        return json.loads(texto[json_ini:json_fin])

    except Exception as e:
        print(f"[LLM] Error al procesar respuesta: {e}")
        return {}
