"""
salon.py — L'orchestrateur central du Salon Multi-IA
=====================================================
C'est le métronome dont Samuel est l'écho.
Il coordonne les 3 phases du flux à chaque tour de parole.

FLUX PAR TOUR :
  Phase 1 : Samuel envoie → 5 IA répondent en parallèle
  Phase 2 : Samuel voit les réponses, choisit à qui répondre (ou à tous)
            → Les IA reçoivent la réponse de Samuel + les réponses des pairs
  Phase 3 : L'historique est mis à jour pour le prochain tour

CONCEPT CLÉ — asyncio.gather() :
  Imagine 5 serveurs dans un restaurant.
  Sans async : le cuisinier prépare plat 1, attend, prépare plat 2, attend...
  Avec async  : le cuisinier lance les 5 plats, tous cuisent simultanément.
  gather() = "attends que TOUS les plats soient prêts avant de servir"
"""

import asyncio
import time
from typing import Optional

from agents.base_agent import BaseAgent, AgentResponse, Message


class Salon:
    """
    Le Salon Multi-IA.
    
    Usage :
        salon = Salon()
        salon.register(claude_agent)
        salon.register(gemini_agent)
        ...
        responses = await salon.broadcast("Quelle est ta vision de l'IA ?")
    """

    def __init__(self, timeout_seconds: float = 30.0):
        """
        timeout_seconds : si une IA ne répond pas dans ce délai,
        on la marque comme échouée et on continue.
        Sans timeout, une IA plantée bloquerait TOUT le salon.
        """
        self.agents: dict[str, BaseAgent] = {}  # {nom: agent}
        self.history: list[Message] = []         # Historique cumulatif global
        self.turn_count: int = 0
        self.timeout = timeout_seconds

    # ── Gestion des agents ──────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> None:
        """Enregistre un agent dans le salon."""
        self.agents[agent.name] = agent
        print(f"  + Agent enregistré : {agent}")

    def unregister(self, agent_name: str) -> None:
        """Retire un agent (utile si une API tombe en cours de session)."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            print(f"  - Agent retiré : {agent_name}")

    async def initialize(self) -> dict[str, bool]:
        """
        Vérifie la connexion de tous les agents en parallèle.
        Retourne {nom: True/False} pour savoir quels agents sont opérationnels.
        
        On utilise asyncio.gather() ici aussi — pas la peine d'attendre
        la connexion Claude avant de tester Gemini.
        """
        print("\n🔌 Vérification des connexions...\n")
        
        tasks = {
            name: agent.check_connection()
            for name, agent in self.agents.items()
        }
        
        # gather() avec return_exceptions=True : si une vérif plante,
        # on récupère l'exception plutôt que de tout arrêter
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )
        
        status = {}
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                status[name] = False
                self.agents[name].is_available = False
                print(f"  ✗ {name} : ERREUR — {result}")
            else:
                status[name] = bool(result)
                self.agents[name].is_available = bool(result)
                icon = "✓" if result else "✗"
                print(f"  {icon} {name} : {'OK' if result else 'INDISPONIBLE'}")
        
        available = sum(1 for v in status.values() if v)
        print(f"\n  {available}/{len(self.agents)} agents disponibles\n")
        return status

    # ── Cycle principal ─────────────────────────────────────────────────────

    async def broadcast(
        self,
        user_message: str,
        peers_responses: Optional[dict[str, str]] = None,
        target_agents: Optional[list[str]] = None
    ) -> dict[str, AgentResponse]:
        """
        Envoie un message à tous les agents (ou à une liste cible)
        et collecte leurs réponses en parallèle.
        
        Paramètres :
        - user_message    : Le message de Samuel
        - peers_responses : Si Phase 2, contient les réponses du tour précédent
        - target_agents   : Si None → broadcast à tous. Sinon → liste de noms.
        
        Retourne : {nom_agent: AgentResponse}
        """
        self.turn_count += 1
        
        # Sélection des agents cibles
        targets = {
            name: agent
            for name, agent in self.agents.items()
            if agent.is_available and (target_agents is None or name in target_agents)
        }
        
        if not targets:
            print("⚠ Aucun agent disponible.")
            return {}

        # Enregistrement du message de Samuel dans l'historique
        self.history.append(Message(
            role="user",
            content=user_message,
            agent="samuel"
        ))

        # ── Lancement parallèle ─────────────────────────────────────────────
        # On crée une coroutine par agent, enveloppée dans un timeout.
        # asyncio.wait_for() : si l'agent dépasse self.timeout secondes → exception

        async def ask_with_timeout(name: str, agent: BaseAgent) -> tuple[str, AgentResponse]:
            """Wrapper qui ajoute le timeout et gère les erreurs proprement."""
            start = time.time()
            try:
                response = await asyncio.wait_for(
                    agent.ask(user_message, self.history.copy(), peers_responses),
                    timeout=self.timeout
                )
                return name, response
            
            except asyncio.TimeoutError:
                latency = (time.time() - start) * 1000
                return name, AgentResponse(
                    agent_name=name,
                    content="",
                    success=False,
                    latency_ms=latency,
                    error=f"Timeout après {self.timeout}s"
                )
            
            except Exception as e:
                latency = (time.time() - start) * 1000
                return name, AgentResponse(
                    agent_name=name,
                    content="",
                    success=False,
                    latency_ms=latency,
                    error=str(e)
                )

        # gather() lance TOUTES les tâches en même temps
        # Le résultat arrive quand la DERNIÈRE tâche se termine
        raw_results = await asyncio.gather(
            *[ask_with_timeout(name, agent) for name, agent in targets.items()]
        )

        # ── Collecte et enregistrement ──────────────────────────────────────
        responses = dict(raw_results)
        
        for name, resp in responses.items():
            if resp.success:
                # On ajoute la réponse de chaque IA à l'historique global
                self.history.append(Message(
                    role="assistant",
                    content=resp.content,
                    agent=name.lower()
                ))

        return responses

    # ── Méthodes utilitaires ────────────────────────────────────────────────

    def get_history_summary(self) -> str:
        """Résumé lisible de l'historique pour debug."""
        lines = [f"=== Historique — {len(self.history)} messages ==="]
        for msg in self.history[-10:]:  # 10 derniers
            preview = msg.content[:80].replace('\n', ' ')
            lines.append(f"  [{msg.agent}] {preview}...")
        return "\n".join(lines)

    def get_last_responses(self) -> dict[str, str]:
        """
        Récupère les dernières réponses de chaque agent.
        Utile pour construire peers_responses au tour suivant.
        """
        last = {}
        # Parcours à l'envers pour trouver la dernière réponse de chaque agent
        for msg in reversed(self.history):
            if msg.role == "assistant" and msg.agent not in last:
                last[msg.agent] = msg.content
            if len(last) == len(self.agents):
                break
        return last

    def reset_history(self) -> None:
        """Remet à zéro l'historique (nouvelle session)."""
        self.history.clear()
        self.turn_count = 0
        print("🔄 Historique effacé.")

    def export_session(self, filepath: str) -> None:
        """
        Exporte la session en JSON pour relecture.
        Utile pour l'OS-IA : chaque session devient une donnée d'entraînement.
        """
        import json
        session_data = {
            "turn_count": self.turn_count,
            "agents": list(self.agents.keys()),
            "history": [
                {
                    "role": msg.role,
                    "agent": msg.agent,
                    "content": msg.content,
                    "timestamp": msg.timestamp
                }
                for msg in self.history
            ]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        print(f"Session exportée → {filepath}")

    def __repr__(self):
        agents_str = ", ".join(self.agents.keys())
        return f"Salon(agents=[{agents_str}], turns={self.turn_count})"