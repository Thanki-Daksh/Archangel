---
tags:
  - archangel
  - project
  - swarm-engine
status: active
priority: high
date: 2026-07-27
---

# 🛡️ Project Note: Archangel V1.5 Core Swarm Engine

> [!NOTE] Mission Statement
> Build a high-throughput, autonomous B2B lead generation engine capable of scanning thousands of multi-channel job postings per minute, filtering target buyers with zero token cost, and producing rich CRM Intelligence Reports.

---

## 🎯 Project Scope & Objectives

> [!IMPORTANT] Core Deliverables
> - [x] **Swarm Engine:** 300–1,000 parallel worker pool (`SwarmPool`).
> - [x] **0-Token Filter:** Keyword intent, freshness (`--fresh`), memory (`you.txt`), and budget rules.
> - [x] **Smart Budget Normalizer:** Hourly (`$50/hr`), monthly (`$5k/m`), salary (`$150k/y`), fixed budget parsing.
> - [x] **Content Hash Deduplication:** SHA-256 fingerprinting on first 15 normalized words to prevent duplicate cross-posts.
> - [x] **Log Persistence:** Append mode enabled by default (`reset_log=False`).

---

## 📊 Performance & System Metrics

> [!SUCCESS] Benchmark Highlights
> - **Scanning Throughput:** ~350 posts scanned per 5-second burst
> - **Filter Overhead:** `< 1ms` CPU regex evaluation
> - **Token Cost:** `$0.00` per filtered candidate
> - **Write Performance:** SQLite WAL Async Batch Writer (Avg flush: `31ms`)

---

## ⚖️ Architectural Decisions
- **Token-Free First:** Eliminate 95% of irrelevant posts via regex before calling LLM APIs.
- **Append Log Stream:** Ensure `swarm_leads.log` retains full historical lead data by default.
- **Normalized Hourly Baselines:** Convert hourly rates to an 80-hour project baseline (`$50/hr` = `$4,000`) for fair comparison against `--budget` thresholds.

---

## 🔮 Next Roadmap Milestones
- [x] **Filter Pipeline Modularization:** Split `TokenFreeFilter` into independent pipeline stages.
- [x] **Multi-Currency Parser:** Support `€` (Euro) and `£` (Pound).
- [ ] **Automatic Obsidian Exporter:** Auto-sync high-scoring leads into `ARCHANGEL/Leads/`.

---
*Related:* [[ARCHANGEL/03-Tasks/Tasks|Tasks]] | [[ARCHANGEL/05-Research/Research|Research]] | [[ARCHANGEL/06-Decisions/Decisions|Decisions]] | [[ARCHANGEL/01-Hub/Index|Index]]
