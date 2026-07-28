# Archangel Architectural Decisions (ADRs)

## ADR-001: Default Minimum Lead Quality Thresholds
- **Date**: 2026-07-28
- **Decision**: Hardcode `min_score = 50.0` (Sales Readiness >= 50.0) and `min_priority = "MEDIUM"` as default parameters in `SwarmManager` and CLI options.
- **Rationale**: Prevent low-intent posts (e.g. Sales Readiness 9.3 or Priority LOW) from cluttering `swarm_leads.log`.

## ADR-002: Async Event Loop Yielding
- **Date**: 2026-07-28
- **Decision**: Insert `if self.processed_count % 10 == 0: await asyncio.sleep(0)` in `LeadProcessor._consume_loop`.
- **Rationale**: Prevents 1,000 parallel worker tasks from starving the main asyncio thread and freezing terminal rendering.
