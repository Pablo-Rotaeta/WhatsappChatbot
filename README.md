# WhatsApp LLM Bot

Un sistema automatizado que extrae mensajes de canales de WhatsApp, los analiza usando un modelo de lenguaje (Gemini) y redistribuye la información estructurada.

## Características

- Automatización con Selenium (WhatsApp Web)
- Extracción de datos con Google Gemini
- Almacenamiento en SQLite
- Envío automatizado de mensajes o resúmenes
- Programación de tareas
- Estructura modular y extensible

## Estructura del Proyecto

```
modules/
├── automation.py # Selenium
├── database.py # SQLite
├── llm_extractor.py # Gemini LLM
├── scheduler.py # Tareas
└── utils.py # Hashes, normalización
```

## Configuración

1. Clona el repositorio
2. Crea el archivo `.env` con tus datos
3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

```
python whatsapp_bot.py --scraper       # Extrae mensajes
python whatsapp_bot.py --send          # Envía individualmente
python whatsapp_bot.py --resumen       # Envía resumen diario
python whatsapp_bot.py --auto          # Modo automático
```
