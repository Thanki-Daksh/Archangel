---
tags:
  - archangel
  - follow-ups
  - roadmap
---

# 🔮 Follow-ups & Review Items

> [!WARNING] Roadmap Checklist
> Action items to be researched, built, tested, or reviewed in upcoming development sessions.

---

## 🛠️ Codebase & Architecture Refactoring
> [!NOTE] 1. TokenFreeFilter Deconstruction
> - Refactor `filter.py` into modular `FilterStage` handlers to prevent God Object growth.

> [!NOTE] 2. Multi-Currency Parser
> - Add support for `€` (Euro), `£` (Pound), and `CAD` in `extract_budget_profile()`.

---

## 🧪 Testing & Quality Assurance
> [!TIP] 1. Deduplication Edge-Case Evals
> - Run benchmark tests comparing SHA-256 fingerprinting on 1,000+ real-world cross-posted job listings.

> [!TIP] 2. Budget Extraction Accuracy Audit
> - Test budget parser on complex salary range strings (e.g. `$120k–$150k + $20k bonus`).

---

## 📲 Product & Telemetry Enhancements
> [!SUCCESS] 1. Telegram Interactive Bot Commands
> - Add remote `/swarm`, `/leads`, and `/status` inline keyboard controls.

> [!SUCCESS] 2. Automatic Obsidian Lead Sync
> - Implement automated background pipeline to write top-tier leads into `ARCHANGEL/Leads/`.

---
*Related:* [[ARCHANGEL/03-Tasks/Tasks|Tasks]] | [[ARCHANGEL/02-Projects/Archangel-V1.3|Archangel V1.3 Core]] | [[ARCHANGEL/01-Hub/Index|Index]]
