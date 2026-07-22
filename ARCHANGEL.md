# ARCHANGEL.md — AI Context Document

> The single source of truth for AI coding agents working on The Archangel.
>
> Read this file once. It contains everything needed to understand the project without re-reading every specification.

---

# Project Identity

**The Archangel** is an autonomous, AI-powered lead intelligence platform.

It continuously discovers, analyzes, ranks, organizes, and notifies software development opportunities from multiple online sources.

**Core philosophy:**

```
Internet
    ↓
Observe
    ↓
Understand
    ↓
Score
    ↓
Notify
```

The developer should never waste time manually searching for opportunities.

---

# What The Archangel Is NOT

- A Telegram scraper
- A Reddit bot
- A Discord monitor
- A keyword scanner
- Another automation script
- A CRM
- A project management platform
- A chat application

**The Archangel IS:**

- A lead intelligence platform
- An event-driven system
- An AI-assisted decision engine
- A modular developer tool
- A reusable intelligence platform

---

# Vision

The Archangel should become a reusable intelligence platform capable of discovering opportunities anywhere on the internet.

If a new platform appears tomorrow, adding support should mean writing one plugin — not rewriting the engine.

The engine remains stable. Everything around it evolves independently.

---

# Design Goals

| Goal | Meaning |
|------|---------|
| Modularity | Every component is replaceable |
| Predictability | One agent = one responsibility |
| Maintainability | Small, focused modules |
| Extensibility | Plugins add capabilities |
| Observability | Metrics, logs, health checks |
| Testability | Each component testable independently |
| AI-friendly | Documentation removes ambiguity |

---

# Architecture Overview

## Layer Model

```
CLI
 ↓
Engine
 ↓
Agents
 ↓
Subsystems
 ↓
Infrastructure
```

Each layer has a clearly defined responsibility.

## High-Level Design

```
                    User
                      │
                      ▼
                 CLI Interface
                      │
                      ▼
                Commander Agent
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
  Runtime Engine             Guardian Agent
         │
         ▼
     Event Bus
         │
 ┌───────┼────────────────────────────────────┐
 ▼       ▼         ▼         ▼        ▼       ▼
Collectors Analysis Scoring Storage Notification Export
```

Every component is independent. Every component communicates through events.

---

# Event System

## Communication Model

Agents never communicate directly. They communicate through the Event Bus.

**Correct:**

```
Collector
    ↓
RawPostEvent
    ↓
Intelligence
```

**Incorrect:**

```
Collector
    ↓
Intelligence.analyze()
```

Direct dependencies increase coupling. Events reduce coupling.

## Event Flow

```
Internet
    ↓
Collector
    ↓
RawPostEvent
    ↓
Intelligence
    ↓
LeadAnalysisEvent
    ↓
Scoring
    ↓
LeadScoredEvent
    ↓
Storage
    ↓
LeadStoredEvent
    ↓
Notification
    ↓
LeadDeliveredEvent
```

Each stage only understands the event it receives.

## Event Types

| Event | Producer | Consumer |
|-------|----------|----------|
| RawPostEvent | Collector | Intelligence |
| LeadAnalysisEvent | Intelligence | Scoring |
| LeadScoredEvent | Scoring | Storage |
| LeadStoredEvent | Storage | Notification |
| LeadDeliveredEvent | Notification | — |
| AgentStarted | Any Agent | Guardian |
| AgentStopped | Any Agent | Guardian |
| AgentHeartbeat | Any Agent | Guardian |
| AgentFailure | Any Agent | Guardian |
| HealthChanged | Guardian | — |
| RestartRequested | Guardian | Commander |
| CLICommand | CLI | Commander |
| ShutdownRequest | CLI | Commander |

---

# Agent System

## Agent Architecture

```
                   User
                     │
                     ▼
                CLI Interface
                     │
                     ▼
              Commander Agent
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 Collector      Intelligence     Storage
      │              │
      └──────┐  ┌────┘
             ▼  ▼
          Scoring
              │
              ▼
       Notification
              │
              ▼
            Export
```

Guardian supervises the entire system.

## Shared Lifecycle

Every agent follows:

```
Created → Initialized → Starting → Running → Stopping → Stopped
```

## Shared Rules

**Every agent must:**

- Own one responsibility
- Communicate through events
- Expose health information
- Support graceful shutdown
- Recover safely after restart

**Every agent must NOT:**

- Modify another agent's internal state
- Bypass the Event Bus
- Directly call unrelated agents
- Contain unrelated business logic

---

## Guardian Agent

**Purpose:** Supervisor. Monitors health of the platform.

**Responsibilities:**

- Monitor all agents
- Detect crashes
- Detect stalled queues
- Restart failed agents
- Publish health events
- Collect runtime metrics

**Health States:** Healthy | Degraded | Offline

**Consumes:** AgentStarted, AgentStopped, AgentHeartbeat, AgentFailure

**Produces:** HealthChanged, RestartRequested, SystemHealthy, SystemDegraded

**FORBIDDEN:** Never collects leads, performs AI analysis, stores data, or sends notifications.

---

## Commander Agent

**Purpose:** Orchestrator. Every startup and shutdown operation begins here.

**Responsibilities:**

- Start agents
- Stop agents
- Register agents
- Route commands
- Coordinate runtime
- Initialize subsystems

**Consumes:** CLICommand, ShutdownRequest, StartupRequest

**Produces:** AgentStart, AgentStop, RuntimeReady, RuntimeShutdown

**FORBIDDEN:** Never analyzes posts, scores leads, or stores data. Coordinates only.

---

## Collector Agent

**Purpose:** Gathers raw information. Nothing else.

**Responsibilities:**

- Receive data from collectors
- Normalize payloads
- Validate payloads
- Publish RawPost events

**Sources:** Telegram, Reddit, Discord, GitHub, RSS, future plugins

**Output:** RawPostEvent

**FORBIDDEN:** Never calls AI, scores leads, sends notifications, or writes databases.

---

## Intelligence Agent

**Purpose:** The reasoning engine. Converts raw information into structured understanding.

**Responsibilities:**

- Is this a lead?
- Confidence level
- Estimated budget
- Urgency
- Category
- Duplicate detection
- Recommended response
- Relevant tags

**Input:** RawPostEvent

**Output:** LeadAnalysisEvent

**FORBIDDEN:** Never stores information, sends notifications, or exports reports.

---

## Scoring Agent

**Purpose:** Ranks opportunities.

**Responsibilities:**

Generate numerical Lead Score from:

- Confidence
- Budget
- Urgency
- Keyword Match
- Source Quality
- Recency

**Output:** LeadScoredEvent

---

## Storage Agent

**Purpose:** Persist information.

**Responsibilities:**

Store: Raw posts, Analysis, Scores, Metadata, Runtime history

**Possible backends:** SQLite, JSON, PostgreSQL

**FORBIDDEN:** Never performs AI analysis, sends notifications, or exports data.

---

## Notification Agent

**Purpose:** Deliver completed opportunities.

**Responsibilities:**

Send notifications through: Telegram, Discord, Email, Desktop

**Input:** LeadStoredEvent

**Output:** LeadDeliveredEvent

**FORBIDDEN:** Never analyzes data, modifies leads, or stores information.

---

## Export Agent

**Purpose:** Generate external reports.

**Formats:** CSV, JSON, Markdown, Excel

**FORBIDDEN:** Never analyzes data, notifies users, or collects information.

---

## Outreach Agent (Future)

**Purpose:** Generate personalized outreach after lead approval.

**Workflow:**

```
Lead Approved → Generate proposal → Wait for approval → Send
```

Always requires explicit user approval before sending messages.

---

# Pipeline

## High-Level Flow

```
                  Internet
                      │
                      ▼
              Source Plugins
                      │
                      ▼
                Collector Agent
                      │
               RawPostEvent
                      │
                      ▼
           Intelligence Agent
                      │
            LeadAnalysisEvent
                      │
                      ▼
             Scoring Agent
                      │
             LeadScoredEvent
                      │
                      ▼
             Storage Agent
                      │
             LeadStoredEvent
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 Notification Agent        Export Agent
          │
          ▼
         User
```

## Pipeline Stages

| Stage | Agent | Input | Output |
|-------|-------|-------|--------|
| 1. Collection | Collector | Internet | RawPostEvent |
| 2. Intelligence | Intelligence | RawPostEvent | LeadAnalysisEvent |
| 3. Scoring | Scoring | LeadAnalysisEvent | LeadScoredEvent |
| 4. Storage | Storage | LeadScoredEvent | LeadStoredEvent |
| 5. Notification | Notification | LeadStoredEvent | LeadDeliveredEvent |
| 6. Export | Export | Storage | CSV/JSON/MD/Excel |

## Pipeline Rules

1. Collectors only collect
2. Intelligence only analyzes
3. Scoring only ranks
4. Storage only persists
5. Notifications only deliver
6. Exports only transform stored data
7. Every stage communicates through events
8. No stage should bypass another stage
9. Every event should have a well-defined schema
10. Every stage should be independently testable

## Raw Post Format

Every collector normalizes content into:

```json
{
  "source": "telegram",
  "channel": "Python Jobs",
  "author": "john_doe",
  "content": "...",
  "timestamp": "...",
  "url": "...",
  "metadata": {}
}
```

## AI Output Format

```json
{
  "lead": true,
  "confidence": 0.94,
  "estimated_budget": "$500-$1000",
  "urgency": "High",
  "category": "Automation",
  "tags": ["Python", "Telegram", "AI"]
}
```

---

# Plugin System

## Philosophy

The Engine is the operating system. Plugins are applications running on top of it.

Every external integration should be a plugin.

## Plugin Directory

All plugins live inside `archangel/plugins/`.

## Plugin Structure

```
plugins/
  telegram/
    plugin.py
    manifest.yaml
    config.py
    README.md
```

## Plugin Manifest

```yaml
name: Telegram
id: telegram
version: 1.0.0
author: The Archangel
type: collector
enabled: true
```

## Plugin Types

| Type | Purpose | Events |
|------|---------|--------|
| Collector | Collect information | Publishes RawPostEvent |
| Notification | Send messages | Subscribes to LeadStoredEvent |
| Export | Generate exports | Subscribes to stored leads |
| AI (Future) | AI providers | Replaces Intelligence backend |
| Storage (Future) | Persistence | Replaces Storage backend |

## Plugin Lifecycle

```
Discovered → Loaded → Validated → Initialized → Running → Stopping → Unloaded
```

## Plugin Rules

1. Every plugin owns one responsibility
2. Plugins communicate only through events
3. Plugins should never modify Engine internals
4. Plugins should be discoverable automatically
5. Plugins should be independently testable
6. Plugin failures should never stop the platform
7. Every plugin should include documentation and a manifest
8. Adding a plugin should not require changing existing plugins

---

# Configuration

## Configuration Hierarchy

```
Built-in Defaults
    ↓
Configuration Files
    ↓
Environment Variables
    ↓
CLI Flags
```

Each layer overrides the previous one. Highest priority wins.

## Configuration Directory

All user-editable configuration lives inside `configs/`.

## Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml` | Global runtime settings |
| `sources.yaml` | Where information is collected |
| `keywords.yaml` | What the user is looking for |
| `analysis.yaml` | AI behavior control |
| `scoring.yaml` | Opportunity ranking |
| `notifications.yaml` | Notification channels |
| `storage.yaml` | Persistence settings |

## Main Configuration

```yaml
runtime:
  debug: false
  log_level: INFO
  timezone: UTC

plugins:
  auto_discovery: true

guardian:
  enabled: true

engine:
  workers: auto
```

## Keywords Configuration

```yaml
include:
  - python
  - automation
  - ai
  - backend
  - flutter

exclude:
  - internship
  - unpaid
  - volunteer
```

## Analysis Configuration

```yaml
provider: gemini
model: gemini-3.5-flash
temperature: 0.2
confidence_threshold: 0.80
detect_duplicates: true
```

## Scoring Configuration

```yaml
weights:
  confidence: 40
  urgency: 25
  budget: 20
  keywords: 10
  recency: 5
```

## Environment Variables

Sensitive information belongs in environment variables:

```
OPENAI_API_KEY
GEMINI_API_KEY
TELEGRAM_API_ID
TELEGRAM_API_HASH
```

## Configuration Rules

1. Never hardcode user configuration
2. Sensitive values belong in environment variables
3. Each configuration file owns one responsibility
4. Invalid configuration must stop startup
5. Defaults should exist for every optional setting
6. CLI flags override configuration temporarily
7. Plugins should only read their own configuration
8. Configuration should be validated before any agent starts

---

# CLI

## Philosophy

The CLI is the primary interface. It should feel like a professional developer tool (Git, Docker, Ruff, UV).

## Command Reference

| Command | Purpose |
|---------|---------|
| `archangel summon` | Start the platform |
| `archangel` | Start the platform 
| `archangel terminate` | Graceful shutdown |
| `archangel status` | Display runtime information |
| `archangel watch` | Live event stream |
| `archangel scan` | One-time scan (exits after) |
| `archangel doctor` | Run diagnostics |
| `archangel config` | Inspect/edit configuration |
| `archangel export` | Export leads |
| `archangel logs` | View runtime logs |
| `archangel purge` | Clean cache |
| `archangel update` | Update plugins |
| `archangel version` | Display version |
| `archangel help` | Display commands |

## Default Behavior

Running `archangel` without a subcommand invokes `archangel summon`.

## Flags

```
--debug
--verbose
--config <path>
```

## Startup Sequence

```
Display Banner
    ↓
Load Configuration
    ↓
Validate Configuration
    ↓
Initialize Logger
    ↓
Initialize Event Bus
    ↓
Initialize Storage
    ↓
Load Plugins
    ↓
Spawn Guardian
    ↓
Spawn Commander
    ↓
Spawn Collector Agent
    ↓
Spawn Intelligence Agent
    ↓
Spawn Scoring Agent
    ↓
Spawn Notification Agent
    ↓
Run Health Check
    ↓
Mission Operational
```

## Shutdown Sequence

```
Freeze Guardian
    ↓
Stop accepting new work
    ↓
Stop Collectors
    ↓
Flush Event Queue
    ↓
Complete AI Analysis
    ↓
Save Database
    ↓
Complete Notifications
    ↓
Finish Exports
    ↓
Unload Plugins
    ↓
Close Logger
    ↓
Shutdown
```

No data should be lost during shutdown.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General Error |
| 2 | Configuration Error |
| 3 | Plugin Error |
| 4 | Storage Error |
| 5 | Network Error |
| 6 | Runtime Failure |

## Output Rules

- Display active progress messages while work is being performed
- Only show completed indicators after operations finish
- Progress builds confidence
- Errors should be actionable (what failed, why, how to fix)

## CLI Rules

The CLI must never:

- Contain business logic
- Directly call agents
- Modify engine internals

---

# Repository Structure

## Root Layout

```
The_Archangel/
├── archangel/          # Main application source
├── configs/            # User configuration files
├── data/               # Runtime databases and exports
├── docs/               # Project specifications
├── logs/               # Runtime logs
├── tests/              # Automated testing
├── README.md           # Public overview
├── ARCHANGEL.md        # AI context document (this file)
├── pyproject.toml      # Python project configuration
├── uv.lock             # Dependency lockfile
├── .gitignore          # Ignored files
└── LICENSE             # Project license
```

## Source Layout

```
archangel/
├── cli/            # Command-line interface
├── engine/         # Runtime engine
├── agents/         # Autonomous agents
├── collectors/     # Source-specific collectors
├── analysis/       # AI reasoning logic
├── scoring/        # Lead quality calculation
├── storage/        # Data persistence
├── notifications/  # Message delivery
├── export/         # Report generation
├── plugins/        # Dynamically loaded plugins
├── config/         # Internal configuration models
├── events/         # Event Bus contracts
├── utils/          # Shared utilities
└── assets/         # Static resources
```

## Directory Responsibilities

| Directory | Owns |
|-----------|------|
| `cli/` | Command parsing, output display |
| `engine/` | Startup, shutdown, lifecycle, event routing |
| `agents/` | Autonomous decision makers |
| `collectors/` | Source-specific data retrieval |
| `analysis/` | AI reasoning, prompt construction |
| `scoring/` | Score calculation, ranking |
| `storage/` | Database, persistence, migrations |
| `notifications/` | Message delivery |
| `export/` | Report generation (CSV, JSON, MD, Excel) |
| `plugins/` | External integrations |
| `config/` | Schema validation, configuration loading |
| `events/` | Event type definitions |
| `utils/` | Logging, helpers, constants |
| `assets/` | Banners, templates, prompts |

## Repository Rules

1. Every file must have an obvious home
2. Avoid miscellaneous directories
3. Every module owns its own responsibility
4. No module should assume ownership of another module's responsibilities
5. Application logic never lives in the repository root

---

# Runtime Lifecycle

## States

```
Stopped → Starting → Running → Stopping → Stopped
```

Only the Engine controls state transitions.

## Startup Order

```
Guardian → Commander → Collector → Intelligence → Scoring → Storage → Notification → Export
```

Platform is operational only after every critical agent reports READY.

## Shutdown Order

```
Stop Collectors → Finish AI Queue → Finish Scoring → Flush Storage → Finish Notifications → Finish Exports → Shutdown
```

Every shutdown should preserve pending work.

## Error Handling

Every component fails independently.

Example: Discord Collector crashes → Guardian detects → Collector restarted → System continues running.

The entire platform should never terminate because one collector failed.

---

# Engineering Rules

These rules should never be violated:

| # | Rule |
|---|------|
| 1 | One component owns one responsibility |
| 2 | Communication happens through events |
| 3 | Collectors never perform AI analysis |
| 4 | AI never writes directly to storage |
| 5 | Storage never performs notifications |
| 6 | The CLI never performs business logic |
| 7 | The Engine coordinates — it does not own business logic |
| 8 | Plugins should extend functionality without engine modifications |

---

# Terminology

| Term | Meaning |
|------|---------|
| Agent | Autonomous worker with one responsibility |
| Engine | Runtime coordinator |
| Event Bus | Communication backbone |
| Plugin | External integration |
| Collector | Data source integration |
| Intelligence | AI reasoning layer |
| Scoring | Opportunity ranking system |
| Guardian | Health supervisor |
| Commander | Startup/shutdown orchestrator |
| RawPost | Unprocessed collected data |
| Lead | Analyzed, scored opportunity |
| Pipeline | Data flow from internet to user |
| Summon | Start the platform |
| Terminate | Gracefully stop the platform |
| Mission | A running session of The Archangel |

---

# AI Guidelines

## For Future Coding Agents

1. **Read this file first.** It contains the complete project context.

2. **Understand the architecture before writing code.** Every component has strict boundaries.

3. **Never violate agent boundaries.** If an agent's forbidden list includes an action, do not add that action.

4. **Communicate through events.** Never add direct calls between agents.

5. **Follow the repository structure.** Every directory has one purpose.

6. **Update documentation when architecture changes.** Keep ARCHANGEL.md current.

7. **Test independently.** Each component should be testable in isolation.

8. **Respect the pipeline.** Data flows: Collection → Intelligence → Scoring → Storage → Notification → Export.

9. **Configuration is external.** Never hardcode user settings.

10. **Plugins extend. They do not modify.** Adding a plugin should not change the Engine.

## Decision Framework

When implementing a new feature:

- Which agent owns this responsibility?
- What events does it consume?
- What events does it produce?
- Does it violate any forbidden actions?
- Does it fit the repository structure?
- Can it be tested independently?

If any answer is unclear, reconsider the approach.

---

# Current Status

## Implementation Phase: Greenfield

**This project is in the pre-implementation planning phase.**

- All architecture is defined across 10 specification documents
- All source directories exist but contain no code
- No configuration files exist yet
- No tests exist yet
- No dependencies are installed

**What exists:**

- Complete architectural specifications
- Agent definitions with responsibilities and forbidden actions
- Pipeline design with event flow
- Plugin system design
- Configuration system design
- CLI command reference
- Repository structure

**What needs to be built:**

Everything. Start with the Engine, then agents, then pipeline stages.

---

# Future Direction

- AI Outreach Agent
- Dashboard
- Analytics
- Team Collaboration
- Memory Agent
- Cloud Deployment
- More Sources
- Better Scoring
- Plugin Marketplace

These should be implemented as extensions, not architectural rewrites.

---

# Cross-References

| Topic | Primary Document |
|-------|-----------------|
| Vision | `docs/00-Vision.md` |
| Architecture | `docs/01-Architecture.md` |
| Agents | `docs/02-Agents.md` |
| CLI | `docs/03-CLI.md` |
| Repository | `docs/04-Repository.md` |
| Pipeline | `docs/05-Pipeline.md` |
| Plugins | `docs/06-Plugin-System.md` |
| Configuration | `docs/07-Configuration.md` |
| Roadmap | `docs/08-Roadmap.md` |

---

*"Opportunity is revealed to those who seek."*

⚔️ The Archangel
