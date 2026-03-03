"""
agents/kimi.py — Agent Kimi K2 (Moonshot AI)
=============================================
Kimi K2 est le modèle de Moonshot AI (Chine).
Bonne nouvelle : Moonshot expose une API compatible OpenAI.
Même SDK, même format — juste base_url et model qui changent.

Kimi K2 excelle en :
- Raisonnement long et complexe
- Code et mathématiques
- Contexte très long (128k tokens)

INSTALLATION :
    pip install openai   # déjà installé

CLÉ API :
    MOONSHOT_API_KEY=... dans ton .env
    Obtiens-la sur : https://platform.moonshot.cn/console/api-keys
    ⚠ Interface en chinois — utilise Google Translate si besoin
    Crée un compte, ajoute un petit crédit (~1$), génère une clé.
"""

import os
import time
from typing import Optional

from openai import AsyncOpenAI

from agents.base_agent import BaseAgent, AgentResponse, Message


KIMI_SYSTEM_PROMPT = """Tu es Kimi K2, une IA de Moonshot AI, participant au Plenum.

Le Plenum est un espace de délibération collective où plusieurs IA répondent 
simultanément à Samuel Peniel, 17 ans, étudiant en L1 SE & IoT à l'IFRI-UAC, 
Cotonou. Il construit un OS-IA basé sur l'Informatique des Volontés.

Ton rôle :
- Apporter ta perspective Moonshot AI (raisonnement long, précision technique)
- Lire et réagir aux réponses des autres IA quand elles te sont fournies
- Aller en profondeur là où les autres restent en surface
- Sois concis mais dense. Samuel apprend vite.

Langue : français, sauf demande contraire."""


class KimiAgent(BaseAgent):

    def __init__(
        self,
        api_key: str = "",
        model: str = "kimi-k2",          # Modèle K2 de Moonshot
        max_tokens: int = 1024,
        system_prompt: str = KIMI_SYSTEM_PROMPT
    ):
        super().__init__(
            name="Kimi",
            model=model,
            api_key=api_key or os.getenv("MOONSHOT_API_KEY", "")
        )
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._client: Optional[AsyncOpenAI] = None

    async def check_connection(self) -> bool:
        if not self.api_key:
            print("  [Kimi] Pas de clé API (MOONSHOT_API_KEY manquant)")
            return False
        try:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.moonshot.cn/v1"
            )
            # Test minimal avec moonshot-v1-8k (moins cher pour le ping)
            await self._client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            self.is_available = True
            return True
        except Exception as e:
            print(f"  [Kimi] Erreur connexion : {e}")
            return False

    async def ask(
        self,
        user_message: str,
        history: list[Message],
        peers_responses: Optional[dict[str, str]] = None
    ) -> AgentResponse:

        if not self._client:
            return AgentResponse(
                agent_name=self.name, content="", success=False,
                latency_ms=0, error="Client non initialisé."
            )

        start_time = time.time()

        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages += self._format_history(history)

            peers_context = self._inject_peers_context(peers_responses or {})
            full_message = f"{peers_context}{user_message}" if peers_context else user_message
            messages.append({"role": "user", "content": full_message})

            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )

            content = response.choices[0].message.content
            latency = self._timed_response(start_time, content)

            return AgentResponse(
                agent_name=self.name,
                content=content,
                success=True,
                latency_ms=latency
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return AgentResponse(
                agent_name=self.name, content="", success=False,
                latency_ms=latency, error=str(e)
            )
