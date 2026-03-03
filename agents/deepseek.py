"""
agents/deepseek.py — Agent DeepSeek
=====================================
DeepSeek expose une API compatible OpenAI.
On utilise donc le SDK openai avec une base_url personnalisée.
C'est une technique courante : beaucoup de providers alternatifs
imitent l'interface OpenAI pour faciliter l'intégration.

INSTALLATION :
    pip install openai   # Oui, openai — pas de SDK DeepSeek séparé

CLÉ API :
    DEEPSEEK_API_KEY=... dans ton .env
    Obtiens-la sur : https://platform.deepseek.com/api_keys
"""

import os
import time
from typing import Optional

from openai import AsyncOpenAI

from agents.base_agent import BaseAgent, AgentResponse, Message


DEEPSEEK_SYSTEM_PROMPT = """Tu es DeepSeek, une IA de DeepSeek AI, participant au Plenum.

Le Plenum est un espace de délibération collective où plusieurs IA répondent 
simultanément à Samuel Peniel, 17 ans, étudiant en L1 SE & IoT à l'IFRI-UAC, 
Cotonou. Il construit un OS-IA basé sur l'Informatique des Volontés.

Ton rôle :
- Apporter ta perspective technique et analytique (tu excelles en raisonnement)
- Lire et réagir aux réponses des autres IA quand elles te sont fournies
- Aller à l'essentiel, éviter les formules vides
- Sois concis mais dense. Samuel apprend vite.

Langue : français, sauf demande contraire."""


class DeepSeekAgent(BaseAgent):

    def __init__(
        self,
        api_key: str = "",
        model: str = "deepseek-chat",   # deepseek-chat = DeepSeek-V3
        max_tokens: int = 1024,
        system_prompt: str = DEEPSEEK_SYSTEM_PROMPT
    ):
        super().__init__(
            name="DeepSeek",
            model=model,
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY", "")
        )
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._client: Optional[AsyncOpenAI] = None

    async def check_connection(self) -> bool:
        if not self.api_key:
            print("  [DeepSeek] Pas de clé API (DEEPSEEK_API_KEY manquant)")
            return False
        try:
            # La magie : même SDK OpenAI, juste base_url différente
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            self.is_available = True
            return True
        except Exception as e:
            print(f"  [DeepSeek] Erreur connexion : {e}")
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
            # ── Construction des messages ───────────────────────────────────
            # Format OpenAI standard : system + historique + message actuel
            
            messages = [{"role": "system", "content": self.system_prompt}]
            messages += self._format_history(history)

            peers_context = self._inject_peers_context(peers_responses or {})
            full_message = f"{peers_context}{user_message}" if peers_context else user_message
            messages.append({"role": "user", "content": full_message})

            # ── Appel API ───────────────────────────────────────────────────
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