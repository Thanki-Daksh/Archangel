# Archangel Architectural Decisions (ADRs)

## ADR-001: Default Minimum Lead Quality Thresholds
- **Date**: 2026-07-28
- **Decision**: Hardcode `min_score = 50.0` (Sales Readiness >= 50.0) and `min_priority = "MEDIUM"` as default parameters in `SwarmManager` and CLI options.
- **Rationale**: Prevent low-intent posts (e.g. Sales Readiness 9.3 or Priority LOW) from cluttering `swarm_leads.log`.

## ADR-002: Async Event Loop Yielding
- **Date**: 2026-07-28
- **Decision**: Insert `if self.processed_count % 10 == 0: await asyncio.sleep(0)` in `LeadProcessor._consume_loop`.
- **Rationale**: Prevents 1,000 parallel worker tasks from starving the main asyncio thread and freezing terminal rendering.

## ADR-003: Multi-Key OAuth Token Pool & Explicit Terminal Screen Refreshing
- **Date**: 2026-07-28
- **Decision**:
  1. Implement `RedditTokenPool` to rotate up to 10+ Reddit API keys for 1,000 req/min zero-block authenticated ingestion.
  2. Set `auto_refresh=False` and invoke explicit `live.refresh()` calls on every tick in `SwarmManager.run()`.
- **Rationale**: Eliminates HTTP 403 rate-limit blocks while ensuring smooth, un-frozen `Runtime Elapsed` timer updates on Windows PowerShell.

## ADR-004: Interactive Telegram Action Cards & Dynamic AI Keyboard Synthesis
- **Date**: 2026-07-29
- **Decision**: Attach Inline Keyboard action cards (`[ 💬 DM Client ]`, `[ ⚡ Quick Pitch ]`, `[ 📓 Save to Obsidian ]`, `[ ❌ Dismiss ]`) to high-ticket Telegram lead push alerts, and enable dynamic AI button synthesis for interactive LLM turns.
- **Rationale**: Reduces lockscreen-to-DM outreach latency to under 10 seconds with 1-tap proposal generation.

## ADR-005: Natural Language Remote Swarm Control & Zero-Filler Grounding
- **Date**: 2026-07-29
- **Decision**:
  1. Build `parse_natural_language_swarm_cmd()` in `TelegramSwarmBot` to parse casual Telegram commands (`"spin an agent swarm up with 1000 workers, my price is 15k inr and intermediate level"`).
  2. Inject `ARCHANGEL_BOT_SYSTEM_PROMPT` into Telegram LLM engine to forbid generic corporate AI textbook advice.
- **Rationale**: Enables seamless 24/7 remote swarm control directly from Telegram mobile app.

## ADR-006: Personal Instructions Store (`user_instructions.json`)
- **Date**: 2026-07-29
- **Decision**: Persist developer bio, tech stack preferences, target budgets, and pitch style in `data/user_instructions.json`.
- **Rationale**: Automatically customizes generated pitches to match the developer's exact background.

## ADR-007: Live Worker Telemetry Stream (`aa logs -v`) & 0ms Live Rendering
- **Date**: 2026-07-29
- **Decision**:
  1. Add `SwarmTelemetryLogger` to output `info : GET`, `info : OK 42ms`, `info : MATCH` lines to `data/swarm_activity.log` at 50 FPS.
  2. Wrap `Live` context manager around SwarmManager startup flow.
- **Rationale**: Renders terminal UI instantly in 0ms while streaming worker activity logs continuously.
