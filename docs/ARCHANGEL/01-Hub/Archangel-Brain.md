# 🧠 Archangel Master Brain & System Architecture
> **Created**: 2026-07-29 | **Last Updated**: 2026-07-29 | **Version**: 2.1.0  
> **Hub Cross-Links**: [[Index]] | [[Tasks]] | [[Decisions]] | [[Daily-Log]]

---

## 1. System Identity & Mission
**Archangel** is an autonomous 1,000-worker client acquisition & lead discovery swarm built specifically for high-ticket software developers, agency owners, and AI engineers.

Its goal is scanning hundreds of thousands of posts across Reddit, RSS feeds, X (Twitter), GitHub issues, and Web Search in real time, filtering out noise in **5 microseconds**, and delivering copy-pasteable pitch hooks and direct DM links to Telegram in **under 10 seconds**.

---

## 2. Core Architecture Map

```mermaid
graph TD
    UserTelegram[Telegram Mobile App] <-->|Chat / Inline Buttons| TelegramBot[TelegramSwarmBot Daemon]
    TelegramBot <-->|Control Commands| SwarmManager[SwarmManager]
    
    subgraph Swarm Core Pipeline
        SwarmManager -->|Spawns 1,000 Tasks| SwarmPool[SwarmPool (1,000 Workers)]
        SwarmPool -->|330+ Streams| Reddit[Reddit API]
        SwarmPool -->|330+ Streams| RSS[RSS Stream]
        SwarmPool -->|330+ Streams| Reach[X / Search Vector]
        
        Reddit & RSS & Reach -->|Raw Posts| DiscQueue[Discovery Queue]
        DiscQueue -->|10,000 posts/sec| PreFilter[TokenFreeFilter (5-Microsecond Pre-Filter)]
        PreFilter -->|Qualified Leads| StorQueue[Storage Queue]
        StorQueue -->|Batch Flush| SQLite[SQLite WAL DB & Micro-Log Parts]
    end
    
    SQLite -->|Pushes High-Ticket Cards| TelegramBot
    TelegramBot -->|Appends Notes| Vault[Obsidian Vault (ARCHANGEL/08-Logs/)]
```

---

## 3. Component Deep Dive

### A. Swarm Concurrency (`archangel/agents/swarm/pool.py`)
- **Worker Allocation**: Spawns **1,000 active worker tasks** in memory across 330+ platform target streams.
- **Target Cycling**: Cycles targets so all 1,000 task slots stay 100% active (`Active Workers: 1000 / 1000`).

### B. Ultra-Fast Pre-Filter (`archangel/agents/swarm/filter.py`)
- **5-Microsecond Token-Free Filter**: Drops non-hiring posts in 5 microseconds using C-string tuple membership (`"hiring"`, `"looking for"`, `"need developer"`, `"saas"`, `"automation"`) before invoking regex or LLMs. **100% Token-Free ($0.00 cost)**.

### C. Pipeline & Storage (`archangel/agents/swarm/pipeline.py`)
- **Queue Throughput**: `LeadProcessor` burst-drains up to 200 posts per tick at **10,000+ posts/sec**.
- **Persisted Storage**: Writes qualified leads to SQLite WAL (`data/swarm_leads.db`) and rotating micro-logs (`data/leads_parts/swarm_leads_part_001.log`).

### D. Live Worker Telemetry Stream (`archangel/agents/swarm/logger.py`)
- **50 FPS Telemetry Stream**: `SwarmTelemetryLogger` outputs real-time `info : GET`, `info : OK 42ms`, `info : MATCH` lines to `data/swarm_activity.log`.
- **Tailing Command**: Executed via `aa logs -v` with infinite terminal scrolling.

### E. Interactive Telegram Bot & Natural Language Launcher (`archangel/agents/swarm/telegram_bot.py`)
- **Action Cards**: Inline buttons `[ 💬 DM Client ]`, `[ ⚡ Quick Pitch ]`, `[ 📓 Save to Obsidian ]`, `[ ❌ Dismiss ]`.
- **Command Parser**: Recognizes natural language prompts like *"spin an agent swarm up with 1000 workers, my price is 15k inr and intermediate level"* and instantly triggers `SwarmManager.run(max_workers=1000, allowed_tiers={'intermediate'}, min_budget='15kinr')`.
- **Personal Instructions Store**: Managed by `PersonalInstructionsStore` ([personal_instructions.py](file:///d:/Daksh/Business/Archangel/archangel/config/personal_instructions.py)) reading `data/user_instructions.json`.

---

## 4. Telegram Bot System Rules & Persona Grounding

> [!IMPORTANT]
> **CRITICAL SYSTEM RULE**: The bot MUST NEVER act like a generic AI/cloud consultant or ask "What's the use case?" / "What cloud platform?". The bot IS Archangel's live command center.
> 
> Grounding prompt: [system_prompt.py](file:///d:/Daksh/Business/Archangel/archangel/config/system_prompt.py) (`ARCHANGEL_BOT_SYSTEM_PROMPT`).
> 
> When the user asks to start/run the swarm, it must immediately execute the command and return:
> `⚔️ Archangel Agent Swarm Launched! 1,000 Workers Active | Min Budget: ₹15,000 | Tiers: INTERMEDIATE`
