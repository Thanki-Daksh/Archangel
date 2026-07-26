# ⚔️ Archangel V1.3

> Autonomous AI-powered Lead Intelligence Platform

Discover. Analyze. Enrich. Score. Close.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![SQLite](https://img.shields.io/badge/SQLite-WAL--Mode-003B57?style=for-the-badge&logo=sqlite)
![Gemini](https://img.shields.io/badge/Gemini_AI-2.5_Flash-8E75B2?style=for-the-badge&logo=google)
![AsyncIO](https://img.shields.io/badge/AsyncIO-Event_Bus-FFD43B?style=for-the-badge)
![AI Agents](https://img.shields.io/badge/AI_Agents-Autonomous-green?style=for-the-badge)

Archangel is an autonomous B2B lead intelligence platform built for software developers, agencies, and founders. It turns unstructured online discussions across Reddit, X (Twitter), GitHub, and RSS streams into qualified, enriched commercial leads.

Instead of spending hours manually searching forums or reading noise, Archangel uses AI Intent Expansion to generate 25+ buying intent search vectors, scans thousands of streams in parallel, enriches target company profiles, detects tech stacks, calculates revenue estimates, and generates personalized outreach pitches automatically.

Built on an asynchronous event-driven architecture with zero-token local filters, 128-thread worker pools, and persistent SQLite storage, Archangel delivers complete CRM Intelligence Reports straight to your console or Telegram.

---

## Preview

### ⚔️ Live Agent Swarm Dashboard
```text
┌────────────────────────── Archangel Swarm Monitor ──────────────────────────┐
│ Active Workers:              300 / 1000                                     │
│ Runtime Elapsed:             00h 02m 04s (Target: 24h 00m 00s)              │
│ Output Stream:               data\swarm_leads.log                           │
│ Token Cost:                  $0.00 (100% Token-Free Regex Engine)           │
│ Posts Scanned (This Run):    7,785                                          │
│ Qualified Leads (This Run):  5                                              │
│                                                                             │
│ Discovery Queue:             0 / 5,000                                      │
│ Storage Queue:               0 / 2,000                                      │
│ Batch Stats:                 Avg size: 1.7 | Avg flush: 1760.3ms            │
│ Writes:                      3 OK | 0 Failed                                │
│ Persisted (This Run):        5 leads                                        │
│ Backpressure:                0 warnings                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Clone the repository
```bash
git clone https://github.com/Thanki-Daksh/Archangel.git
```

### Enter the project
```bash
cd Archangel
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run setup
```bash
archangel setup
```

### Start the swarm
```bash
archangel swarm
```

---

## Quick Start

```bash
# 1. Run system diagnostics & verify dependencies
archangel doctor

# 2. Interactive setup wizard for profile & AI keys
archangel setup

# 3. Launch 24/7 autonomous agent swarm for a query
archangel swarm -l "website development"

# 4. View active persistent configuration
archangel config

# 5. Clear or inspect local lead logs
archangel leads log --wipe --db
```

- `archangel doctor` — Diagnostic tool for checking Python, internet, Telegram, Gemini API, SQLite, and scraper health.
- `archangel setup` — Interactive wizard for user profile, business details, AI keys, and search preferences.
- `archangel swarm` — Launches the 300+ worker parallel discovery and enrichment pipeline.
- `archangel leads` — Manages, filters, wipes, or views CRM intelligence lead reports.
- `archangel config` — Inspects persistent settings stored in `~/.archangel/`.

---

## What is Archangel?

Archangel is designed around one continuous operational pipeline:

```text
Internet
    ↓
Observe
    ↓
Understand
    ↓
Score
    ↓
Enrich
    ↓
Notify
```

### Why it exists
Most developers and agencies waste hundreds of hours manually browsing job boards, Reddit subreddits, and X feeds looking for contract work or client projects. Generic web scrapers only collect raw text and spam.

Archangel exists to bridge the gap between raw web noise and high-paying client contracts. It acts as an autonomous revenue engine that operates 24/7 in the background—discovering real buyers with active budgets, fingerprinting their tech stack, assessing their AI maturity, and giving you an exact pitch strategy to close the deal.

---

## Features

- ✅ **AI Intent Expansion Engine** — Generates 25+ buying intent search phrases from a single prompt via Gemini 2.5 Flash.
- ✅ **Autonomous Agent Swarm** — Scalable 300+ worker thread pool querying Reddit, X, GitHub, and RSS streams in parallel.
- ✅ **CRM Intelligence Reports** — Generates 14-section structured lead reports with actionable pitch angles.
- ✅ **Website Fingerprinting** — Automatically detects target frameworks (React, Laravel, Tailwind, Next.js, etc.).
- ✅ **AI Readiness Detector** — Analyzes whether target companies use OpenAI, Anthropic, Gemini, or LangChain.
- ✅ **Competition Analysis** — Measures outreach difficulty and market saturation.
- ✅ **Revenue Estimation** — Estimates commercial ARR ranges and buyer budget tiers.
- ✅ **Async Event Pipeline** — Decoupled pub/sub architecture using Python `asyncio` queues.
- ✅ **SQLite WAL Storage** — High-concurrency thread-safe database storage.
- ✅ **Telegram Notifications** — Instant real-time alerts sent to your mobile device.
- ✅ **Setup Wizard** — Interactive CLI setup storing settings under `~/.archangel/`.
- ✅ **Doctor Diagnostics** — Automated 8-pillar health check command (`archangel doctor`).

---

## Architecture

Archangel uses a decoupled, event-driven architecture where specialized agents communicate strictly via an internal `EventBus`:

```text
Workers (Reddit / X / GitHub / RSS)
                ↓
         Discovery Queue
                ↓
    Token-Free Qualification (0 Tokens)
                ↓
      SQLite Raw Post Storage
                ↓
   Enrichment Queue (9 Engines)
                ↓
  Canonical CRM Lead Generation
                ↓
   Logger & Telegram Notifications
```

---

## Project Structure

```text
archangel/
├── agents/        # Autonomous swarm workers, orchestrators, and token-free filters.
├── enrichment/    # Company profiling, tech fingerprinting, and pitch generation engines.
├── intent/        # Gemini AI Studio prompt expansion and heuristic buying-intent generators.
├── memory/        # User profile memory and you.txt rule enforcement.
├── storage/       # SQLite WAL mode storage backend and schema migrations.
├── config/        # Thread-safe persistent configuration manager for ~/.archangel/.
└── cli/           # Rich console commands, REPL interface, setup wizard, and doctor.
```

---

## Example Lead Report

```text
==================================================
=== ARCHANGEL CRM INTELLIGENCE LEAD #00001 ===
==================================================

[1. IDENTITY]
Lead ID: #00001
Lifecycle Stage: ANALYZED
Generated At: 2026-07-26 16:17:40 UTC

[2. COMPANY PROFILE]
Company Name: Weworkremotely
Target Domain: weworkremotely.com
Funding Stage: Bootstrapped / Early
Team Size: 1-10

[3. CONTACTS & SOCIALS]
Author Handle: rss_publisher
Primary Email: N/A
Social Handles: linkedin: datadog

[4. WEBSITE & INFRASTRUCTURE]
Domain: weworkremotely.com
Post URL: https://weworkremotely.com/remote-jobs/datadog-partner-manager-channels
Platform/Source: rss (Channel: rss)

[5. DETECTED TECH STACK]
Frameworks / Infrastructure: Laravel, Tailwind CSS, Bootstrap

[6. AI READINESS MATRIX]
Maturity Tier: None
Detected AI Tech: None

[7. WEBSITE HEALTH DIAGNOSTICS]
Health Score: 80/100
Response Speed (TTFB): 1708ms
SSL Status: HTTPS Enabled
SEO / Social Tags: Optimized

[8. PAIN TAXONOMY]
Identified Pain Categories: Sales, Marketing, Infrastructure, AI, DevOps

[9. OPPORTUNITY MAPPING]
Recommended Services: AI Chatbot, Full Stack SaaS MVP, Website Optimization

[10. COMMERCIAL & REVENUE ESTIMATE]
Estimated ARR Range: $0 - $100K
Buying Power Tier: Low

[11. OUTREACH COMPETITION]
Outreach Difficulty: Low
Platform Saturation: 20%

[12. LEAD SCORING]
Overall Score: 98.0 / 100.0
Priority Tier: HIGH
Filter Confidence: 0.98

[13. RECOMMENDED PITCH ANGLE]
Opening Angle: "Noticed Weworkremotely is built on AWS/Cloud."
Value Proposition: "We have deep expertise in AWS/Cloud and help teams scale rapidly."
Call to Action: "Would you be open to a quick 10-minute chat this week?"

[14. RAW POST MESSAGE]
"""
Datadog: Partner Manager - Channels
We are looking for an experienced Channel & Alliances sales professional...
"""

==================================================
END CRM LEAD REPORT #00001
==================================================
```

---

## Core Design Principles

1. **Intelligence over Collection** — Collecting data is easy; understanding data is valuable. Every post is analyzed and enriched before reaching the user.
2. **Modular Architecture** — Every component (storage, AI models, scrapers, notification channels) is fully decoupled and replaceable.
3. **One Agent = One Responsibility** — Single responsibility principle across collectors, scorers, enrichers, and loggers.
4. **Event-Driven Communication** — Subsystems never invoke each other directly; they publish and subscribe through an asynchronous `EventBus`.
5. **Token Efficiency** — 100% token-free local regex filtering eliminates LLM costs during initial post scanning.
6. **Graceful Degradation** — If AI API keys or external services go offline, deterministic heuristic engines take over without crashing.

---

## Roadmap

### V1.3 (Current Release)
- [x] AI Intent Expansion Engine (25+ queries default)
- [x] Interactive Setup Wizard (`archangel setup`)
- [x] Async Event-Driven Storage & Enrichment Pipeline
- [x] Full 14-Section CRM Intelligence Reports
- [x] System Diagnostics Doctor (`archangel doctor`)

### V1.4 & Future
- [ ] Live Deep Website Crawling
- [ ] Redis High-Performance Cache Layer
- [ ] Company Knowledge Graph & Entity Linking
- [ ] Web-based Visual Dashboard (Next.js)

---

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository (`https://github.com/Thanki-Daksh/Archangel.git`).
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.