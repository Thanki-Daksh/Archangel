# features.md — 10 Features Beyond Current Vision

> These features go beyond the planned AI Outreach Agent, Dashboard, Analytics, Team Collaboration, Memory, Cloud Deployment, More Sources, Better Scoring, and Plugin Marketplace.
>
> Each feature is designed to make The Archangel genuinely unique — not just another lead tracker.

---

## 1. Lead Lifecycle Engine

**What:** Track every lead from discovery → analysis → outreach → response → negotiation → conversion → payment → repeat.

**Why:** Currently Archangel discovers and scores leads but loses track after notification. You have no visibility into what happened next. Did you outreach? Did they respond? Did it convert? How much did you earn?

**How:**
- New agent: `LifecycleAgent`
- States: `discovered` → `analyzed` → `contacted` → `responded` → `negotiating` → `won` → `paid` → `archived`
- CLI: `archangel leads` — list all leads with status
- CLI: `archangel lead <id>` — show full lifecycle of a lead
- CLI: `archangel lead <id> --status contacted` — update status
- Storage: new `lead_lifecycle` table

**Impact:** Turns Archangel from a notification tool into a full pipeline manager.

---

## 2. Smart Deduplication & Merging

**What:** When the same lead appears from multiple sources (Reddit + GitHub + Discord), merge them into one lead with combined context.

**Why:** Right now if someone posts "Need Python dev" on Reddit AND GitHub Issues, you get two notifications for the same job. Wastes time, clutters data.

**How:**
- New agent: `DeduplicationAgent` (runs after Intelligence agent)
- Fingerprinting: normalize title + description + keywords → hash
- Similarity scoring: if two leads have >85% similarity, merge
- Merged lead shows: "Found on: Reddit, GitHub, Discord" with links to each source
- CLI: `archangel merge <id1> <id2>` — manual merge
- CLI: `archangel duplicates` — list suspected duplicates

**Impact:** Clean data, no duplicate notifications, richer context per lead.

---

## 3. Auto-Enrichment

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

## 4. Predictive Scoring with Feedback Loop

**What:** Instead of static weights (confidence 40%, urgency 25%, etc.), use a model that learns from YOUR behavior — which leads you pursued, which you ignored, which converted.

**Why:** Static weights are a starting point. But your personal patterns are different from the defaults. Maybe you care more about budget than urgency. Maybe you prefer remote over on-site. The model learns YOUR preferences.

**How:**
- New agent: `LearningAgent`
- User provides feedback: `archangel lead <id> --score 8` or `archangel lead <id> --ignore`
- Feedback stored: lead features + user action
- Model: simple gradient boosting or logistic regression (scikit-learn)
- Retrained weekly (or on-demand: `archangel train`)
- Scoring weights become dynamic, personalized

**Impact:** Scores get more accurate over time. Leads you actually want rise to the top.

---

## 5. Outreach Intelligence

**What:** Analyze the lead's communication style, past projects, and tech preferences to generate personalized outreach messages that match their tone and needs.

**Why:** Generic outreach gets ignored. Personalized outreach gets responses. But personalization takes time. Archangel should do it automatically.

**How:**
- New agent: `OutreachAgent`
- Input: lead context + enrichment data + user's past outreach templates
- Output: 2-3 personalized message drafts
- Tone analysis: formal vs casual, technical vs business, English vs other languages
- Template library: user saves successful outreach patterns
- CLI: `archangel outreach <id>` — generate outreach drafts
- CLI: `archangel outreach <id> --send` — send via configured channel (Telegram, email, etc.)

**Impact:** Higher response rates, less time writing messages.

---

## 6. Lead Relationship Graph

**What:** Map connections between leads, companies, people, and technologies. "This lead worked with that company, who uses this tech stack, which appeared in 3 other leads."

**Why:** Individual leads are useful. But patterns across leads are powerful. You might notice: "Every Python automation lead from Reddit converts. Every Flutter lead from Discord doesn't." That's actionable intelligence.

**How:**
- New module: `archangel/graph/`
- Graph database (or SQLite with adjacency list)
- Entities: leads, companies, people, technologies, sources
- Relations: `worked_with`, `uses_tech`, `posted_on`, `similar_to`
- CLI: `archangel graph` — visualize relationships (text-based or export to Graphviz)
- CLI: `archangel graph --company <name>` — show all leads from a company
- CLI: `archangel graph --tech <name>` — show all leads using a technology

**Impact:** See patterns invisible at the individual lead level.

---

## 7. Browser Extension

**What:** Capture leads from any webpage with one click. See a job post on Twitter, LinkedIn, or a company careers page? Click the Archangel extension → it's analyzed, scored, and added to your pipeline.

**Why:** Not all leads come from Telegram/Reddit/Discord/GitHub. Some come from browsing. The extension bridges that gap.

**How:**
- Chrome/Firefox extension (manifest v3)
- Click extension icon → captures page content + URL
- Sends to Archangel API (local server or cloud)
- Intelligence agent analyzes and scores
- Lead appears in `archangel leads`
- CLI: `archangel serve` — start local API server for extension

**Impact:** Capture leads from anywhere on the internet, not just configured sources.

---

## 8. Smart Notification Batching

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

## 9. Lead Market Analysis

**What:** Aggregate all discovered leads to show market trends: "Python automation leads are up 30% this month. Average budget: $5K. Best source: Reddit r/forhire."

**Why:** Individual leads tell you what's available NOW. Market analysis tells you what's TRENDING. Helps you decide: should I learn Flutter? Is Rust becoming more popular? Are GitHub leads better than Reddit?

**How:**
- New module: `archangel/analytics/`
- Queries lead database for patterns
- Metrics:
  - Leads per source (Reddit vs GitHub vs Discord)
  - Leads per category (Python, Flutter, AI, Backend)
  - Average budget per category
  - Conversion rate per source
  - Trend over time (this week vs last week)
- CLI: `archangel analytics` — show market overview
- CLI: `archangel analytics --source reddit` — filter by source
- CLI: `archangel analytics --trend` — show trends over time

**Impact:** Data-driven decisions about what to learn, where to look, what to charge.

---

## 10. Revenue Tracking & ROI

**What:** Track which leads actually converted to income. Calculate ROI per source, per category, per time period. "Reddit gave me $15K this quarter. GitHub gave me $8K. Flutter leads converted at 40%."

**Why:** Discovering leads is useless if you don't know which ones actually pay. Revenue tracking closes the loop from opportunity → income.

**How:**
- New module: `archangel/revenue/`
- User logs conversions: `archangel revenue <lead_id> --amount 5000 --date 2026-07-14`
- Tracks: source, category, amount, date, time-to-close
- CLI: `archangel revenue` — total revenue summary
- CLI: `archangel revenue --source reddit` — revenue from Reddit leads
- CLI: `archangel revenue --roi` — ROI per source (revenue / time invested)
- CLI: `archangel revenue --export` — export to CSV for accounting

**Impact:** Know exactly where your money comes from. Optimize for high-ROI sources.

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
