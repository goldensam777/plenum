"""
main.py — Point d'entrée du Plenum
====================================
Lance le serveur web FastAPI accessible depuis le navigateur et le téléphone.

Usage :
  python main.py           → http://localhost:8000
  python main.py --cli     → mode terminal (ancien comportement)

Accès téléphone (même réseau Wi-Fi) :
  Le serveur affiche l'IP locale au démarrage, ex: http://192.168.1.42:8000
"""

import asyncio
import os
import socket
import sys

import uvicorn
from dotenv import load_dotenv

from agents.claude import ClaudeAgent
from agents.gemini import GeminiAgent
from agents.deepseek import DeepSeekAgent
from agents.chatgpt import ChatGPTAgent
from agents.kimi import KimiAgent
from core.plenum import Salon
from core.memory import save_session, list_sessions
from core.display import display_responses, display_status, display_banner

# ── Chargement .env ──────────────────────────────────────────────────────────
load_dotenv()


# ── Construction des agents ──────────────────────────────────────────────────

def build_agents() -> list:
    """
    Instancie les 5 agents avec leurs clés API.
    Un agent sans clé sera marqué indisponible par check_connection().
    """
    return [
        ClaudeAgent(api_key=os.getenv("ANTHROPIC_API_KEY", "")),
        GeminiAgent(api_key=os.getenv("GEMINI_API_KEY", "")),
        DeepSeekAgent(api_key=os.getenv("DEEPSEEK_API_KEY", "")),
        ChatGPTAgent(api_key=os.getenv("OPENAI_API_KEY", "")),
        KimiAgent(api_key=os.getenv("MOONSHOT_API_KEY", "")),
    ]


# ── Commandes spéciales ──────────────────────────────────────────────────────

HELP_TEXT = """
Commandes disponibles :
  /quit     — Quitte le Plenum (auto-sauvegarde si historique non vide)
  /reset    — Efface l'historique de la session en cours
  /export   — Sauvegarde manuelle de la session en JSON
  /status   — Affiche l'état des agents
  /sessions — Liste les sessions sauvegardées
  /help     — Ce message
"""


async def handle_command(cmd: str, salon: Salon) -> bool:
    """
    Traite une commande /xxx.
    Retourne False si on doit quitter, True sinon.
    """
    token = cmd.strip().lower()

    if token in ("/quit", "/exit", "/q"):
        if salon.history:
            filepath = save_session(salon.history)
            print(f"Session sauvegardée → {filepath}")
        print("\nAu revoir.\n")
        return False

    elif token == "/reset":
        salon.reset_history()

    elif token == "/export":
        if not salon.history:
            print("Aucun historique à exporter.")
        else:
            filepath = save_session(salon.history)
            print(f"Session exportée → {filepath}")

    elif token == "/status":
        status = {name: agent.is_available for name, agent in salon.agents.items()}
        display_status(status)

    elif token == "/sessions":
        sessions = list_sessions()
        if not sessions:
            print("Aucune session sauvegardée.")
        else:
            print("\nSessions sauvegardées :")
            for s in sessions:
                print(f"  {s['name']}  —  {s['message_count']} messages  —  {s['saved_at']}")
            print()

    elif token == "/help":
        print(HELP_TEXT)

    else:
        print(f"Commande inconnue : {cmd}  (tape /help)")

    return True


# ── Boucle principale ────────────────────────────────────────────────────────

async def main() -> None:
    display_banner()

    # Instanciation et enregistrement
    salon = Salon(timeout_seconds=30.0)
    for agent in build_agents():
        salon.register(agent)

    # Vérification des connexions
    status = await salon.initialize()
    display_status(status)

    available = [name for name, ok in status.items() if ok]
    if not available:
        print("Aucun agent disponible. Vérifie ton .env et tes clés API.")
        sys.exit(1)

    print(f"Agents actifs : {', '.join(available)}")
    print("Tape /help pour la liste des commandes.\n")

    # Réponses pairs du tour précédent (None au tour 1)
    last_responses: dict[str, str] = {}

    while True:
        try:
            user_input = input("Samuel › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            if salon.history:
                filepath = save_session(salon.history)
                print(f"Session sauvegardée → {filepath}")
            print("Au revoir.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            should_continue = await handle_command(user_input, salon)
            if not should_continue:
                break
            continue

        # Broadcast — pairs injectés dès le 2e tour
        peers = last_responses if last_responses else None
        responses = await salon.broadcast(user_input, peers_responses=peers)

        display_responses(responses, turn=salon.turn_count)

        # Prépare les réponses pairs pour le prochain tour
        last_responses = {
            name: resp.content
            for name, resp in responses.items()
            if resp.success
        }


# ── Lancement ────────────────────────────────────────────────────────────────

def get_local_ip() -> str:
    """Retourne l'IP locale pour l'accès téléphone."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"


if __name__ == "__main__":
    if "--cli" in sys.argv:
        # Mode terminal (ancien comportement)
        asyncio.run(main())
    else:
        # Mode web (défaut)
        host = "0.0.0.0"
        port = 8000
        local_ip = get_local_ip()
        print(f"\n  Plenum Web — http://localhost:{port}")
        print(f"  Téléphone  — http://{local_ip}:{port}\n")
        uvicorn.run("server:app", host=host, port=port, reload=False)
