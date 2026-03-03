"""
server.py — Backend FastAPI du Plenum
======================================
Expose le Salon Multi-IA comme une API REST consommée par le frontend HTML/JS.

Routes :
  GET  /           → sert static/index.html
  GET  /status     → état des agents
  POST /chat       → broadcast + réponses JSON
  POST /reset      → efface l'historique
  POST /export     → sauvegarde la session
  GET  /sessions   → liste des sessions sauvegardées
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from agents.claude import ClaudeAgent
from agents.gemini import GeminiAgent
from agents.deepseek import DeepSeekAgent
from agents.chatgpt import ChatGPTAgent
from agents.kimi import KimiAgent
from core.plenum import Salon
from core.memory import save_session, list_sessions

load_dotenv()

# ── État global ──────────────────────────────────────────────────────────────
# Une seule instance de Salon partagée par toutes les requêtes.
# asynccontextmanager gère le cycle de vie : init au démarrage, rien à fermer.

salon: Salon = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global salon
    salon = Salon(timeout_seconds=30.0)

    agents = [
        ClaudeAgent(api_key=os.getenv("ANTHROPIC_API_KEY", "")),
        GeminiAgent(api_key=os.getenv("GEMINI_API_KEY", "")),
        DeepSeekAgent(api_key=os.getenv("DEEPSEEK_API_KEY", "")),
        ChatGPTAgent(api_key=os.getenv("OPENAI_API_KEY", "")),
        KimiAgent(api_key=os.getenv("MOONSHOT_API_KEY", "")),
    ]
    for agent in agents:
        salon.register(agent)

    await salon.initialize()
    print("Plenum prêt.")
    yield
    # Sauvegarde automatique à l'arrêt si historique non vide
    if salon.history:
        filepath = save_session(salon.history)
        print(f"Session auto-sauvegardée → {filepath}")


app = FastAPI(title="Plenum", lifespan=lifespan)

# Fichiers statiques (CSS, JS)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Modèles Pydantic ─────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/status")
async def status():
    """Retourne l'état de chaque agent."""
    return {
        name: {
            "available": agent.is_available,
            "model": agent.model,
        }
        for name, agent in salon.agents.items()
    }


@app.post("/chat")
async def chat(body: ChatRequest):
    """
    Envoie le message de Samuel à tous les agents disponibles.
    Injecte les réponses du tour précédent comme contexte pairs.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message vide.")

    available = [a for a in salon.agents.values() if a.is_available]
    if not available:
        raise HTTPException(status_code=503, detail="Aucun agent disponible.")

    # Réponses du tour précédent → contexte pairs pour ce tour
    peers = salon.get_last_responses() if salon.turn_count > 0 else None

    responses = await salon.broadcast(body.message, peers_responses=peers)

    return {
        "turn": salon.turn_count,
        "responses": {
            name: {
                "content": resp.content,
                "latency_ms": round(resp.latency_ms),
                "success": resp.success,
                "error": resp.error,
            }
            for name, resp in responses.items()
        },
    }


@app.post("/reset")
async def reset():
    """Efface l'historique de la session en cours."""
    salon.reset_history()
    return {"ok": True}


@app.post("/export")
async def export():
    """Sauvegarde la session actuelle en JSON."""
    if not salon.history:
        raise HTTPException(status_code=400, detail="Aucun historique à exporter.")
    filepath = save_session(salon.history)
    return {"path": filepath}


@app.get("/sessions")
async def sessions():
    """Liste les sessions sauvegardées."""
    return {"sessions": list_sessions()}
