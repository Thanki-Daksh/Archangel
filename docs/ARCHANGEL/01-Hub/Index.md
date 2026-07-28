# Archangel Master Index & System Architecture

## Core Components
- **CLI Entrypoint**: [main.py](file:///d:/Daksh/Business/Archangel/archangel/cli/main.py) (`aa swarm`, `aa as`, `aa s`)
- **Swarm Manager**: [manager.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/manager.py)
- **Storage Pipeline**: [pipeline.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/pipeline.py) (LeadProcessor, BatchWriter, EnrichmentProcessor)
- **Target Registry**: [registry.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/registry.py) (Intent Expansion & 200+ parallel target streams)
- **Workers**: [reddit_worker.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/workers/reddit_worker.py) (RedditWorker with after-cursor pagination), RSSStreamWorker, ReachWorker
- **Filters & Scoring**: [filter.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/filter.py), [agent.py](file:///d:/Daksh/Business/Archangel/archangel/enrichment/agent.py)
