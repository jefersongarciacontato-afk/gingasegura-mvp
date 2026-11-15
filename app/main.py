from datetime import date
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Aluno, Base, Frequencia, SessionLocal, Turma, engine

Base.metadata.create_all(bind=engine)
app = FastAPI(title="GingaSegura MVP", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verificar_educador(x_educador_token: str = Header(default="mestre-martelo-ok")):
    if not x_educador_token or x_educador_token == "invalido":
        raise HTTPException(status_code=401, detail="Sessao de educador nao autorizada")
    return x_educador_token

class ItemChamada(BaseModel):
    aluno_id: int
    presente: bool

class LoteChamadaSxchema(BaseModel):
    data_aula: date
    registros: List[ItemChamada] = Field(..., min_length=1)

@app.on_event("startup")
def seed_dados_iniciais():
    db = SessionLocal()
    if not db.query(Turma).first():
        t1 = Turma(nome="Capoeira Infantil (6 a 12 anos)", horario="18h30 - Ter / Qui")
        db.add(t1)
        db.commit()
        db.refresh(t1)
        db.add_all([
            Aluno(nome="Lucas Silva", apelido="Gafanhoto", corda="Corda Crua", responsavel_nome="Carlos Silva", responsavel_telefone="11999990001", turma_id=t1.id),
            Aluno(nome="Mariana Souza", apelido="Sereia", corda="Corda Amarela", alergia="Picada de insetos", restricao_medica="Asma (Usa bombinha)", responsavel_nome="Ana Souza", responsavel_telefone="11987654321", turma_id=t1.id),
            Aluno(nome="Caua Oliveira", apelido="Tigre", corda="Corda Crua", responsavel_nome="Marcos Oliveira", responsavel_telefone="11999990003", turma_id=t1.id),
        ])
        db.commit()
    db.close()

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/turmas")
def listar_turmas(db: Session = Depends(get_db), _: str = Depends(verificar_educador)):
    return db.query(Turma).all()

@app.get("/api/turmas/{turma_id}/alunos")
def listar_alunos_turma(turma_id: int, db: Session = Depends(get_db), _: str = Depends(verificar_educador)):
    return db.query(Aluno).filter(Aluno.turma_id == turma_id).all()

@app.post("/api/chamadas/lote", status_code=201)
def registrar_chamada_lote(payload: LoteChamadaSxchema, db: Session = Depends(get_db), _: str = Depends(verificar_educador)):
    try:
        for item in payload.registros:
            db.add(Frequencia(aluno_id=item.aluno_id, data_aula=payload.data_aula, presente=item.presente))
        db.commit()
        presentes = sum(1 for r in payload.registros if r.presente)
        return {"status": "sincronizado", "presentes": presentes, "ausentes": len(payload.registros) - presentes}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Chamada ja registrada para aluno nesta data.")
