import os
import requests
import sqlite3
import pandas as pd
from fastapi import FastAPI
from datetime import datetime
from fastapi.responses import JSONResponse

app = FastAPI()

API_KEY = os.getenv("AEMET_API_KEY")
IDEMA = "2422"
DB_PATH = "valladolid.db"
URL_BASE = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas/"

def recolectar_datos():
    try:
        r = requests.get(URL_BASE, headers={"accept": "application/json", "api_key": API_KEY})
        r.raise_for_status()
        datos_url = r.json()["datos"]
        r2 = requests.get(datos_url)
        r2.raise_for_status()
        datos = r2.json()
    except Exception as e:
        print("Error al descargar datos:", e)
        return []

    df = pd.DataFrame([d for d in datos if str(d.get("idema")) == IDEMA])
    if df.empty:
        return []

    df["fint"] = pd.to_datetime(df["fint"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observaciones (
        idema INTEGER,
        ubi TEXT,
        lon REAL,
        lat REAL,
        fint TEXT,
        tamin REAL,
        tamax REAL,
        ta REAL,
        hr REAL,
        vv REAL,
        dv REAL,
        prec REAL,
        PRIMARY KEY (idema, fint)
    )""")
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO observaciones VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["idema"]), row["ubi"], float(row["lon"]), float(row["lat"]), row["fint"],
                row.get("tamin"), row.get("tamax"), row.get("ta"), row.get("hr"),
                row.get("vv"), row.get("dv"), row.get("prec")
            ))
        except:
            continue
    conn.commit()
    conn.close()
    return df.to_dict(orient="records")

@app.get("/recolectar")
def recolectar():
    datos = recolectar_datos()
    return {"insertados": len(datos)}

@app.get("/data")
def obtener_datos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM observaciones ORDER BY fint DESC LIMIT 24", conn)
    conn.close()
    return JSONResponse(content=df.to_dict(orient="records"))
from fastapi.responses import FileResponse

@app.get("/descargar-db")
def descargar_db():
    db_path = DB_PATH
    if os.path.exists(db_path):
        return FileResponse(db_path, filename="valladolid.db", media_type="application/octet-stream")
    else:
        return JSONResponse(content={"error": "Base de datos no encontrada"}, status_code=404)
