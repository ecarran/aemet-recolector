from fastapi import FastAPI, Request, Response
import requests
import sqlite3
from datetime import datetime
import os

app = FastAPI()

API_KEY = os.getenv("AEMET_API_KEY")
DB_FILE = "aemet_valladolid.db"
STATION_IDEMA = 2422

URL_BASE = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"

def recolectar_datos():
    headers = {"accept": "application/json", "api_key": API_KEY}
    response = requests.get(URL_BASE, headers=headers)
    response.raise_for_status()

    url_datos = response.json()["datos"]
    response_datos = requests.get(url_datos)
    response_datos.raise_for_status()
    datos = response_datos.json()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observaciones (
            idema INTEGER,
            ubi TEXT,
            fint TEXT,
            ta REAL,
            tamax REAL,
            tamin REAL,
            hr INTEGER,
            vv REAL,
            dv TEXT,
            prec REAL,
            PRIMARY KEY (idema, fint)
        )
    """)

    insertados = 0
    for fila in datos:
        if int(fila["idema"]) != STATION_IDEMA:
            continue
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO observaciones (
                    idema, ubi, fint, ta, tamax, tamin,
                    hr, vv, dv, prec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(fila["idema"]),
                fila.get("ubi", ""),
                fila["fint"],
                float(fila.get("ta") or 0),
                float(fila.get("tamax") or 0),
                float(fila.get("tamin") or 0),
                int(fila.get("hr") or 0),
                float(fila.get("vv") or 0),
                fila.get("dv", ""),
                float(fila.get("prec") or 0)
            ))
            insertados += cursor.rowcount
        except Exception as e:
            print("Error insertando fila:", e)

    conn.commit()
    conn.close()
    return f"{insertados} observaciones insertadas"

@app.api_route("/recolectar", methods=["GET", "HEAD"])
async def recolectar(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    try:
        resultado = recolectar_datos()
        return {"estado": "ok", "mensaje": resultado}
    except Exception as e:
        return {"estado": "error", "mensaje": str(e)}

@app.get("/descargar-db")
def descargar_db():
    from fastapi.responses import FileResponse
    return FileResponse(DB_FILE, media_type='application/octet-stream', filename=DB_FILE)

