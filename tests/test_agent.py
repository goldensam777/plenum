# tests/test_agent.py
import asyncio
import sys
import os

# Ajoute la racine du projet au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def run(agent_class, agent_name, test_messages=None, peers_responses=None):
    """
    Template pour tester un agent.
    agent_class : classe de l'agent (ClaudeAgent, GeminiAgent, etc.)
    agent_name : nom string pour affichage
    test_messages : liste de messages à envoyer
    peers_responses : dictionnaire de réponses des autres IA pour Phase 2
    """
    print(f"\n=== Test Agent {agent_name} ===\n")

    agent = agent_class()
    print(f"Agent créé : {agent}\n")

    # Vérification de la connexion
    if hasattr(agent, "check_connection"):
        ok = await agent.check_connection()
        if not ok:
            print(f"❌ Connexion échouée pour {agent_name}. Vérifie la clé API.")
            return
        print(f"✓ Connexion OK — {agent_name}\n")

    # Messages de test
    if test_messages is None:
        test_messages = [
            "En une phrase : qu'est-ce que le Plenum représente pour toi dans ce projet ?",
            "Maintenant que tu vois ce que les autres ont dit — tu es d'accord ?"
        ]

    from agents.base_agent import Message

    # Historique simulé
    history = [Message(role="user", content=test_messages[0], agent="samuel")]

    # Phase 1
    response1 = await agent.ask(user_message=test_messages[0], history=[], peers_responses=None)
    if response1.success:
        print(f"✓ Réponse Phase 1 : {response1.content}\n")
    else:
        print(f"❌ Erreur Phase 1 : {response1.error}")
        return

    # Phase 2 avec peers si fourni
    if peers_responses is None:
        peers_responses = {
            "Gemini": "Le Plenum est un espace de convergence intellectuelle.",
            "DeepSeek": "Un protocole de délibération distribuée.",
            "ChatGPT": "Salon multi-agents avec historique partagé.",
        }

    history.append(Message(role="assistant", content=response1.content, agent=agent_name))
    response2 = await agent.ask(user_message=test_messages[1], history=history, peers_responses=peers_responses)
    if response2.success:
        print(f"✓ Réponse Phase 2 : {response2.content}\n")
    else:
        print(f"❌ Erreur Phase 2 : {response2.error}")
        return

    print(f"=== Test {agent_name} terminé ===\n")


def run_sync(agent_class, agent_name, test_messages=None, peers_responses=None):
    asyncio.run(run(agent_class, agent_name, test_messages, peers_responses))