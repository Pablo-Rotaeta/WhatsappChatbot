#!/usr/bin/env python3
"""
WhatsApp LLM Bot - Sistema Automatizado de Agregación y Redistribución
======================================================================

Este bot automatiza la captura, el procesamiento y la redistribución de mensajes de WhatsApp
utilizando un modelo de lenguaje para extraer información estructurada y almacenarla en una base de datos.

FLUJO PRINCIPAL:
1. Conexión a WhatsApp Web mediante Selenium.
2. Extracción de mensajes desde un canal origen.
3. Procesamiento de cada mensaje con un modelo LLM local (Ollama/Llama).
4. Almacenamiento de la información estructurada en SQLite.
5. Redistribución del contenido a un canal destino.

DEPENDENCIAS:
- selenium: automatización del navegador.
- requests: comunicación con la API de Llama.
- sqlite3: base de datos local.
- schedule: programación de tareas.
- hashlib: detección de duplicados.
"""

import sqlite3
import requests
import json
import time
import argparse
import schedule
import google.generativeai as genai
from datetime import datetime
from hashlib import sha256
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# ============================================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================================

# Nombre del canal de WhatsApp del cual se extraerán los mensajes.
CANAL_ORIGEN = "Prueba Pablo"

# Nombre del canal de WhatsApp al cual se enviarán los mensajes procesados.
CANAL_DESTINO = "Test Pablo"

# Directorio para guardar la sesión persistente de Chrome.
RUTA_SESION_CHROME = "./whatsapp_data"

# Ruta al archivo de la base de datos SQLite donde se almacenarán los mensajes.
RUTA_DB = "./data/mensajes.db"

# Configuración de la API de Google Gemini
genai.configure(api_key="AIzaSyDvAvcTcvDUou8-1QXvQd5o_7UFV54p2G")
GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash-8b")

# Horarios programados para las diferentes tareas del bot.
HORARIOS_SCRAPING = ["08:00", "13:00", "17:00"]  # Horarios para extraer mensajes.
HORARIOS_ENVIO = ["08:10", "13:10", "17:10"]     # Horarios para enviar mensajes (10 minutos después).
HORARIO_RESUMEN = "20:00"                        # Horario para enviar el resumen diario.

# Flag de depuración. Si está en True, se imprimirán logs detallados en consola.
DEBUG = True

# ============================================================================
# MÓDULO DE BASE DE DATOS
# ============================================================================

def conectar_bd():
    """
    Establece la conexión con la base de datos SQLite.
    Si la carpeta del archivo no existe, la crea.
    
    Returns:
        sqlite3.Connection: Conexión a la base de datos.
    """
    import os
    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    return sqlite3.connect(RUTA_DB)


def crear_tabla_mensajes():
    """
    Crea la tabla 'mensajes' en la base de datos si no existe.
    Define los campos necesarios para almacenar la información estructurada extraída.

    Campos de la tabla:
        - id: identificador único (autoincremental)
        - fecha: timestamp de cuando se guardó el mensaje
        - texto: contenido original del mensaje
        - pais: país extraído (en español)
        - ciudad: ciudad o localidad extraída
        - fecha_inicio: fecha de inicio del evento (DD/MM/AAAA)
        - fecha_fin: fecha de fin del evento (DD/MM/AAAA)
        - fecha_limite_inscripcion: fecha límite de inscripción (DD/MM/AAAA)
        - tematica: tema o categoría extraída
        - infopack: URL o referencia a información adicional
        - formulario: enlace al formulario de inscripción
        - contacto: información de contacto extraída
        - canal: nombre del canal de WhatsApp de origen
        - hash: hash SHA256 del texto (para evitar duplicados)
    """
    conn = conectar_bd()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME,
            texto TEXT,
            pais TEXT,
            ciudad TEXT,
            fecha_inicio TEXT,
            fecha_fin TEXT,
            fecha_limite_inscripcion TEXT,
            tematica TEXT,
            infopack TEXT,
            formulario TEXT,
            contacto TEXT,
            canal TEXT,
            hash TEXT UNIQUE
        )
    ''')

    conn.commit()
    conn.close()
    if DEBUG:
        print("Tabla de mensajes creada o verificada correctamente.")


def generar_hash_mensaje(texto):
    """
    Genera un hash SHA256 único para el texto del mensaje.
    Esto permite detectar y evitar la inserción de mensajes duplicados.
    
    Args:
        texto (str): Contenido del mensaje.
    
    Returns:
        str: Hash SHA256 del texto.
    """
    return sha256(texto.encode("utf-8")).hexdigest()


def mensaje_ya_existe(hash_mensaje):
    """
    Verifica si un mensaje con el hash dado ya existe en la base de datos.
    
    Args:
        hash_mensaje (str): Hash SHA256 del mensaje.
    
    Returns:
        bool: True si el mensaje ya está registrado, False en caso contrario.
    """
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mensajes WHERE hash=?", (hash_mensaje,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


def limpiar_campo_extraido(valor):
    """
    Normaliza los valores extraídos por el modelo LLM.
    - Convierte None en None.
    - Serializa diccionarios como cadenas JSON.
    - Convierte listas/tuplas en cadenas separadas por comas.
    - Elimina espacios innecesarios.
    
    Args:
        valor: valor extraído por el LLM (puede ser None, dict, list, str).
    
    Returns:
        str | None: Valor limpio y listo para almacenar en la base de datos.
    """
    if valor is None:
        return None
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, (list, tuple)):
        return ", ".join(str(v) for v in valor)
    
    valor_limpio = str(valor).strip()
    return valor_limpio if valor_limpio else None


def insertar_mensaje_bd(texto_mensaje, canal, campos_extraidos):
    """
    Inserta un nuevo mensaje procesado en la base de datos.
    Comprueba duplicados usando el hash del contenido.
    Limpia y normaliza todos los campos extraídos antes de almacenarlos.
    
    Args:
        texto_mensaje (str): Contenido original del mensaje.
        canal (str): Nombre del canal de origen.
        campos_extraidos (dict): Campos estructurados extraídos por el LLM.
    """
    conn = conectar_bd()
    cursor = conn.cursor()
    
    hash_mensaje = generar_hash_mensaje(texto_mensaje)

    campos_limpios = {
        "pais": limpiar_campo_extraido(campos_extraidos.get("pais")),
        "ciudad": limpiar_campo_extraido(campos_extraidos.get("ciudad")),
        "fecha_inicio": limpiar_campo_extraido(campos_extraidos.get("fecha_inicio")),
        "fecha_fin": limpiar_campo_extraido(campos_extraidos.get("fecha_fin")),
        "fecha_limite_inscripcion": limpiar_campo_extraido(campos_extraidos.get("fecha_limite_inscripcion")),
        "tematica": limpiar_campo_extraido(campos_extraidos.get("tematica")),
        "infopack": limpiar_campo_extraido(campos_extraidos.get("infopack")),
        "formulario": limpiar_campo_extraido(campos_extraidos.get("formulario")),
        "contacto": limpiar_campo_extraido(campos_extraidos.get("contacto")),
    }

    if DEBUG:
        print("Insertando mensaje con campos extraídos:")
        for campo, valor in campos_limpios.items():
            print(f"   {campo}: {valor}")

    try:
        cursor.execute('''
            INSERT INTO mensajes (
                fecha, texto, pais, ciudad, fecha_inicio, fecha_fin, 
                fecha_limite_inscripcion, tematica, infopack, formulario, 
                contacto, canal, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            texto_mensaje,
            campos_limpios["pais"],
            campos_limpios["ciudad"],
            campos_limpios["fecha_inicio"],
            campos_limpios["fecha_fin"],
            campos_limpios["fecha_limite_inscripcion"],
            campos_limpios["tematica"],
            campos_limpios["infopack"],
            campos_limpios["formulario"],
            campos_limpios["contacto"],
            canal,
            hash_mensaje
        ))

        conn.commit()
        if DEBUG:
            print("Mensaje guardado correctamente en la base de datos.")

    except sqlite3.IntegrityError:
        if DEBUG:
            print("Mensaje duplicado detectado. No se insertó en la base de datos.")
    
    finally:
        conn.close()


def obtener_mensajes_del_dia():
    """
    Recupera todos los mensajes almacenados cuya fecha corresponda al día actual.
    Útil para enviar mensajes nuevos o generar el resumen diario.
    
    Returns:
        list of tuples: Mensajes recuperados de la base de datos.
    """
    conn = conectar_bd()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM mensajes 
        WHERE DATE(fecha) = DATE('now')
        ORDER BY fecha ASC
    """)
    
    mensajes = cursor.fetchall()
    conn.close()
    
    if DEBUG:
        print(f"Se encontraron {len(mensajes)} mensajes correspondientes al día de hoy.")
    
    return mensajes

# ============================================================================
# MÓDULO EXTRACTOR LLM (versión Google Gemini)
# ============================================================================

def crear_prompt_extraccion(mensaje):
    """
    Genera el prompt que se enviará al modelo de lenguaje (LLM) para
    extraer información estructurada de un mensaje de WhatsApp.
    
    Args:
        mensaje (str): Texto original del mensaje de WhatsApp.
    
    Returns:
        str: Prompt formateado para el modelo LLM.
    """
    return f"""
Eres un extractor de datos especializado en oportunidades de movilidad juvenil.
Tu tarea es extraer información específica del siguiente mensaje de WhatsApp.

IMPORTANTE: Devuelve SOLO un JSON válido con esta estructura exacta:

{{
  "pais": "...",
  "ciudad": "...",
  "fecha_inicio": "...",
  "fecha_fin": "...",
  "fecha_limite_inscripcion": "...",
  "tematica": "...",
  "infopack": "...",
  "formulario": "...",
  "contacto": "..."
}}

REGLAS DE EXTRACCIÓN:
- Si un campo no aparece en el texto, usa null.
- Todos los valores deben ser strings o null.
- El JSON debe ser **válido y parseable**.
- Usa formato DD/MM/AAAA para las fechas cuando sea posible.
- Para fechas de rango (por ejemplo "September 4 – 14, 2025"), extrae fecha_inicio = 04/09/2025 y fecha_fin = 14/09/2025.
- fecha_limite_inscripcion corresponde a la fecha límite para aplicar o inscribirse (si aparece explícita en el texto).
- No incluyas explicaciones adicionales fuera del JSON.

EJEMPLOS DE QUÉ BUSCAR:
- pais: país donde ocurre el evento (en español). Si no se menciona, usa null.
- ciudad: ciudad o localidad (tal como aparezca en el texto).
- fecha_inicio y fecha_fin: fechas del evento en DD/MM/AAAA.
- fecha_limite_inscripcion: fecha límite para aplicar o inscribirse en DD/MM/AAAA.
- tematica: tema principal, objetivo o contenido del programa.
- infopack: URLs o enlaces a documentos informativos.
- formulario: enlace de inscripción o aplicación.
- contacto: correos electrónicos, teléfonos o nombres de contacto.

---

MENSAJE A PROCESAR:
\"\"\"{mensaje}\"\"\"

Responde solo con el JSON:
"""


def extraer_campos_con_llm(mensaje):
    """
    Envía el mensaje al modelo Gemini para extraer información estructurada.
    Maneja la construcción del prompt, la llamada al modelo,
    el análisis de la respuesta y la validación de JSON.
    
    Args:
        mensaje (str): Texto original del mensaje.
    
    Returns:
        dict: Diccionario con los campos extraídos del mensaje.
    """
    prompt = crear_prompt_extraccion(mensaje)
    
    try:
        if DEBUG:
            print("Enviando solicitud a Gemini...")

        # Llamada al modelo
        response = GEMINI_MODEL.generate_content(prompt)
        texto_respuesta = response.text.strip()

        if DEBUG:
            print("Respuesta cruda del modelo:")
            print(texto_respuesta)

        # Intentar localizar y parsear el JSON en la respuesta.
        inicio_json = texto_respuesta.find('{')
        fin_json = texto_respuesta.rfind('}') + 1

        if inicio_json != -1 and fin_json > inicio_json:
            json_str = texto_respuesta[inicio_json:fin_json]
            datos_extraidos = json.loads(json_str)

            if DEBUG:
                print("Campos extraídos correctamente:")
                for campo, valor in datos_extraidos.items():
                    print(f"   {campo}: {valor}")

            return datos_extraidos

        else:
            raise json.JSONDecodeError("No se encontró un JSON válido en la respuesta", texto_respuesta, 0)

    except json.JSONDecodeError as e:
        print(f"Error: la respuesta del modelo no es JSON válido: {e}")
        if DEBUG:
            print(f"Respuesta recibida: {texto_respuesta}")
        return {}

    except Exception as e:
        print(f"Error inesperado al procesar con el modelo Gemini: {e}")
        return {}


# ============================================================================
# MÓDULO AUTOMATIZACIÓN WHATSAPP (SELENIUM)
# ============================================================================

def inicializar_navegador():
    """
    Configura e inicializa el navegador Chrome con las opciones necesarias
    para automatizar WhatsApp Web mediante Selenium.
    
    Returns:
        selenium.webdriver.Chrome: Instancia del navegador configurada.
    """
    opciones = webdriver.ChromeOptions()
    opciones.add_argument(f"--user-data-dir={RUTA_SESION_CHROME}")
    opciones.add_argument("--remote-debugging-port=9222")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--disable-web-security")
    opciones.add_argument("--disable-features=VizDisplayCompositor")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opciones)
    driver.set_window_size(1200, 800)

    if DEBUG:
        print("Navegador Chrome inicializado correctamente.")

    return driver


def abrir_whatsapp_web(driver):
    """
    Navega a WhatsApp Web y espera a que cargue completamente.
    También gestiona el escaneo del código QR si es necesario.
    
    Args:
        driver (webdriver.Chrome): Instancia del navegador.
    """
    print("Abriendo WhatsApp Web...")
    driver.get("https://web.whatsapp.com")
    time.sleep(50)

    try:
        qr_code = driver.find_element(By.XPATH, "//div[@data-ref and contains(@data-ref, 'qr')]")
        if qr_code:
            print("Se requiere escanear el código QR para iniciar sesión.")
            input("Presione Enter después de escanear el código QR en su teléfono...")
            time.sleep(50)
    except NoSuchElementException:
        print("Sesión activa detectada en WhatsApp Web.")


def navegar_a_seccion_canales(driver):
    """
    Navega a la sección de Canales de WhatsApp.
    Esta funcionalidad depende de la interfaz de WhatsApp Web y puede variar.
    
    Args:
        driver (webdriver.Chrome): Instancia del navegador.
    
    Returns:
        bool: True si se logró abrir la sección de canales, False en caso contrario.
    """
    try:
        print("Navegando a la sección de Canales...")
        boton_canales = driver.find_element(
            By.XPATH, 
            "//span[@data-icon='newsletter-outline']/ancestor::button"
        )
        boton_canales.click()
        time.sleep(50)
        print("Sección de canales abierta correctamente.")
        return True

    except NoSuchElementException:
        print("No se encontró la sección de Canales en la interfaz actual.")
        print("Verifique que la función de Canales esté habilitada en su cuenta.")
        return False


def abrir_canal_especifico(driver, nombre_canal):
    """
    Busca y abre un canal específico por su nombre.
    
    Args:
        driver (webdriver.Chrome): Instancia del navegador.
        nombre_canal (str): Nombre del canal a abrir.
    
    Returns:
        bool: True si se abrió el canal correctamente, False si no se encontró.
    """
    try:
        print(f"Buscando el canal: {nombre_canal}")
        elemento_canal = driver.find_element(
            By.XPATH,
            f"//span[contains(text(), '{nombre_canal}')]"
        )
        elemento_canal.click()
        time.sleep(50)
        print(f"Canal '{nombre_canal}' abierto correctamente.")
        return True

    except NoSuchElementException:
        print(f"No se encontró el canal: {nombre_canal}.")
        print("Verifique que el nombre sea correcto y que tenga acceso al canal.")
        return False


def extraer_mensajes_visibles(driver):
    """
    Extrae todos los mensajes visibles en la pantalla actual del canal.
    
    Args:
        driver (webdriver.Chrome): Instancia del navegador.
    
    Returns:
        list of str: Lista de mensajes extraídos con texto válido.
    """
    try:
        print("Extrayendo mensajes visibles en pantalla...")

        selectores_mensaje = [
            "//div[contains(@class, 'copyable-text')]",
            "//div[@data-pre-plain-text]",
            "//span[contains(@class, 'selectable-text')]"
        ]

        mensajes_encontrados = []
        for selector in selectores_mensaje:
            try:
                elementos = driver.find_elements(By.XPATH, selector)
                if elementos:
                    mensajes_encontrados = [elem.text.strip() for elem in elementos if elem.text.strip()]
                    break
            except:
                continue

        mensajes_validos = [msg for msg in mensajes_encontrados if len(msg) > 10]

        if DEBUG:
            print(f"Se encontraron {len(mensajes_validos)} mensajes válidos en la pantalla actual.")

        return mensajes_validos

    except Exception as e:
        print(f"Error al extraer mensajes: {e}")
        return []


def escribir_mensaje_en_chat(driver, texto_mensaje):
    """
    Escribe y envía un mensaje en el chat activo de WhatsApp Web.
    Usa Shift+Enter para respetar saltos de línea sin enviar el mensaje antes de tiempo.
    
    Args:
        driver (webdriver.Chrome): Instancia del navegador.
        texto_mensaje (str): Texto completo del mensaje a enviar.
    
    Returns:
        bool: True si el mensaje se envió correctamente, False en caso de error.
    """
    try:
        caja_texto = driver.find_element(
            By.XPATH,
            "//footer//div[@contenteditable='true']"
        )
        caja_texto.click()
        time.sleep(1)

        from selenium.webdriver.common.action_chains import ActionChains
        acciones = ActionChains(driver)

        for linea in texto_mensaje.splitlines():
            caja_texto.send_keys(linea)
            acciones.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
            time.sleep(0.1)

        caja_texto.send_keys(Keys.ENTER)
        time.sleep(2)

        if DEBUG:
            print("Mensaje enviado correctamente al chat activo.")
        return True

    except NoSuchElementException:
        print("No se encontró la caja de texto para escribir el mensaje.")
        return False

    except Exception as e:
        print(f"Error al enviar mensaje: {e}")
        return False

# ============================================================================
# FUNCIONES PRINCIPALES DEL SISTEMA
# ============================================================================

def scraping_hasta_no_haber_nuevos(max_intentos=5, espera_segundos=3):
    """
    Ejecuta scraping de mensajes repetidamente hasta que ya no se detecten nuevos.
    Evita bucles infinitos mediante un número máximo de intentos.
    
    Args:
        max_intentos (int): Número máximo de pasadas para buscar nuevos mensajes.
        espera_segundos (int): Tiempo de espera entre pasadas.
    """
    print("Iniciando proceso de scraping iterativo hasta no detectar más mensajes nuevos...")
    intentos = 0
    nuevos_mensajes = True

    while nuevos_mensajes and intentos < max_intentos:
        mensajes_antes = len(obtener_mensajes_del_dia())
        print(f"Intento #{intentos + 1} - Mensajes actuales: {mensajes_antes}")
        
        exito = ejecutar_scraping_completo()
        if not exito:
            print("Error durante scraping. Proceso detenido.")
            break

        time.sleep(espera_segundos)
        mensajes_despues = len(obtener_mensajes_del_dia())
        nuevos_mensajes = mensajes_despues > mensajes_antes
        intentos += 1

    print("Scraping finalizado: no se detectan más mensajes nuevos.")


def ejecutar_scraping_completo():
    """
    Función principal que coordina todo el proceso de scraping.
    Incluye la conexión a WhatsApp Web, navegación, extracción de mensajes,
    procesamiento con el LLM y almacenamiento en la base de datos.
    
    Returns:
        bool: True si el scraping se completó con éxito, False si hubo errores.
    """
    print("===== INICIANDO PROCESO DE SCRAPING =====")
    crear_tabla_mensajes()

    driver = inicializar_navegador()
    
    try:
        abrir_whatsapp_web(driver)

        if not navegar_a_seccion_canales(driver):
            print("No se pudo acceder a la sección de canales.")
            return False

        if not abrir_canal_especifico(driver, CANAL_ORIGEN):
            print(f"No se pudo abrir el canal de origen: {CANAL_ORIGEN}")
            return False

        mensajes_extraidos = extraer_mensajes_visibles(driver)
        if not mensajes_extraidos:
            print("No se encontraron mensajes para procesar.")
            return False

        mensajes_nuevos = 0
        for mensaje in mensajes_extraidos:
            try:
                hash_mensaje = generar_hash_mensaje(mensaje)
                if mensaje_ya_existe(hash_mensaje):
                    if DEBUG:
                        print("Mensaje ya procesado anteriormente. Saltando...")
                    continue

                print("Procesando mensaje nuevo...")
                campos_extraidos = extraer_campos_con_llm(mensaje)
                insertar_mensaje_bd(mensaje, CANAL_ORIGEN, campos_extraidos)
                mensajes_nuevos += 1

            except Exception as e:
                print(f"Error procesando mensaje: {e}")
                continue

        print(f"Scraping completado: {mensajes_nuevos} mensajes nuevos procesados.")
        return True

    except Exception as e:
        print(f"Error durante el proceso de scraping: {e}")
        return False

    finally:
        driver.quit()
        print("Navegador cerrado.")


def enviar_mensajes_individuales():
    """
    Envía individualmente cada mensaje almacenado del día al canal destino.
    Usa Selenium para abrir el navegador, acceder al canal y enviar cada mensaje.
    
    Returns:
        bool: True si los mensajes se enviaron correctamente, False en caso contrario.
    """
    print("===== INICIANDO ENVÍO DE MENSAJES INDIVIDUALES =====")
    mensajes = obtener_mensajes_del_dia()

    if not mensajes:
        print("No hay mensajes nuevos para enviar.")
        return False

    driver = inicializar_navegador()
    
    try:
        abrir_whatsapp_web(driver)

        if not abrir_canal_especifico(driver, CANAL_DESTINO):
            print(f"No se pudo abrir el canal destino: {CANAL_DESTINO}")
            return False

        print(f"Enviando {len(mensajes)} mensajes individualmente...")
        for mensaje_bd in mensajes:
            texto_original = mensaje_bd[2]

            if escribir_mensaje_en_chat(driver, texto_original):
                if DEBUG:
                    print("Mensaje enviado correctamente.")
                time.sleep(3)
            else:
                print("Error al enviar un mensaje.")

        print("Todos los mensajes individuales fueron enviados.")
        return True

    except Exception as e:
        print(f"Error durante el envío de mensajes: {e}")
        return False

    finally:
        driver.quit()


def limpiar_texto_unicode(texto):
    """
    Elimina caracteres fuera del Basic Multilingual Plane (BMP),
    como algunos emojis o caracteres especiales que pueden causar errores
    en el ChromeDriver al enviar mensajes.
    
    Args:
        texto (str): Texto de entrada.
    
    Returns:
        str: Texto filtrado sin caracteres problemáticos.
    """
    return ''.join(c for c in texto if ord(c) <= 0xFFFF)


def generar_y_enviar_resumen_diario():
    """
    Genera un resumen estructurado con todos los mensajes del día
    y lo envía como un único mensaje al canal destino.
    
    Returns:
        bool: True si el resumen se envió correctamente, False en caso contrario.
    """
    print("===== GENERANDO Y ENVIANDO RESUMEN DIARIO =====")
    mensajes = obtener_mensajes_del_dia()

    if not mensajes:
        print("No hay mensajes disponibles para el resumen.")
        return False

    resumen = "**RESUMEN DE OPORTUNIDADES DEL DÍA**\n"
    resumen += f"Fecha: {datetime.now().strftime('%d/%m/%Y')}\n"
    resumen += f"Oportunidades encontradas: {len(mensajes)}\n\n"

    for i, mensaje_bd in enumerate(mensajes, 1):
        resumen += f"OPORTUNIDAD {i}\n"

        pais = mensaje_bd[3] or "País no especificado"
        ciudad = mensaje_bd[4] or "Ciudad no especificada"
        fecha_inicio = mensaje_bd[5] or "Fecha de inicio no especificada"
        fecha_fin = mensaje_bd[6] or "Fecha de fin no especificada"
        fecha_limite = mensaje_bd[7] or "Fecha límite de inscripción no especificada"
        tematica = mensaje_bd[8] or "Temática no especificada"
        infopack = mensaje_bd[9]
        formulario = mensaje_bd[10]
        contacto = mensaje_bd[11]

        resumen += f"- País: {pais}\n"
        resumen += f"- Ciudad: {ciudad}\n"
        resumen += f"- Fecha de inicio: {fecha_inicio}\n"
        resumen += f"- Fecha de fin: {fecha_fin}\n"
        resumen += f"- Fecha límite de inscripción: {fecha_limite}\n"
        resumen += f"- Temática: {tematica}\n"

        if infopack:
            resumen += f"- Información adicional: {infopack}\n"
        if formulario:
            resumen += f"- Formulario: {formulario}\n"
        if contacto:
            resumen += f"- Contacto: {contacto}\n"

        resumen += "-" * 30 + "\n\n"

    resumen += "Mensaje generado automáticamente por WhatsApp LLM Bot."

    if DEBUG:
        print("Resumen generado:")
        print(resumen if len(resumen) < 500 else resumen[:500] + "...")

    driver = inicializar_navegador()

    try:
        abrir_whatsapp_web(driver)

        if not navegar_a_seccion_canales(driver):
            print("No se pudo acceder a la sección de canales.")
            return False

        if not abrir_canal_especifico(driver, CANAL_DESTINO):
            print(f"No se pudo abrir el canal destino: {CANAL_DESTINO}")
            return False

        resumen_limpio = limpiar_texto_unicode(resumen)
        if escribir_mensaje_en_chat(driver, resumen_limpio):
            print("Resumen diario enviado correctamente.")
            return True
        else:
            print("Error al enviar el resumen.")
            return False

    except Exception as e:
        print(f"Error durante el envío del resumen: {e}")
        return False

    finally:
        driver.quit()


def mostrar_estadisticas_mensajes():
    """
    Muestra un resumen en consola con estadísticas de los mensajes guardados hoy.
    Incluye la cantidad y un listado con fecha, lugar y contenido abreviado.
    """
    print("===== ESTADÍSTICAS DE MENSAJES =====")
    mensajes_hoy = obtener_mensajes_del_dia()
    print(f"Mensajes guardados hoy: {len(mensajes_hoy)}")

    if mensajes_hoy:
        print("\nListado de mensajes:")
        for i, mensaje in enumerate(mensajes_hoy, 1):
            fecha = mensaje[1]
            texto_corto = mensaje[2][:80] + "..." if len(mensaje[2]) > 80 else mensaje[2]
            lugar = mensaje[3] or "Sin lugar"
            print(f"{i}. [{fecha}] {lugar}")
            print(f"   {texto_corto}")
            print()

# ============================================================================
# SISTEMA DE PROGRAMACIÓN AUTOMÁTICA
# ============================================================================

def configurar_horarios_automaticos():
    """
    Configura los horarios programados para todas las tareas del bot.
    Usa la biblioteca 'schedule' para definir las ejecuciones diarias.
    """
    print("Configurando horarios automáticos...")

    for horario in HORARIOS_SCRAPING:
        schedule.every().day.at(horario).do(ejecutar_scraping_completo)
        print(f"Scraping programado a las {horario}")

    for horario in HORARIOS_ENVIO:
        schedule.every().day.at(horario).do(enviar_mensajes_individuales)
        print(f"Envío programado a las {horario}")

    schedule.every().day.at(HORARIO_RESUMEN).do(generar_y_enviar_resumen_diario)
    print(f"Resumen diario programado a las {HORARIO_RESUMEN}")

    print("Horarios configurados correctamente.")


def ejecutar_bucle_automatico():
    """
    Ejecuta el sistema en modo automático continuo.
    Monitorea y ejecuta las tareas programadas en los horarios definidos.
    Muestra mensajes de estado en consola cada cierto tiempo.
    """
    print("===== INICIANDO MODO AUTOMÁTICO =====")
    print("El bot ejecutará las siguientes tareas automáticamente:")
    print(f"  - Scraping: {', '.join(HORARIOS_SCRAPING)}")
    print(f"  - Envío: {', '.join(HORARIOS_ENVIO)}")
    print(f"  - Resumen: {HORARIO_RESUMEN}")
    print("\nPara detener el bot, presione Ctrl+C.")
    print("-" * 50)

    configurar_horarios_automaticos()

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)

            if hasattr(ejecutar_bucle_automatico, 'contador'):
                ejecutar_bucle_automatico.contador += 1
            else:
                ejecutar_bucle_automatico.contador = 1

            if ejecutar_bucle_automatico.contador % 10 == 0:
                print(f"Bot activo - {datetime.now().strftime('%H:%M:%S')}")

    except KeyboardInterrupt:
        print("\nEjecución interrumpida por el usuario. Bot detenido.")

# ============================================================================
# INTERFAZ DE LÍNEA DE COMANDOS
# ============================================================================

def mostrar_ayuda():
    """
    Muestra la ayuda completa del sistema
    """
    print("""
WhatsApp LLM Bot - Sistema de Agregación Inteligente
════════════════════════════════════════════════════════

DESCRIPCIÓN:
Este bot automatiza la extracción, procesamiento y redistribución de mensajes
de WhatsApp utilizando inteligencia artificial para estructurar la información.

COMANDOS DISPONIBLES:

🔍 --scraper
   Ejecuta el scraping inmediatamente
   Extrae mensajes del canal origen y los procesa con IA

🔍 --scraper-loop
   Ejecuta el scraping para casos en los que hay más de 1 mensaje nuevo inmediatamente
   Extrae mensajes del canal origen y los procesa con IA


📤 --send  
   Envía mensajes individuales al canal destino
   Envía cada mensaje del día por separado

📋 --resumen
   Genera y envía un resumen diario estructurado
   Consolida todas las oportunidades del día en un mensaje

📊 --stats
   Muestra estadísticas de mensajes almacenados
   Información sobre mensajes procesados hoy

⏰ --auto
   Ejecuta el bot en modo automático continuo
   Programa todas las tareas según los horarios configurados

❓ --help
   Muestra esta ayuda

CONFIGURACIÓN ACTUAL:
   📥 Canal origen: {CANAL_ORIGEN}
   📤 Canal destino: {CANAL_DESTINO}  
   🤖 Modelo LLM: {LLAMA_MODEL}
   📊 Base de datos: {RUTA_DB}

EJEMPLOS DE USO:
   python whatsapp_bot.py --scraper     # Extraer mensajes ahora
   python whatsapp_bot.py --send        # Enviar mensajes ahora  
   python whatsapp_bot.py --resumen     # Enviar resumen ahora
   python whatsapp_bot.py --auto        # Modo automático
   python whatsapp_bot.py --stats       # Ver estadísticas

REQUISITOS:
   - Chrome/Chromium instalado
   - Ollama ejecutándose con modelo {LLAMA_MODEL}
   - WhatsApp Web configurado y logueado
   - Acceso a los canales configurados

¡Recuerda mantener Ollama ejecutándose para el procesamiento con IA!
""")

def main():
    """
    Función principal que maneja la interfaz de línea de comandos
    y ejecuta las diferentes funcionalidades del bot
    """
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(
        description="WhatsApp LLM Bot - Sistema de Agregación Inteligente",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Definir argumentos disponibles
    parser.add_argument(
        "--scraper", 
        action="store_true", 
        help="Ejecutar scraping de mensajes inmediatamente"
    )
    
    parser.add_argument(
        "--send", 
        action="store_true", 
        help="Enviar mensajes individuales al canal destino"
    )
    
    parser.add_argument(
        "--resumen", 
        action="store_true", 
        help="Generar y enviar resumen diario"
    )
    
    parser.add_argument(
        "--stats", 
        action="store_true", 
        help="Mostrar estadísticas de mensajes"
    )
    
    parser.add_argument(
        "--auto", 
        action="store_true", 
        help="Ejecutar en modo automático continuo"
    )

    parser.add_argument(
        "--scraper-loop", 
        action="store_true", 
        help="Ejecutar múltiples pasadas de scraping hasta no encontrar nuevos mensajes"
    )

    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Mostrar banner del sistema
    print("WhatsApp LLM Bot v1.0")
    print("═" * 50)
    
    # Verificar que al menos un argumento fue proporcionado
    if not any(vars(args).values()):
        mostrar_ayuda()
        return
    
    # Ejecutar la función correspondiente según el argumento
    try:
        if args.scraper:
            print("Ejecutando scraping manual...")
            exito = ejecutar_scraping_completo()
            if exito:
                print("Scraping completado exitosamente")
            else:
                print("Error durante el scraping")
        
        elif args.send:
            print("Enviando mensajes individuales...")
            exito = enviar_mensajes_individuales()
            if exito:
                print("Mensajes enviados exitosamente")
            else:
                print("Error durante el envío")
        
        elif args.resumen:
            print("Generando resumen diario...")
            exito = generar_y_enviar_resumen_diario()
            if exito:
                print("Resumen enviado exitosamente")
            else:
                print("Error durante el envío del resumen")
        
        elif args.stats:
            mostrar_estadisticas_mensajes()
        
        elif args.auto:
            ejecutar_bucle_automatico()

        elif args.scraper_loop:
            print("Ejecutando scraping múltiple hasta que no haya más mensajes nuevos...")
            scraping_hasta_no_haber_nuevos()

    
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"Error inesperado: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()

# ============================================================================
# FUNCIONES DE UTILIDAD Y DEBUGGING
# ============================================================================

def verificar_dependencias():
    """
    Verifica que todas las dependencias estén instaladas y configuradas
    """
    print("Verificando dependencias del sistema...")
    
    # Verificar importaciones
    try:
        import selenium
        print("Selenium instalado")
    except ImportError:
        print("Selenium no instalado: pip install selenium")
        return False
    
    try:
        import requests
        print("Requests instalado")
    except ImportError:
        print("Requests no instalado: pip install requests")
        return False
    
    try:
        import schedule
        print("Schedule instalado")
    except ImportError:
        print("Schedule no instalado: pip install schedule")
        return False
    
    # Verificar directorio de datos
    import os
    if not os.path.exists(os.path.dirname(RUTA_DB)):
        print(f"Creando directorio de datos: {os.path.dirname(RUTA_DB)}")
        os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    
    print("Todas las dependencias verificadas")
    return True

def limpiar_base_datos():
    """
    Función de utilidad para limpiar la base de datos
    ¡USAR CON PRECAUCIÓN!
    """
    respuesta = input("¿Estás seguro de que quieres limpiar la base de datos? (sí/no): ")
    
    if respuesta.lower() in ['sí', 'si', 'yes', 'y']:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mensajes")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='mensajes'")
        conn.commit()
        conn.close()
        print("Base de datos limpiada")
    else:
        print("Operación cancelada")

# ============================================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# ============================================================================

if __name__ == "__main__":
    """
    Punto de entrada principal del programa
    Verifica dependencias y ejecuta la interfaz de comandos
    """
    try:
        # Verificar que todo esté configurado correctamente
        if not verificar_dependencias():
            print("Faltan dependencias requeridas")
            print("Revisa la configuración antes de continuar")
            exit(1)
        
        # Ejecutar la interfaz principal
        main()
        
    except Exception as e:
        print(f"Error crítico del sistema: {e}")
        if DEBUG:
            import traceback
            traceback.print_exc()
        exit(1)

# ============================================================================
# NOTAS ADICIONALES Y DOCUMENTACIÓN
# ============================================================================

"""
NOTAS DE IMPLEMENTACIÓN:
═══════════════════════════

1. CONFIGURACIÓN INICIAL:
   - Instalar dependencias: pip install selenium requests schedule
   - Descargar ChromeDriver y agregarlo al PATH
   - Instalar Ollama y descargar el modelo: ollama pull llama3.2
   - Configurar WhatsApp Web en Chrome

2. ESTRUCTURA DE DATOS:
   La base de datos almacena:
   - Texto original del mensaje
   - Campos extraídos por IA (lugar, fecha, temática, etc.)
   - Hash único para evitar duplicados
   - Metadatos (fecha de procesamiento, canal origen)

3. FLUJO DE TRABAJO:
   Scraping → Procesamiento IA → Almacenamiento → Redistribución
   
4. SEGURIDAD:
   - Usa hash SHA256 para detectar duplicados
   - Mantiene sesión persistente de Chrome
   - Manejo de errores robusto

5. ESCALABILIDAD:
   - Fácil agregar nuevos campos de extracción
   - Configurable para múltiples canales
   - Sistema de horarios flexible

6. TROUBLESHOOTING:
   - Si WhatsApp no carga: verificar sesión de Chrome
   - Si LLM no responde: verificar que Ollama esté ejecutándose
   - Si no encuentra canales: verificar nombres exactos
   - Si hay errores de Selenium: actualizar ChromeDriver

CONTRIBUCIONES:
Para mejorar el bot, considera:
- Agregar más campos de extracción
- Implementar filtros de contenido
- Agregar interfaz web
- Mejorar el sistema de horarios
- Agregar notificaciones de estado

LICENCIA:
Este código es de uso educativo y personal.
Respeta los términos de servicio de WhatsApp.
"""
