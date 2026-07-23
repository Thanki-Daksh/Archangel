# features.md — 10 Features Beyond Current Vision

> These features go beyond the planned AI Outreach Agent, Dashboard, Analytics, Team Collaboration, Memory, Cloud Deployment, More Sources, Better Scoring, and Plugin Marketplace.
>
> Each feature is designed to make The Archangel genuinely unique — not just another lead tracker.

---

## 1. Lead Lifecycle Engine [SHIPPED]

**Status:** Completed (`archangel/lifecycle/`)

**What:** Track every lead from discovery → analysis → outreach → response → negotiation → conversion → payment → repeat.

---

## 2. Smart Deduplication & Merging [SHIPPED]

**Status:** Completed (`archangel/deduplication/`)

**What:** When the same lead appears from multiple sources (Reddit + GitHub + Discord), merge them into one lead with combined context.

---

## 3. Auto-Enrichment [SHIPPED]

**Status:** Completed (`archangel/enrichment/`)

**What:** When a lead is discovered, automatically pull additional context: company info, tech stack, team size, funding status, GitHub activity, website.

**Why:** A lead saying "Need Flutter dev for startup" tells you nothing about the startup. Enrichment turns a vague lead into an actionable opportunity.

**How:**
- New agent: `EnrichmentAgent` (runs after Intelligence agent)
- Sources for enrichment:
  - Company name → LinkedIn, Crunchbase, Glassdoor
  - GitHub org → repos, languages, activity
  - Website → tech stack (Wappalyzer-style), team page
  - Domain → WHOIS, DNS records
- Enrichment stored as metadata on the lead
- CLI: `archangel enrich <id>` — manually enrich a lead
- CLI: `archangel lead <id>` — shows enriched data

**Impact:** You know everything about a lead before you even respond.

---

## 4. Predictive Scoring with Feedback Loop [SHIPPED]

**Status:** Completed (`archangel/scoring/learning.py`)

**What:** Instead of static weights (confidence 40%, urgency 25%, etc.), use a model that learns from YOUR behavior — which leads you pursued, which you ignored, which converted.

---

## 5. Outreach Intelligence [SHIPPED]

**Status:** Completed (`archangel/outreach/`)

**What:** Analyze the lead's communication style, past projects, and tech preferences to generate personalized outreach messages that match their tone and needs.

---

## 6. Lead Relationship Graph & Obsidian Vault [SHIPPED]

**Status:** Completed (`archangel/vault/`)

**What:** Map connections between leads, companies, people, and technologies into an Obsidian Knowledge Vault with `.md` notes, bi-directional wikilinks (`[[Company:X]]`), Dataview blocks, and `.canvas` visual pipeline maps.

---

## 7. Browser Extension

**What:** Capture leads from any webpage with one click. See a job post on Twitter, LinkedIn, or a company careers page? Click the Archangel extension → it's analyzed, scored, and added to your pipeline.

---

## 8. Smart Notification Batching [SHIPPED]

**Status:** Completed (`archangel/notifications/batching.py`)

**What:** Don't ping for every lead. Batch low-priority leads into daily digests. Only alert immediately for high-score leads.

**Why:** If Archangel finds 20 leads a day and notifies for each one, you'll ignore them all. Smart batching means you only see what matters immediately, and review the rest when you have time.

**How:**
- New agent: `BatchingAgent` (runs before Notification agent)
- Rules (configurable in `configs/batching.yaml`):
  - Score > 80: notify immediately
  - Score 50-80: batch into hourly digest
  - Score < 50: batch into daily digest
- Digest format: summary table with top 5 leads, rest as count
- CLI: `archangel digest` — show current batched digest
- CLI: `archangel digest --send` — send digest now

**Impact:** No notification fatigue. You see what matters when it matters.

---

## 9. Lead Market Analysis [SHIPPED]

**Status:** Completed (`archangel/analytics/`)

**What:** Aggregate all discovered leads to show market trends: "Python automation leads are up 30% this month. Average budget: $5K. Best source: Reddit r/forhire."

---

## 10. Revenue Tracking & ROI [SHIPPED]

**Status:** Completed (`archangel/revenue/`)

**What:** Track which leads actually converted to income. Calculate ROI per source, per category, per time period. "Reddit gave me $15K this quarter. GitHub gave me $8K. Flutter leads converted at 40%."

---

## Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | Smart Deduplication | Medium | High — clean data |
| P0 | Auto-Enrichment | Medium | High — actionable context |
| P1 | Lead Lifecycle Engine | Large | High — full pipeline visibility |
| P1 | Predictive Scoring | Large | High — personalized accuracy |
| P2 | Outreach Intelligence | Medium | Medium — higher response rates |
| P2 | Smart Notification Batching | Small | Medium — less noise |
| P3 | Lead Market Analysis | Medium | Medium — trend insights |
| P3 | Revenue Tracking | Small | Medium — close the loop |
| P4 | Lead Relationship Graph | Large | Low-Medium — pattern discovery |
| P4 | Browser Extension | Large | Low-Medium — capture from anywhere |

---

## How These Fit Existing Architecture

All features plug into the existing event-driven architecture:

```
Collector → DeduplicationAgent → IntelligenceAgent → EnrichmentAgent →
ScoringAgent (with feedback loop) → LifecycleAgent → BatchingAgent →
NotificationAgent → RevenueTracking
```

No architectural rewrites needed. Each feature is a new agent or module that subscribes to events.

---

## What These Features Do NOT Replace

- Dashboard (still useful for visual browsing)
- Team Collaboration (still useful for shared leads)
- Plugin Marketplace (still useful for extending sources)
- Cloud Deployment (still useful for 24/7 operation)

These features COMPLEMENT the planned features, not replace them.

---

*"Opportunity is revealed to those who seek — and the seek better with better tools."*
