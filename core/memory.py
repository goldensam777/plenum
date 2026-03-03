"""
core/memory.py — Persistance des sessions du Plenum
=====================================================
Exporte et importe l'historique en JSON.
Chaque session devient une archive de délibération collective.

Interface avec plenum.py :
    save_session(salon.history)  → écrit sessions/session_YYYYMMDD_HHMMSS.json
    load_session(filepath)       → retourne list[Message] injectable dans salon.history
"""

import json
import os
from datetime import datetime
from typing import Optional

from agents.base_agent import Message


# Dossier de stockage des sessions — à côté de main.py
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "sessions")


def save_session(history: list[Message], name: Optional[str] = None) -> str:
    """
    Sauvegarde l'historique en JSON dans sessions/.
    Retourne le chemin du fichier créé.

    name : nom optionnel (sans extension). Sinon timestamp automatique.
    """
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    session_name = name or datetime.now().strftime("session_%Y%m%d_%H%M%S")
    filepath = os.path.join(SESSIONS_DIR, f"{session_name}.json")

    data = {
        "name": session_name,
        "saved_at": datetime.now().isoformat(),
        "message_count": len(history),
        "history": [
            {
                "role": msg.role,
                "agent": msg.agent,
                "content": msg.content,
                "timestamp": msg.timestamp,
            }
            for msg in history
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


def load_session(filepath: str) -> list[Message]:
    """
    Charge un fichier de session JSON.
    Retourne list[Message] prêt à être injecté dans salon.history.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        Message(
            role=item["role"],
            agent=item["agent"],
            content=item["content"],
            timestamp=item["timestamp"],
        )
        for item in data["history"]
    ]


def list_sessions() -> list[dict]:
    """
    Liste les sessions sauvegardées dans sessions/.
    Retourne [{name, path, saved_at, message_count}, ...] triée par date.
    """
    if not os.path.exists(SESSIONS_DIR):
        return []

    sessions = []
    for fname in sorted(os.listdir(SESSIONS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "name": data.get("name", fname[:-5]),
                "path": path,
                "saved_at": data.get("saved_at", "?"),
                "message_count": data.get("message_count", 0),
            })
        except Exception:
            continue

    return sessions
