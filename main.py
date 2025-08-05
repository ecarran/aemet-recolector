import os
import sqlite3
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from datetime import datetime
from pytz import timezone
from threading import Thread
import time

app = FastAPI()
DB_FILENAME = "aemet_valladolid.db"
API_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas/"
API_KEY = os.getenv("AEMET_API_KEY")

HEADERS = {
    "accept": "application/json",
    "api_key": API_KEY,
    "User-Agent": "aemet-recolector/1.0 (Render)"
}

@app.get("/")
def keep_alive():
    now = datetime.now()
    db_exists = os.path.exists(DB_FILENAME)
    n_registros = -1

    try:
        if db_exists:
            conn = sqlite3.connect(DB_FILENAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM observaciones")
            n_registros = cursor.fetchone()[0]
            conn.close()
    except Exception as e:
        print(f"[KEEPALIVE] Error al contar registros: {e}")

    log_entry = f"[KEEPALIVE] {now.strftime('%Y-%m-%d %H:%M:%S')} - DB: {db_exists} - Registros: {n_registros}\n"
    try:
        with open("keepalive.log", "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[KEEPALIVE] Error escribiendo log: {e}")

    return {
        "estado": "ok",
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "db_existe": db_exists,
        "n_registros": n_registros
    }

def recolectar_datos():
    if not API_KEY:
        print("[RECOLECTAR] API KEY no configurada")
        return

    try:
        r1 = requests.get(API_URL, headers=HEADERS, timeout=10)
        r1.raise_for_status()
        url_datos = r1.json()["datos"]
    except Exception as e:
        print(f"[RECOLECTAR] Error en primer paso (r1): {e}")
        return

    time.sleep(1)  # pequeña espera entre r1 y r2

    try:
        r2 = requests.get(url_datos, timeout=10)
        r2.raise_for_status()
        datos = r2.json()
    except Exception as e:
        print(f"[RECOLECTAR] Error en segundo paso (r2): {e}")
        return

    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observaciones (
            idema TEXT,
            ubi TEXT,
            lon REAL,
            lat REAL,
            fint TEXT,
            ta REAL,
            tamax REAL,
            tamin REAL,
            hr REAL,
            vv REAL,
            dv TEXT,
            vmax REAL,
            pres REAL,
            pres_nmar REAL,
            prec REAL,
            sol REAL,
            inso REAL,
            nieve REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_idema_fint ON observaciones(idema, fint)")

    def parse_float(val):
        try:
            return float(val)
        except:
            return None

    insertados = 0
    for row in datos:
        if row.get("ubi") != "VALLADOLID":
            continue

        try:
            idema = row["idema"]
            ubi = row["ubi"]
            lon = float(row["lon"])
            lat = float(row["lat"])
            utc_dt = datetime.fromisoformat(row["fint"].replace("Z", "+00:00"))
            fint = utc_dt.astimezone(timezone("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")

            ta = parse_float(row.get("ta"))
            tamax = parse_float(row.get("tamax"))
            tamin = parse_float(row.get("tamin"))
            hr = parse_float(row.get("hr"))
            vv = parse_float(row.get("vv"))
            dv = row.get("dv", "")
            vmax = parse_float(row.get("vmax"))
            pres = parse_float(row.get("pres"))
            pres_nmar = parse_float(row.get("pres_nmar"))
            prec = parse_float(row.get("prec"))
            sol = parse_float(row.get("sol"))
            inso = parse_float(row.get("inso"))
            nieve = parse_float(row.get("nieve"))
        except Exception as e:
            print("[RECOLECTAR] Error procesando fila:", e)
            continue

        cursor.execute("SELECT 1 FROM observaciones WHERE idema = ? AND fint = ?", (idema, fint))
        if cursor.fetchone():
            continue

        try:
            cursor.execute("""
                INSERT INTO observaciones (
                    idema, ubi, lon, lat, fint, ta, tamax, tamin,
                    hr, vv, dv, vmax, pres, pres_nmar, prec,
                    sol, inso, nieve
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                idema, ubi, lon, lat, fint, ta, tamax, tamin,
                hr, vv, dv, vmax, pres, pres_nmar, prec,
                sol, inso, nieve
            ))
            insertados += 1
        except Exception as e:
            print("[RECOLECTAR] Error insertando fila:", e)

    conn.commit()
    conn.close()
    print(f"[RECOLECTAR] Recolección terminada. Registros insertados: {insertados}")

@app.get("/healthz")
def healthcheck():
    db_exists = os.path.exists(DB_FILENAME)
    estado = "ok"
    n = -1

    try:
        if db_exists:
            conn = sqlite3.connect(DB_FILENAME)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM observaciones")
            n = cursor.fetchone()[0]
            conn.close()
        else:
            estado = "sin_db"
    except Exception as e:
        estado = f"error_db: {e}"

    return {
        "estado": estado,
        "registros": n
    }

@app.get("/recolectar")
def recolectar_directo():
    recolectar_datos()
    return {"estado": "ok", "mensaje": "Recolección ejecutada directamente"}

@app.get("/disparar-recolector")
def recolector_en_segundo_plano():
    def recolectar_seguro():
        try:
            recolectar_datos()
        except Exception as e:
            print(f"[RECOLECTAR] Excepción inesperada en hilo: {e}")

    Thread(target=recolectar_seguro).start()
    return {"estado": "ok", "mensaje": "Recolector lanzado en segundo plano"}

@app.get("/descargar-db")
def descargar_db():
    if os.path.exists(DB_FILENAME):
        return FileResponse(DB_FILENAME, media_type="application/octet-stream", filename=DB_FILENAME)
    return {"estado": "error", "mensaje": "Fichero de base de datos no encontrado"}