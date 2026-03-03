"""
base_agent.py — Le contrat commun de tous les agents IA
========================================================
Tout agent du Salon DOIT hériter de BaseAgent et implémenter `ask()`.
C'est comme une prise électrique standard : peu importe l'appareil,
la forme de la prise ne change pas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import time


# ── Structure de réponse ────────────────────────────────────────────────────
# On utilise @dataclass pour avoir un objet propre plutôt qu'un dict.
# Avantage : autocomplétion, typage, lisibilité.

@dataclass
class AgentResponse:
    """Ce que chaque agent DOIT retourner — ni plus, ni moins."""
    agent_name: str          # "Claude", "Gemini", etc.
    content: str             # La réponse textuelle
    success: bool            # True si tout s'est bien passé
    latency_ms: float        # Temps de réponse en millisecondes
    error: Optional[str] = None  # Message d'erreur si success=False


# ── Message dans l'historique ───────────────────────────────────────────────
@dataclass
class Message:
    """Un tour de conversation : qui a dit quoi."""
    role: str       # "user" ou "assistant"
    content: str
    agent: str      # "samuel", "claude", "gemini", etc.
    timestamp: float = field(default_factory=time.time)


# ── La classe abstraite ─────────────────────────────────────────────────────
# ABC = Abstract Base Class. Un agent qui hérite mais n'implémente pas
# `ask()` lèvera une erreur IMMÉDIATEMENT à l'instanciation.
# C'est intentionnel : mieux vaut planter tôt que silencieusement.

class BaseAgent(ABC):
    """
    Interface que TOUS les agents doivent respecter.
    
    Règle simple :
    - Tu peux surcharger __init__ pour tes configs spécifiques
    - Tu DOIS implémenter ask()
    - Tu peux utiliser _format_history() pour préparer ton contexte
    """

    def __init__(self, name: str, model: str = "", api_key: str = ""):
        self.name = name          # Nom affiché dans l'interface
        self.model = model        # "claude-opus-4", "gemini-2.0-flash", etc.
        self.api_key = api_key
        self.is_available = False  # Devient True après _check_connection()

    @abstractmethod
    async def ask(
        self,
        user_message: str,
        history: list[Message],
        peers_responses: Optional[dict[str, str]] = None
    ) -> AgentResponse:
        """
        Envoie un message à l'IA et retourne sa réponse.

        Paramètres :
        - user_message    : Ce que Samuel a écrit ce tour-ci
        - history         : Tous les tours précédents (croît à chaque tour)
        - peers_responses : {nom_agent: réponse} des autres IA ce tour
                            → None au tour 1 (pas encore de réponses pairs)
                            → Rempli dès le tour 2 (Phase 2 du flux)
        """
        pass

    @abstractmethod
    async def check_connection(self) -> bool:
        """Vérifie que l'API/le navigateur est accessible. Appelé au démarrage."""
        pass

    # ── Méthodes utilitaires (disponibles pour tous les enfants) ─────────────

    def _format_history(self, history: list[Message], max_turns: int = 10) -> list[dict]:
        """
        Convertit notre historique interne en format messages API standard.
        La plupart des APIs attendent : [{"role": "user/assistant", "content": "..."}]
        
        max_turns : on garde les N derniers tours pour éviter les contextes trop longs.
        C'est le "fenêtre glissante" — technique classique en LLM engineering.
        """
        # On prend les derniers max_turns*2 messages (user + assistant = 2 par tour)
        recent = history[-(max_turns * 2):]
        
        formatted = []
        for msg in recent:
            if msg.role == "user":
                formatted.append({"role": "user", "content": msg.content})
            elif msg.agent == self.name.lower():
                # On ne prend que SES propres réponses pour son historique
                # Chaque IA a sa propre continuité narrative
                formatted.append({"role": "assistant", "content": msg.content})
        
        return formatted

    def _inject_peers_context(self, peers_responses: dict[str, str]) -> str:
        """
        Formate les réponses des autres IA pour les injecter dans le prompt.
        
        Exemple de sortie :
        '--- Contexte Salon ---
         ChatGPT a dit : [...]
         Gemini a dit : [...]
         ---------------------'
        
        Pourquoi injecter ça ? C'est la magie du Salon :
        chaque IA sait ce que les autres ont répondu et peut réagir,
        contredire, approfondir. C'est une vraie délibération collective.
        """
        if not peers_responses:
            return ""
        
        lines = ["", "--- Contexte Salon (réponses de tes co-IA ce tour) ---"]
        for agent_name, response in peers_responses.items():
            if agent_name != self.name:  # On n'injecte pas sa propre réponse
                lines.append(f"{agent_name} : {response[:500]}...")  # Tronqué à 500 chars
        lines.append("--- Fin Contexte Salon ---\n")
        
        return "\n".join(lines)

    def _timed_response(self, start_time: float, content: str) -> float:
        """Calcule la latence en ms depuis start_time."""
        return (time.time() - start_time) * 1000

    def __repr__(self):
        status = "✓" if self.is_available else "✗"
        return f"[{status}] {self.name} ({self.model})"