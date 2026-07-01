import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from database.mongo import conectar, desconectar, get_db
from agents.onboarding import processar_turno
from agents.narrator import narrar_stream

app = FastAPI(title="RPG Narrado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await conectar()
    await _seed_sistemas()


@app.on_event("shutdown")
async def shutdown():
    await desconectar()


async def _seed_sistemas():
    """Carrega os sistemas de RPG no banco se ainda não existirem."""
    db = get_db()
    sistemas_path = Path(__file__).parent / "systems"
    for arquivo in sistemas_path.glob("*.json"):
        sistema = json.loads(arquivo.read_text(encoding="utf-8"))
        await db.systems.update_one(
            {"id": sistema["id"]},
            {"$set": sistema},
            upsert=True,
        )


# ── Sistemas ──────────────────────────────────────────────────────────────────

@app.get("/sistemas")
async def listar_sistemas():
    db = get_db()
    sistemas = await db.systems.find({}, {"_id": 0, "id": 1, "nome": 1, "descricao": 1, "imagem": 1}).to_list(20)
    return sistemas


# ── Sessões ───────────────────────────────────────────────────────────────────

@app.get("/sessoes")
async def listar_sessoes():
    db = get_db()
    sessoes = await db.sessions.find(
        {"status": {"$ne": "abandonada"}},
        {"historico_chat": 0}
    ).sort("atualizado_em", -1).to_list(20)
    for s in sessoes:
        s["_id"] = str(s["_id"])
    return sessoes


class NovaSessaoBody(BaseModel):
    sistema_id: str


@app.post("/sessoes")
async def criar_sessao(body: NovaSessaoBody):
    db = get_db()
    sistema = await db.systems.find_one({"id": body.sistema_id})
    if not sistema:
        raise HTTPException(404, "Sistema não encontrado")

    session_id = str(uuid.uuid4())
    sessao = {
        "_id": session_id,
        "sistema_id": body.sistema_id,
        "sistema_nome": sistema["nome"],
        "status": "onboarding",
        "turno": 0,
        "localizacao": "Início da aventura",
        "historico_chat": [],
        "historico_onboarding": [],
        "criado_em": datetime.utcnow(),
        "atualizado_em": datetime.utcnow(),
    }
    await db.sessions.insert_one(sessao)
    return {"session_id": session_id, "sistema": sistema["nome"]}


# ── Onboarding ────────────────────────────────────────────────────────────────

class OnboardingBody(BaseModel):
    mensagem: str


@app.post("/sessoes/{session_id}/onboarding")
async def onboarding_turno(session_id: str, body: OnboardingBody):
    db = get_db()
    sessao = await db.sessions.find_one({"_id": session_id})
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    if sessao["status"] != "onboarding":
        raise HTTPException(400, "Sessão não está em onboarding")

    sistema = await db.systems.find_one({"id": sessao["sistema_id"]})

    # Adiciona mensagem do usuário ao histórico de onboarding
    historico = sessao.get("historico_onboarding", [])
    historico.append({"role": "user", "content": body.mensagem})

    resultado = await processar_turno(session_id, historico, sistema)

    if resultado["tipo"] == "concluido":
        # Onboarding concluído — muda status e inicia o jogo
        await db.sessions.update_one(
            {"_id": session_id},
            {"$set": {"status": "ativo", "atualizado_em": datetime.utcnow()}}
        )
        personagem = resultado["personagem"]
        personagem.pop("_id", None)
        personagem.pop("session_id", None)
        return {"tipo": "concluido", "personagem": personagem}

    # Continua o onboarding
    historico.append({"role": "assistant", "content": resultado["conteudo"]})
    await db.sessions.update_one(
        {"_id": session_id},
        {"$set": {"historico_onboarding": historico, "atualizado_em": datetime.utcnow()}}
    )
    return {"tipo": "mensagem", "conteudo": resultado["conteudo"]}


# ── Jogo ──────────────────────────────────────────────────────────────────────

class AcaoBody(BaseModel):
    acao: str


@app.post("/sessoes/{session_id}/acao")
async def executar_acao(session_id: str, body: AcaoBody):
    db = get_db()
    sessao = await db.sessions.find_one({"_id": session_id})
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    if sessao["status"] != "ativo":
        raise HTTPException(400, "Sessão não está ativa")

    async def gerador():
        # narrator.py já gera eventos SSE formatados — apenas passamos adiante
        async for evento in narrar_stream(session_id, body.acao):
            yield evento
        yield "data: [DONE]\n\n"

    return StreamingResponse(gerador(), media_type="text/event-stream")


@app.get("/sessoes/{session_id}")
async def obter_sessao(session_id: str):
    db = get_db()
    sessao = await db.sessions.find_one({"_id": session_id}, {"historico_onboarding": 0})
    if not sessao:
        raise HTTPException(404, "Sessão não encontrada")
    personagem = await db.characters.find_one({"session_id": session_id}, {"_id": 0})
    sessao["_id"] = str(sessao["_id"])
    return {"sessao": sessao, "personagem": personagem}
