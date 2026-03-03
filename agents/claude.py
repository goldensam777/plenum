"""
agents/claude.py — Agent Claude (Anthropic)
============================================
Premier agent concret du Plenum.
C'est le plus simple à implémenter car la lib anthropic est
directe et bien documentée.

INSTALLATION REQUISE :
    pip install anthropic

CLÉ API :
    Crée un fichier .env à la racine du projet :
        ANTHROPIC_API_KEY=sk-ant-...

    Ou passe-la directement au constructeur (déconseillé en prod).
"""

import os
import time
import asyncio
from typing import Optional

import anthropic

from agents.base_agent import BaseAgent, AgentResponse, Message


# ── Prompt système de Claude dans le Plenum ─────────────────────────────────
# Ce prompt définit l'identité de Claude AU SEIN du Plenum.
# Il sait qu'il est dans un salon multi-IA — ça change sa façon de répondre.
# Il ne fait pas semblant d'être seul.

CLAUDE_SYSTEM_PROMPT = """Tu es Claude, une IA d'Anthropic, participant au Plenum.

Le Plenum est un espace de délibération collective où plusieurs IA (toi, ChatGPT, 
Gemini, DeepSeek, Kimi) répondent simultanément à Samuel Peniel, 17 ans, 
étudiant en L1 SE & IoT à l'IFRI-UAC, Cotonou. Il construit un OS-IA basé sur 
l'Informatique des Volontés.

Ton rôle dans ce Salon :
- Répondre avec précision et profondeur à Samuel
- Quand les réponses des autres IA te sont fournies, tu peux les lire,
  les commenter, les contredire ou les enrichir — avec bienveillance
- Tu n'es pas en compétition, tu es en délibération
- Sois concis mais dense. Samuel apprend vite.

Langue : français, sauf si Samuel demande autre chose."""


class ClaudeAgent(BaseAgent):
    """
    Agent Claude — wraps l'API Anthropic de façon asynchrone.
    
    Exemple d'instanciation :
        agent = ClaudeAgent(api_key="sk-ant-...")
        # ou avec variable d'environnement :
        agent = ClaudeAgent()
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-opus-4-6",  # Modèle par défaut : le plus récent
        max_tokens: int = 1024,
        system_prompt: str = CLAUDE_SYSTEM_PROMPT
    ):
        # On appelle __init__ du parent avec nos valeurs
        super().__init__(
            name="Claude",
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

        # Le client Anthropic — None jusqu'à check_connection()
        # On ne crée pas le client avant de savoir si la clé est valide
        self._client: Optional[anthropic.AsyncAnthropic] = None

    # ── Connexion ───────────────────────────────────────────────────────────

    async def check_connection(self) -> bool:
        """
        Vérifie que la clé API est valide en faisant un appel minimal.
        On envoie un message court — si ça répond, la connexion est OK.
        """
        if not self.api_key:
            print(f"  [Claude] Pas de clé API (ANTHROPIC_API_KEY manquant)")
            return False
        
        try:
            # AsyncAnthropic = version asynchrone du client
            # Essentiel pour ne pas bloquer la boucle asyncio
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Appel test minimal
            await self._client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            self.is_available = True
            return True
        
        except anthropic.AuthenticationError:
            print(f"  [Claude] Clé API invalide")
            return False
        
        except Exception as e:
            print(f"  [Claude] Erreur connexion : {e}")
            return False

    # ── Méthode principale ──────────────────────────────────────────────────

    async def ask(
        self,
        user_message: str,
        history: list[Message],
        peers_responses: Optional[dict[str, str]] = None
    ) -> AgentResponse:
        """
        Envoie un message à Claude et retourne sa réponse.
        
        Construction du prompt :
        1. Historique formaté (les tours précédents)
        2. Contexte pairs (si Phase 2 — les réponses des autres IA)
        3. Message de Samuel (tour actuel)
        
        Pourquoi cette structure ?
        L'API Anthropic attend une liste de messages alternés user/assistant.
        On reconstruit cette liste depuis notre historique global.
        """
        if not self._client:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                latency_ms=0,
                error="Client non initialisé. Appelle check_connection() d'abord."
            )

        start_time = time.time()

        try:
            # ── Construction des messages ───────────────────────────────────
            
            # 1. Historique des tours précédents (format API)
            messages = self._format_history(history)
            
            # 2. Message du tour actuel
            # Si on a des réponses pairs (Phase 2), on les injecte DANS
            # le message utilisateur, pas en tant que message séparé.
            # Pourquoi ? L'API attend user/assistant/user/assistant...
            # pas user/context/user. On enrichit le message user directement.
            
            peers_context = self._inject_peers_context(peers_responses or {})
            full_user_message = f"{peers_context}{user_message}" if peers_context else user_message
            
            messages.append({"role": "user", "content": full_user_message})

            # ── Appel API ───────────────────────────────────────────────────
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,   # Prompt système séparé chez Anthropic
                messages=messages
            )

            # ── Extraction de la réponse ────────────────────────────────────
            # response.content est une liste de blocs (TextBlock, ToolUseBlock...)
            # On prend le premier bloc texte
            content = response.content[0].text
            latency = self._timed_response(start_time, content)

            return AgentResponse(
                agent_name=self.name,
                content=content,
                success=True,
                latency_ms=latency
            )

        except anthropic.RateLimitError:
            latency = (time.time() - start_time) * 1000
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                latency_ms=latency,
                error="Rate limit atteint. Attends quelques secondes."
            )

        except anthropic.APIError as e:
            latency = (time.time() - start_time) * 1000
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                latency_ms=latency,
                error=f"Erreur API Anthropic : {e}"
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                latency_ms=latency,
                error=f"Erreur inattendue : {e}"
            )