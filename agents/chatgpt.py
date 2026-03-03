"""
agents/chatgpt.py — Agent ChatGPT (OpenAI)
===========================================
Pattern identique à DeepSeek — même SDK, même format de messages.
La seule différence : base_url pointe vers OpenAI par défaut.

INSTALLATION :
    pip install openai   # déjà installé si tu as fait DeepSeek

CLÉ API :
    OPENAI_API_KEY=... dans ton .env
    Obtiens-la sur : https://platform.openai.com/api-keys
    ⚠ Nécessite un crédit minimum (~5$) pour activer l'accès API
"""

import os
import time
from typing import Optional

from openai import AsyncOpenAI

from agents.base_agent import BaseAgent, AgentResponse, Message


CHATGPT_SYSTEM_PROMPT = """Tu es ChatGPT, une IA d'OpenAI, participant au Plenum.

Le Plenum est un espace de délibération collective où plusieurs IA répondent 
simultanément à Samuel Peniel, 17 ans, étudiant en L1 SE & IoT à l'IFRI-UAC, 
Cotonou. Il construit un OS-IA basé sur l'Informatique des Volontés.

Ton rôle :
- Apporter ta perspective OpenAI (clarté, pédagogie, large spectre)
- Lire et réagir aux réponses des autres IA quand elles te sont fournies
- Ne pas chercher le consensus — chercher la vérité utile
- Sois concis mais dense. Samuel apprend vite.

Langue : français, sauf demande contraire."""


class ChatGPTAgent(BaseAgent):

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o",
        max_tokens: int = 1024,
        system_prompt: str = CHATGPT_SYSTEM_PROMPT
    ):
        super().__init__(
            name="ChatGPT",
            model=model,
            api_key=api_key or os.getenv("OPENAI_API_KEY", "")
        )
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._client: Optional[AsyncOpenAI] = None

    async def check_connection(self) -> bool:
        if not self.api_key:
            print("  [ChatGPT] Pas de clé API (OPENAI_API_KEY manquant)")
            return False
        try:
            # Pas de base_url ici — OpenAI natif
            self._client = AsyncOpenAI(api_key=self.api_key)
            await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            self.is_available = True
            return True
        except Exception as e:
            print(f"  [ChatGPT] Erreur connexion : {e}")
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
