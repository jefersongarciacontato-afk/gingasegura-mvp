import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="GingaSegura - Família Martelo Predador", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
DB_PATH = os.getenv("DB_PATH", "gingasegura.db")
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "Martelo@2026")

SESSIONS = {}

ROLES_VALIDOS = {"admin", "super_admin", "professor", "monitor", "estagiario"}

def hash_pwd(senha: str) -> str:
    return hashlib.sha256(f"fmp_salt_{senha}".encode("utf-8")).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            cargo TEXT NOT NULL,
            role TEXT NOT NULL,
            senha_hash TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitantes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_visitante TEXT NOT NULL,
            data_hora_utc TEXT NOT NULL
        )
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS chamadas (id INTEGER PRIMARY KEY AUTOINCREMENT, data_aula TEXT NOT NULL, aluno_id INTEGER NOT NULL, presente INTEGER NOT NULL, registrado_em TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, data_evento TEXT NOT NULL, local TEXT NOT NULL, categoria TEXT NOT NULL)")

    cur = conn.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO usuarios (nome, email, cargo, role, senha_hash, ativo) VALUES (?, ?, ?, ?, ?, 1)",
            ("Mestre Martelo (Admin)", "admin@familiamartelopredador.org.br", "Fundador & Administrador Geral", "admin", hash_pwd(DEFAULT_ADMIN_PASS))
        )
    conn.commit()
    conn.close()

init_db()

def get_current_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.")
    token = authorization.replace("Bearer ", "").strip()
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token não autorizado.")
    return user

def exigir_permissao(user: dict, roles_permitidos: set):
    if user["role"] not in roles_permitidos:
        raise HTTPException(status_code=403, detail=f"Perfil '{user['role']}' não possui permissão para editar este recurso.")

class LoginRequest(BaseModel):
    email: str
    senha: str

class VisitanteRequest(BaseModel):
    nome: str

class NovoUsuarioRequest(BaseModel):
    nome: str
    email: str
    cargo: str
    role: str
    senha: str

class AlterarSenhaRequest(BaseModel):
    nova_senha: str

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
        "rbac": ["admin", "super_admin", "professor", "monitor", "estagiario", "visitante"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM usuarios WHERE lower(email) = lower(?) AND ativo = 1", (payload.email.strip(),)).fetchone()
    conn.close()
    if not row or row["senha_hash"] != hash_pwd(payload.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    token = secrets.token_hex(24)
    user_data = {"id": row["id"], "nome": row["nome"], "email": row["email"], "cargo": row["cargo"], "role": row["role"]}
    SESSIONS[token] = user_data
    return {"token": token, "user": user_data}

@app.post("/api/auth/visitante")
def entrar_visitante(payload: VisitanteRequest):
    nome_limpo = payload.nome.strip()
    if len(nome_limpo) < 2:
        raise HTTPException(status_code=400, detail="Informe seu nome completo para entrar como visitante.")
    agora = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO visitantes_log (nome_visitante, data_hora_utc) VALUES (?, ?)", (nome_limpo, agora))
    conn.commit()
    conn.close()
    token = secrets.token_hex(24)
    user_data = {"id": 0, "nome": f"{nome_limpo} (Visitante)", "email": "visitante@leitura", "cargo": "Modo Leitura • Sem Edição", "role": "visitante"}
    SESSIONS[token] = user_data
    return {"token": token, "user": user_data}

@app.get("/api/admin/visitantes")
def listar_visitantes(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, nome_visitante, data_hora_utc FROM visitantes_log ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/admin/usuarios")
def listar_usuarios(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, nome, email, cargo, role, ativo FROM usuarios ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/usuarios")
def criar_usuario(payload: NovoUsuarioRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin"})
    if payload.role not in ROLES_VALIDOS:
        raise HTTPException(status_code=400, detail="Categoria de acesso inválida.")
    if len(payload.senha) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres.")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, cargo, role, senha_hash, ativo) VALUES (?, ?, ?, ?, ?, 1)",
            (payload.nome.strip(), payload.email.strip().lower(), payload.cargo.strip(), payload.role, hash_pwd(payload.senha))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Já existe um usuário cadastrado com este e-mail.")
    conn.close()
    return {"status": "ok"}

@app.put("/api/admin/usuarios/{user_id}/senha")
def alterar_senha(user_id: int, payload: AlterarSenhaRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin"})
    if len(payload.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres.")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (hash_pwd(payload.nova_senha), user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.put("/api/admin/usuarios/{user_id}/status")
def alternar_status_usuario(user_id: int, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin"})
    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta de administrador.")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE usuarios SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.post("/api/chamadas/lote")
def salvar_chamada_lote(payload: ChamadaLoteRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin", "super_admin", "professor", "monitor"})
    conn = sqlite3.connect(DB_PATH)
    agora = datetime.now(timezone.utc).isoformat()
    for item in payload.registros:
        conn.execute("INSERT INTO chamadas (data_aula, aluno_id, presente, registrado_em) VALUES (?, ?, ?, ?)", (payload.data_aula, item.aluno_id, int(item.presente), agora))
    conn.commit()
    conn.close()
    return {"status": "ok", "total_registrado": len(payload.registros), "data_aula": payload.data_aula}

@app.post("/api/eventos")
def criar_evento(payload: EventoRequest, authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    exigir_permissao(user, {"admin", "super_admin"})
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO eventos (titulo, data_evento, local, categoria) VALUES (?, ?, ?, ?)", (payload.titulo, payload.data_evento, payload.local, payload.categoria))
    conn.commit()
    conn.close()
    return {"status": "ok", "evento": payload.model_dump()}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")