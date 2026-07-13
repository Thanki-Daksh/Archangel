# ⚔ The Archangel

> *An autonomous, AI-powered lead intelligence platform built around specialized agents.*

---

# What is The Archangel?

The Archangel is the successor to Leads Bot.

It is **not** a Telegram scraper.

It is **not** another automation script.

It is an autonomous intelligence platform designed to continuously discover, analyze, rank, organize, and notify software development opportunities from multiple online sources.

The project's philosophy is simple:

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

Instead, The Archangel continuously watches configured sources, filters noise using AI, and delivers only high-value opportunities.

---

# Design Goals

The project is designed around six core principles.

## 1. Intelligence over Collection

Collecting data is easy.

Understanding data is valuable.

Every post should be analyzed before reaching the user.

---

## 2. Modular Architecture

Every component should be replaceable.

Storage can change.

Models can change.

Collectors can change.

Nothing should require rewriting the system.

---

## 3. One Agent = One Responsibility

Each agent exists for exactly one purpose.

Collectors never score.

Storage never analyzes.

Notifications never store.

This makes the system predictable and easy to extend.

---

## 4. Event Driven

Agents never call one another directly.

Instead they communicate through events.

```
Collector

↓

NewPostEvent

↓

Intelligence

↓

LeadScoredEvent

↓

Storage

↓

Notification
```

This allows components to be replaced independently.

---

## 5. CLI First

The CLI is the primary interface.

Future dashboards may exist.

The CLI remains the source of truth.

---

## 6. AI First

The documentation, architecture, and repository are designed so another AI can understand the project without guessing.

---

# Architecture

```
                    User
                      │
                      ▼
                 CLI Interface
                      │
                      ▼
                Commander Agent
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
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

Guardian monitors every running component.

---

# Agents

## Guardian

Supervisor.

Responsibilities

- Monitor health
- Restart crashed agents
- Detect stalled queues
- Runtime metrics

Never performs business logic.

---

## Commander

The orchestrator.

Responsibilities

- Read configuration
- Start agents
- Stop agents
- Route events
- Handle CLI commands

Everything begins here.

---

## Collector

Collects raw data.

Sources

- Telegram
- Reddit
- Discord
- GitHub
- RSS
- Future plugins

Forbidden

- AI analysis
- Storage
- Notifications

Output

```
RawPostEvent
```

---

## Intelligence

The AI brain.

Determines

- Is it a lead?
- Confidence
- Budget
- Urgency
- Category
- Duplicate detection
- Recommended action

Produces

```
LeadAnalysisEvent
```

---

## Scoring

Ranks opportunities.

Example

```
Budget

+

Urgency

+

Confidence

+

Recency

=

Lead Score
```

---

## Storage

Stores

- Raw posts
- AI analysis
- Scores
- Metadata
- History

No other agent writes directly to the database.

---

## Notification

Responsible only for messaging.

Future support

- Telegram
- Discord
- Email
- Desktop

---

## Export

Produces

- CSV
- JSON
- Markdown
- Excel

---

## Outreach (Future)

After approval

```
Lead

↓

Generate proposal

↓

Wait for approval

↓

Send
```

---

# Startup

```
archangel summon
```

Sequence

```
Display Banner

↓

Load Config

↓

Initialize Logger

↓

Load Plugins

↓

Initialize Storage

↓

Guardian

↓

Commander

↓

Collectors

↓

Intelligence

↓

Scoring

↓

Notification

↓

Export

↓

Mission Operational
```

Output

```
⚔️ Summoning The Archangel...

✓ Guardian awakened

✓ Commander online

✓ Storage initialized

✓ Collectors online

✓ Intelligence online

✓ Notifications online

Mission Status

OPERATIONAL
```

---

# Shutdown

```
archangel terminate
```

Sequence

```
Stop Collectors

↓

Flush AI Queue

↓

Save Storage

↓

Complete Notifications

↓

Export Pending Reports

↓

Unload Plugins

↓

Shutdown
```

Output

```
⚔️ The Archangel returns to the heavens.

Mission Complete.
```

---

# CLI

```
archangel summon
```

Start platform.

```
archangel terminate
```

Graceful shutdown.

```
archangel status
```

System information.

```
archangel watch
```

Live activity feed.

```
archangel scan
```

One-time scan.

```
archangel doctor
```

Diagnostics.

Checks

- Database
- Plugins
- Network
- Queues
- API Keys
- Storage

```
archangel config
```

Configuration.

```
archangel export
```

Export leads.

```
archangel logs
```

View logs.

```
archangel purge
```

Clean cache.

```
archangel update
```

Update plugins.

```
archangel version
```

Version.

---

# Repository

```
The_Archangel/

README.md

ARCHANGEL.md

archangel/
│
├── cli/
├── engine/
├── agents/
├── collectors/
├── analyzers/
├── scoring/
├── storage/
├── notifications/
├── export/
├── plugins/
├── utils/

configs/

logs/

data/

docs/

tests/
```

Every directory has one responsibility.

---

# Pipeline

```
Internet

↓

Collector

↓

Normalize

↓

Intelligence

↓

Score

↓

Storage

↓

Notification

↓

Export
```

Every stage is replaceable.

---

# Plugin Philosophy

Sources are plugins.

```
plugins/

telegram.py

reddit.py

discord.py

github.py
```

Drop in.

Restart.

Done.

---

# Future

- AI Outreach Agent
- Dashboard
- Analytics
- Team Collaboration
- Memory
- Cloud Deployment
- More Sources
- Better Scoring
- Plugin Marketplace

---

# Engineering Principles

- Event-driven architecture
- Modular components
- One responsibility per agent
- Replaceable modules
- AI-friendly documentation
- CLI-first workflow
- Minimal coupling
- Maximum observability

---

# The Vision

The Archangel is not intended to become "the best Telegram scraper."

It is intended to become a reusable intelligence platform capable of discovering opportunities anywhere on the internet.

If tomorrow a new platform appears, adding support should mean writing one plugin—not rewriting the engine.

The engine should remain stable while collectors, AI models, storage backends, notification channels, and export evolve independently.

Every design decision should move the project closer to that goal.

---

*"Opportunity is revealed to those who seek."*

**⚔️ The Archangel**