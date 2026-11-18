import os
import sqlite3
from datetime import datetime, timezone
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(
    title="GingaSegura - Sistema de Gestão | Família Martelo Predador",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("DB_PATH", "gingasegura.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_aula TEXT NOT NULL,
            aluno_id INTEGER NOT NULL,
            presente INTEGER NOT NULL,
            registrado_em TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            data_evento TEXT NOT NULL,
            local TEXT NOT NULL,
            categoria TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

class RegistroItem(BaseModel):
    aluno_id: int
    presente: bool

class ChamadaLoteRequest(BaseModel):
    data_aula: str
    registros: List[RegistroItem]

class EventoRequest(BaseModel):
    titulo: str
    data_evento: str
    local: str
    categoria: str

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "GingaSegura - Família Martelo Predador",
        "modalidades": ["Capoeira (Cordas)", "Contato Total Português (Faixas)"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/chamadas/lote")
def salvar_chamada_lote(payload: ChamadaLoteRequest):
    conn = sqlite3.connect(DB_PATH)
    agora = datetime.now(timezone.utc).isoformat()
    for item in payload.registros:
        conn.execute(
            "INSERT INTO chamadas (data_aula, aluno_id, presente, registrado_em) VALUES (?, ?, ?, ?)",
            (payload.data_aula, item.aluno_id, int(item.presente), agora),
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "total_registrado": len(payload.registros), "data_aula": payload.data_aula}

@app.post("/api/eventos")
def criar_evento(payload: EventoRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO eventos (titulo, data_evento, local, categoria) VALUES (?, ?, ?, ?)",
        (payload.titulo, payload.data_evento, payload.local, payload.categoria),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "evento": payload.model_dump()}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")