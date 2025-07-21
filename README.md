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
whatsapp_llm_bot/
├── whatsapp_bot.py                  ← Script principal CLI
├── .env                             ← Variables de entorno
├── requirements.txt                 ← Librerías necesarias
├── README.md                        ← Documentación general
├── prompts/
│   └── extract_prompt.txt           ← Prompt reutilizable para LLM
├── modules/
│   ├── __init__.py (opcional)
│   ├── automation.py                ← Selenium: conexión a WhatsApp
│   ├── config.py                    ← Carga de configuración global
│   ├── database.py                  ← Operaciones con SQLite
│   ├── llm_extractor.py            ← Gemini / LLM parsing
│   ├── scraper.py                   ← Scraping de mensajes
│   ├── sender.py                    ← Envío de mensajes y resumen
│   ├── scheduler.py                 ← Tareas automáticas programadas
│   └── utils.py                     ← Utilidades (verificación, unicode)

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
