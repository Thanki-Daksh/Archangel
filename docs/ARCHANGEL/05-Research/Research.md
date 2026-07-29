---
tags:
  - archangel
  - research
  - architecture
---

# 🔬 Technical Research & System Architecture

> [!ABSTRACT] Research Highlights
> Summary of technical findings, pattern analysis, and architectural design principles established in the **Archangel** platform.

---

## 📐 Key Technical Findings

> [!TIP] 1. Budget Normalization (`BudgetNormalizer`)
> - **Problem:** Raw regex matching (`\$(\d+)`) breaks on hourly rates (`$50/hr`), salary ranges (`$120k-$160k`), and benefits (`401(k)`).
> - **Solution:** A structured `BudgetProfile` data model:
>   - `comp_type`: `"hourly"`, `"monthly"`, `"salary"`, `"fixed"`.
>   - `normalized_value`: Standardized dollar baseline (e.g. `$50/hr` = `$4,000` baseline for `--budget` comparison).
>   - Excludes pension terms (`401k`) and non-financial metrics (`24/7`, `100% remote`).

---

> [!IMPORTANT] 2. Content Fingerprinting (Cross-Platform Deduplication)
> - **Problem:** URL deduplication (`self._seen_urls`) fails when identical job postings are syndicated across different platforms (WeWorkRemotely vs. Reddit `r/forhire` vs. LinkedIn).
> - **Solution:** `compute_content_fingerprint()`:
>   - Normalizes title and first 15 words of text (stripping URLs, punctuation, and casing).
>   - Computes a 16-character SHA-256 hash.
>   - Suppresses duplicate CRM report generation while logging cross-posted sources.

---

> [!NOTE] 3. Obsidian Integration Architecture
> - **Obsidian Local REST API:** Connects via `http://127.0.0.1:27123/` (HTTP) or `https://127.0.0.1:27124/` (HTTPS).
> - **Hard-Linked Rules (`SKILL.md`):** Linking `C:\Users\Admin\.gemini\GEMINI.md` directly to `skills/engineering-mode/SKILL.md` ensures zero-lag, instant synchronization of system engineering rules.

---
*Related:* [[ARCHANGEL/06-Decisions/Decisions|Decisions]] | [[ARCHANGEL/02-Projects/Archangel-V1.3|Archangel V1.3 Core]] | [[ARCHANGEL/01-Hub/Index|Index]]
