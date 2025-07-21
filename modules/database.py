# database.py
import sqlite3
import os
import json
from hashlib import sha256
from datetime import datetime
from modules.config import RUTA_DB, DEBUG


def conectar_bd():
    os.makedirs(os.path.dirname(RUTA_DB), exist_ok=True)
    return sqlite3.connect(RUTA_DB)


def crear_tabla_mensajes():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
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
        print("[DB] Tabla de mensajes verificada.")


def generar_hash_mensaje(texto):
    return sha256(texto.encode("utf-8")).hexdigest()


def mensaje_ya_existe(hash_mensaje):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mensajes WHERE hash=?", (hash_mensaje,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


def entrada_valida(campos):
    for valor in campos.values():
        if valor and str(valor).strip().lower() != 'unknown':
            return True
    return False


def limpiar_campo_extraido(valor):
    if valor is None:
        return None
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, (list, tuple)):
        return ", ".join(str(v) for v in valor)
    valor_limpio = str(valor).strip()
    return valor_limpio if valor_limpio else None


def insertar_mensaje_bd(mensaje_original, canal, campos):
    if not entrada_valida(campos):
        if DEBUG:
            print("[DB] Entrada descartada: todos los campos son desconocidos o vac\u00edos.")
        return False

    hash_mensaje = generar_hash_mensaje(mensaje_original)
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO mensajes (
                texto, pais, ciudad, fecha_inicio, fecha_fin,
                fecha_limite_inscripcion, tematica, infopack,
                formulario, contacto, canal, hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            mensaje_original,
            limpiar_campo_extraido(campos.get("pais")),
            limpiar_campo_extraido(campos.get("ciudad")),
            limpiar_campo_extraido(campos.get("fecha_inicio")),
            limpiar_campo_extraido(campos.get("fecha_fin")),
            limpiar_campo_extraido(campos.get("fecha_limite_inscripcion")),
            limpiar_campo_extraido(campos.get("tematica")),
            limpiar_campo_extraido(campos.get("infopack")),
            limpiar_campo_extraido(campos.get("formulario")),
            limpiar_campo_extraido(campos.get("contacto")),
            canal,
            hash_mensaje
        ))
        conn.commit()
        if DEBUG:
            print("[DB] Mensaje guardado.")
        return True
    except sqlite3.IntegrityError:
        if DEBUG:
            print("[DB] Mensaje duplicado ignorado.")
        return False
    finally:
        conn.close()


def obtener_mensajes_del_dia():
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
        print(f"[DB] {len(mensajes)} mensajes encontrados para hoy.")
    return mensajes


def mostrar_estadisticas_mensajes():
    mensajes = obtener_mensajes_del_dia()
    print(f"Mensajes guardados hoy: {len(mensajes)}")
    for i, m in enumerate(mensajes, 1):
        print(f"{i}. [{m[1]}] {m[3] or 'Sin lugar'} - {m[2][:60]}...")
