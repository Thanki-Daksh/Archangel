# Archangel Master Index & System Architecture Hub
> **Last Updated**: 2026-07-29 | **Status**: Active 1,000-Worker Engine | **Version**: 2.1.0

---

## 🧭 Vault Navigation & Master Notes
- **🧠 Master Brain Architecture**: [[Archangel-Brain]] — Full repository blueprint, swarm dataflow, and system prompt grounding.
- **📋 Master Tasks & Roadmap**: [[Tasks]] — All completed milestones and active roadmap tasks.
- **🏛️ Architecture Decisions Register**: [[Decisions]] — ADR-001 through ADR-007 documenting design choices.
- **📅 Daily Engineering Log**: [[Daily-Log]] — Daily activity logs, bug fixes, and verification command histories.

---

## 🛠️ Core Source Code Map

### CLI & Swarm Management
- **CLI Entrypoint**: [main.py](file:///d:/Daksh/Business/Archangel/archangel/cli/main.py) (`aa swarm`, `aa as`, `aa logs -v`, `aa config`)
- **Swarm Manager**: [manager.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/manager.py) (Concurrently manages 1,000 workers & instant 0ms Rich Live UI)
- **Swarm Worker Pool**: [pool.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/pool.py) (Cycles 1,000 worker tasks across 330+ streams)

### Data Ingestion & Pipeline
- **Storage Pipeline**: [pipeline.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/pipeline.py) (`LeadProcessor`, `BatchWriter`, `EnrichmentProcessor` - 10,000 posts/sec burst queue)
- **Target Registry**: [registry.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/registry.py) (330+ parallel target streams across Reddit, RSS, X, GitHub, Web Search)
- **Scraper Workers**: [reddit_worker.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/workers/reddit_worker.py), [rss_worker.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/workers/rss_worker.py), [reach_worker.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/workers/reach_worker.py)
- **Telemetry Logger**: [logger.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/logger.py) (`SwarmTelemetryLogger` streaming 50 FPS activity logs to `data/swarm_activity.log`)

### Filtering & AI Scoring
- **Token-Free Filter**: [filter.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/filter.py) (5-microsecond C-string fast-path keyword evaluation at $0.00 cost)
- **AI Enrichment Agent**: [agent.py](file:///d:/Daksh/Business/Archangel/archangel/enrichment/agent.py) (Generates CRM sales readiness scores and budget extractions)

### Interactive Telegram Bot & Custom Instructions
- **Telegram Swarm Bot**: [telegram_bot.py](file:///d:/Daksh/Business/Archangel/archangel/agents/swarm/telegram_bot.py) (Action Cards, Dynamic Keyboards & Natural Language Swarm Launcher)
- **Personal Instructions Store**: [personal_instructions.py](file:///d:/Daksh/Business/Archangel/archangel/config/personal_instructions.py) (Custom User & Pitch Context)
- **Archangel System Prompt**: [system_prompt.py](file:///d:/Daksh/Business/Archangel/archangel/config/system_prompt.py) (`ARCHANGEL_BOT_SYSTEM_PROMPT` grounding Telegram LLM)
