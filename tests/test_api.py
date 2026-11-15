from fastapi.testclient import TestClient
from app.main import app, seed_dados_iniciais

seed_dados_iniciais()
client = TestClient(app)

def test_listar_turmas_autenticado():
    res = client.get("/api/turmas")
    assert res.status_code == 200
    assert len(res.json()) >= 1

def test_bloqueio_acesso_nao_autorizado_rnf01():
    res = client.get("/api/turmas", headers={"x-educador-token": "invalido"})
    assert res.status_code == 401

def test_ficha_medica_emergencia_rf02():
    res = client.get("/api/turmas/1/alunos")
    alunos = res.json()
    mariana = next(a for a in alunos if a["apelido"] == "Sereia")
    assert "Asma" in mariana["restricao_medica"]
    assert mariana["responsavel_telefone"] == "11987654321"

def test_registro_chamada_e_prevencao_duplicidade_rnf02():
    payload = {"data_aula": "2026-11-01",,"registros": [{"aluno_id": 1, "presente": True}, {"aluno_id": 2, "presente": True}, {"aluno_id": 3, "presente": False}]}
    res1 = client.post("/api/chamadas/lote", json=payload)
    assert res1.status_code == 201
    assert res1.json()["presentes"] == 2
    res2 = client.post("/api/chamadas/lote", json=payload)
    assert res2.status_code == 409
