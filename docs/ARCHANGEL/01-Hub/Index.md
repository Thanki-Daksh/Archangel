# Archangel Master Index & System Architecture

## Core Components
- **CLI Entrypoint**: [main.py](file:///d:/Daksh/Business/Archangel/archangel/cli/main.py) (`aa swarm`, `aa as`, `aa s`)
- **Swarm Manager**: [manager.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/manager.py)
- **Storage Pipeline**: [pipeline.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/pipeline.py) (LeadProcessor, BatchWriter, EnrichmentProcessor)
- **Target Registry**: [registry.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/registry.py) (Intent Expansion & 200+ parallel target streams)
- **Workers**: [reddit_worker.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/workers/reddit_worker.py) (RedditWorker with after-cursor pagination), RSSStreamWorker, ReachWorker
- **Filters & Scoring**: [filter.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/filter.py), [agent.py](file:///d:/Daksh/Business/Archangel/archangel/enrichment/agent.py)
- **Telegram Swarm Bot**: [telegram_bot.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/telegram_bot.py) (Action Cards, Dynamic Keyboards & Natural Language Swarm Launcher)
- **Personal Instructions Store**: [personal_instructions.py](file:///d:/Daksh/Business/Archangel/archangel/config/personal_instructions.py) (Custom User & Pitch Context)
- **Archangel Master Brain**: [Archangel-Brain.md](file:///d:/Daksh/Business/Archangel/docs/ARCHANGEL/01-Hub/Archangel-Brain.md) (Full Repository Architecture & Knowledge Grounding)
