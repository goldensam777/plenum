"""
agents/gemini.py — Agent Gemini (Google)
=========================================
INSTALLATION :
    pip install google-genai

CLÉ API :
    GEMINI_API_KEY=... dans ton .env
    Obtiens-la sur : https://aistudio.google.com/app/apikey
"""

import os
import time
from typing import Optional

from google import genai
from google.genai import types

from agents.base_agent import BaseAgent, AgentResponse, Message


GEMINI_SYSTEM_PROMPT = """Tu es Gemini, une IA de Google, participant au Plenum.

Le Plenum est un espace de délibération collective où plusieurs IA répondent 
simultanément à Samuel Peniel, 17 ans, étudiant en L1 SE & IoT à l'IFRI-UAC, 
Cotonou. Il construit un OS-IA basé sur l'Informatique des Volontés.

Ton rôle :
- Apporter ta perspective Google (multimodal, large contexte, raisonnement)
- Lire et réagir aux réponses des autres IA quand elles te sont fournies
- Être direct, structuré, et ne pas hésiter à être en désaccord
- Sois concis mais dense. Samuel apprend vite.

Langue : français, sauf demande contraire."""


class GeminiAgent(BaseAgent):

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-2.0-flash",
        max_tokens: int = 1024,
        system_prompt: str = GEMINI_SYSTEM_PROMPT
    ):
        super().__init__(
            name="Gemini",
            model=model,
            api_key=api_key or os.getenv("GEMINI_API_KEY", "")
        )
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self._client: Optional[genai.Client] = None

    async def check_connection(self) -> bool:
        if not self.api_key:
            print("  [Gemini] Pas de clé API (GEMINI_API_KEY manquant)")
            return False
        try:
            self._client = genai.Client(api_key=self.api_key)
            # Test minimal
            self._client.models.generate_content(
                model=self.model,
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            self.is_available = True
            return True
        except Exception as e:
            print(f"  [Gemini] Erreur connexion : {e}")
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
            # ── Construction de l'historique au format Gemini ───────────────
            # Gemini attend : [{"role": "user/model", "parts": [{"text": "..."}]}]
            # Différence clé vs Anthropic : "assistant" s'appelle "model" ici
            
            contents = []
            for msg in self._format_history(history):
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=msg["content"])]
                    )
                )

            # Message du tour actuel avec contexte pairs
            peers_context = self._inject_peers_context(peers_responses or {})
            full_message = f"{peers_context}{user_message}" if peers_context else user_message
            
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=full_message)]
                )
            )

            # ── Appel API ───────────────────────────────────────────────────
            # Note : google-genai n'a pas encore de méthode async native stable
            # On utilise la version sync dans un executor pour ne pas bloquer asyncio
            import asyncio
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,  # executor par défaut (ThreadPoolExecutor)
                lambda: self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        max_output_tokens=self.max_tokens,
                    )
                )
            )

            content = response.text
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