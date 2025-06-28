import os
import sqlite3
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from datetime import datetime
from pytz import timezone

app = FastAPI()
DB_FILENAME = "aemet_valladolid.db"

API_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas/"
API_KEY = os.getenv("AEMET_API_KEY")

@app.get("/")
def raiz():
    return {"mensaje": "API AEMET Valladolid activa. Usa /recolectar o /descargar-db"}

@app.get("/recolectar")
def recolectar():
    if not API_KEY:
        return {"estado": "error", "mensaje": "API KEY no configurada"}

    try:
        headers = {"accept": "application/json", "api_key": API_KEY}
        r1 = requests.get(API_URL, headers=headers)
        r1.raise_for_status()
        url_datos = r1.json()["datos"]

        r2 = requests.get(url_datos)
        r2.raise_for_status()
        datos = r2.json()
    except Exception as e:
        return {"estado": "error", "mensaje": f"Error al descargar datos: {e}"}

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

            ta = float(row.get("ta", "nan"))
            tamax = float(row.get("tamax", "nan"))
            tamin = float(row.get("tamin", "nan"))
            hr = float(row.get("hr", "nan"))
            vv = float(row.get("vv", "nan"))
            dv = row.get("dv", "")  # dirección cardinal como texto
            vmax = float(row.get("vmax", "nan"))
            pres = float(row.get("pres", "nan"))
            pres_nmar = float(row.get("pres_nmar", "nan"))
            prec = float(row.get("prec", "nan"))
            sol = float(row.get("sol", "nan"))
            inso = float(row.get("inso", "nan"))
            nieve = float(row.get("nieve", "nan"))
        except Exception as e:
            print("Error procesando fila:", e)
            continue

        cursor.execute("""
            SELECT 1 FROM observaciones WHERE idema = ? AND fint = ?
        """, (idema, fint))
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
            print("Error insertando fila:", e)

    conn.commit()
    conn.close()
    return {"estado": "ok", "insertados": insertados}

@app.get("/descargar-db")
def descargar_db():
    if os.path.exists(DB_FILENAME):
        return FileResponse(DB_FILENAME, media_type="application/octet-stream", filename=DB_FILENAME)
    return {"estado": "error", "mensaje": "Fichero de base de datos no encontrado"}

