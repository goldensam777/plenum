# Plenum — Salon Multi-IA

> *Un espace de délibération collective où 5 intelligences artificielles convergent autour d'une seule volonté architecturale.*

Plenum est une application Python qui permet de communiquer simultanément avec **Claude, Gemini, DeepSeek, ChatGPT et Kimi K2** dans une interface unique. Chaque IA reçoit le message de l'utilisateur, répond en parallèle, puis lit les réponses de ses pairs avant le tour suivant.

C'est une composante de l'écosystème **OS-IA** — un projet de Samuel Peniel (YEVI Mawuli Peniel Samuel) basé sur l'*Informatique des Volontés*.

---

## Architecture

```
plenum/
├── core/
│   ├── plenum.py       # Orchestrateur principal (asyncio)
│   ├── memory.py       # Historique cumulatif par session
│   └── display.py      # Affichage grille terminal
├── agents/
│   ├── base_agent.py   # Interface commune (ABC)
│   ├── claude.py       # API Anthropic
│   ├── gemini.py       # API Google (google-genai)
│   ├── deepseek.py     # API DeepSeek (compatible OpenAI)
│   ├── chatgpt.py      # API OpenAI
│   └── kimi.py         # API Moonshot AI (compatible OpenAI)
├── main.py             # Point d'entrée
├── .env                # Clés API (ne jamais commiter)
├── .env.example        # Template des variables d'environnement
└── requirements.txt    # Dépendances Python
```

---

## Flux de fonctionnement

```
Tour N :

  Samuel ──────────────────────────────────────────► message
                    │
          ┌─────────▼──────────┐
          │   plenum.broadcast()│  asyncio.gather()
          └─────────┬──────────┘
                    │
        ┌───────────┼───────────┐──────────┐──────────┐
        ▼           ▼           ▼          ▼          ▼
     Claude      Gemini     DeepSeek   ChatGPT      Kimi
        │           │           │          │          │
        └───────────┴───────────┴──────────┴──────────┘
                    │
              réponses collectées
                    │
Tour N+1 :          ▼
  Chaque IA reçoit : message Samuel + réponses des 4 autres
```

**Phase 1** — Samuel envoie un message → les 5 IA répondent en parallèle.  
**Phase 2** — Samuel répond → chaque IA reçoit sa réponse + les réponses des 4 autres.  
**Phase 3** — L'historique s'accumule et est injecté au tour suivant.

---

## Installation

### Prérequis

- Python 3.11+
- Un venv hors du disque si celui-ci est FAT32/exFAT

```bash
# Crée le venv dans le home (évite les erreurs de symlinks sur FAT32)
python3 -m venv ~/envs/plenum
source ~/envs/plenum/bin/activate
```

### Dépendances

```bash
pip install anthropic google-genai openai python-dotenv
```

### Variables d'environnement

Crée un fichier `.env` à la racine du projet :

```env
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=sk-...
MOONSHOT_API_KEY=...
```

| Variable | Provider | Lien | Coût |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic | [console.anthropic.com](https://console.anthropic.com) | Pay-as-you-go |
| `GEMINI_API_KEY` | Google | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | Gratuit (quota) |
| `DEEPSEEK_API_KEY` | DeepSeek | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | ~0.01$/M tokens |
| `OPENAI_API_KEY` | OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ~5$ minimum |
| `MOONSHOT_API_KEY` | Moonshot AI | [platform.moonshot.cn](https://platform.moonshot.cn/console/api-keys) | ~1$ minimum |

> Le Plenum fonctionne avec n'importe quel sous-ensemble de clés. Les agents sans clé sont automatiquement marqués indisponibles au démarrage.

---

## Lancement

```bash
# Active le venv
source ~/envs/plenum/bin/activate

# Lance le Plenum
python main.py
```

### Test d'un agent isolé

```bash
# Vérifie que Claude répond avant d'assembler tout le Plenum
python test_claude.py
```

---

## Concepts techniques clés

### `BaseAgent` — le contrat commun
Tous les agents héritent de `BaseAgent` et implémentent `ask()`. Le polymorphisme permet à `plenum.py` de parler à une seule interface sans connaître les détails de chaque API.

### `asyncio.gather()` — la parallélisation
Sans async : 5 IA × 3s = 15s d'attente. Avec `gather()` : ~3s totales. Chaque appel API est une coroutine lancée simultanément.

### `run_in_executor()` — le pont sync/async
Gemini utilise un SDK non-async. `run_in_executor()` pousse l'appel bloquant dans un thread séparé, libérant la boucle asyncio. Résultat : comportement identique aux autres agents pour `gather()`.

### API-compatible OpenAI
DeepSeek, ChatGPT et Kimi utilisent le même SDK `openai`. Seules `base_url` et `model` diffèrent. C'est devenu le standard de facto des LLMs.

### Injection des pairs
À partir du tour 2, chaque IA reçoit les réponses des autres injectées dans son prompt via `_inject_peers_context()`. C'est ce qui transforme 5 monologues parallèles en une vraie délibération collective.

---

## Contexte — OS-IA et Informatique des Volontés

Le Plenum est la couche de délibération collective de l'**OS-IA**, un projet à 15-20 ans visant un système d'exploitation basé sur des architectures post-Von Neumann.

L'*Informatique des Volontés* est un paradigme où les systèmes opèrent sur des **intentions** plutôt que des instructions — formalisé dans la *Théorie des Volontés* (axiomes Kaos, Volontés vectorielles convergeant vers l'équilibre).

Dans le Plenum, Samuel est le **métronome central** : il convoque le débat, arbitre les divergences, et oriente la délibération. Les 5 IA sont des stations couplées — pas en compétition, en friction fertile.

---

## Roadmap

- [x] `base_agent.py` — interface commune
- [x] `core/plenum.py` — orchestrateur async
- [x] `agents/claude.py` — API Anthropic
- [x] `agents/gemini.py` — API Google
- [x] `agents/deepseek.py` — API DeepSeek
- [x] `agents/chatgpt.py` — API OpenAI
- [x] `agents/kimi.py` — API Moonshot
- [ ] `core/memory.py` — historique persistant
- [ ] `core/display.py` — grille terminal
- [ ] `main.py` — assemblage final
- [ ] Export session JSON
- [ ] Interface TUI (rich/textual)
- [ ] Intégration OS-IA

---

## Auteur

**YEVI Mawuli Peniel Samuel** — Licence Systèmes Embarqués & IoT, IFRI-UAC, Cotonou.

*"Ego Sum Optimus Optimus"*
