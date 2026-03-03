# CLAUDE.md — Instructions pour Claude Code

## Contexte du projet

Tu travailles sur **Plenum**, un salon multi-IA en Python développé par Samuel Peniel (17 ans, L1 SE & IoT, IFRI-UAC, Cotonou). Plenum permet de communiquer simultanément avec 5 IA (Claude, Gemini, DeepSeek, ChatGPT, Kimi K2) dans une interface terminal unique.

Ce projet est une composante de l'**OS-IA** — un écosystème informatique basé sur l'*Informatique des Volontés*, un paradigme où les systèmes opèrent sur des intentions plutôt que des instructions.

---

## Stack technique

- **Python 3.11+** avec `asyncio` pour la parallélisation
- **SDKs** : `anthropic`, `google-genai`, `openai` (utilisé aussi pour DeepSeek et Kimi)
- **Venv** : `~/envs/plenum` (hors du disque projet — FAT32 ne supporte pas les symlinks)
- **Clés API** : dans `.env` à la racine (ne jamais commiter)

---

## Architecture

```
plenum/
├── core/
│   ├── plenum.py       # Orchestrateur principal
│   ├── memory.py       # Historique cumulatif
│   └── display.py      # Affichage grille terminal
├── agents/
│   ├── base_agent.py   # ABC — interface commune à tous les agents
│   ├── claude.py       # AsyncAnthropic
│   ├── gemini.py       # google-genai + run_in_executor
│   ├── deepseek.py     # AsyncOpenAI + base_url DeepSeek
│   ├── chatgpt.py      # AsyncOpenAI natif
│   └── kimi.py         # AsyncOpenAI + base_url Moonshot
├── main.py
└── test_claude.py
```

---

## Conventions de code

### Structure d'un agent
Tout agent hérite de `BaseAgent` et implémente **obligatoirement** :
- `async def check_connection(self) -> bool`
- `async def ask(self, user_message, history, peers_responses) -> AgentResponse`

Utilise `_format_history()` et `_inject_peers_context()` hérités de `BaseAgent`.

### Retours
Toujours retourner un `AgentResponse` — jamais lever d'exception dans `ask()`.  
En cas d'erreur : `AgentResponse(success=False, error=str(e), ...)`.

### Async
- Tout appel réseau doit être `await`
- Les SDKs non-async (ex: google-genai) → `await loop.run_in_executor(None, lambda: ...)`
- Ne jamais utiliser `time.sleep()` → `await asyncio.sleep()`

### Nommage
- Classes : `PascalCase` — `ClaudeAgent`, `GeminiAgent`
- Méthodes privées : préfixe `_` — `_format_history()`, `_inject_peers_context()`
- Variables d'env : `SCREAMING_SNAKE_CASE` — `ANTHROPIC_API_KEY`

---

## Fichiers à compléter

### `core/memory.py`
Gère la persistence de l'historique entre les sessions (export/import JSON).  
Doit s'interfacer avec la liste `history: list[Message]` de `plenum.py`.

### `core/display.py`
Affichage terminal en grille 5 colonnes des réponses des agents.  
Utilise `rich` si disponible, sinon fallback texte brut.  
Doit afficher : nom agent, latence en ms, contenu tronqué/scrollable, statut (✓/✗).

### `main.py`
Point d'entrée. Doit :
1. Charger les clés depuis `.env` avec `python-dotenv`
2. Instancier les 5 agents
3. Créer le `Plenum` et appeler `initialize()`
4. Boucle principale : input Samuel → `broadcast()` → `display()`
5. Commandes spéciales : `/quit`, `/reset`, `/export`, `/status`

---

## Comportements attendus

- Si une clé API est absente → l'agent est ignoré silencieusement, le reste continue
- Si un agent timeout (>30s) → `AgentResponse(success=False, error="Timeout")`, on continue
- L'historique s'accumule sur toute la session — chaque agent reçoit les 10 derniers tours
- Les réponses des pairs sont injectées dans le message utilisateur du tour suivant

---

## Ce qu'il ne faut pas faire

- Ne pas modifier `base_agent.py` sans vérifier l'impact sur les 5 agents
- Ne pas commiter `.env`
- Ne pas utiliser de variables globales mutables dans les agents
- Ne pas faire d'appels API synchrones dans une coroutine sans `run_in_executor`
- Ne pas utiliser `print()` dans les agents — les erreurs vont dans `AgentResponse.error`