# Archangel Master Tasks & Roadmap

## Completed Tasks
- [x] Hardcode default min lead quality thresholds (`min_score = 50.0`, `min_priority = MEDIUM`)
- [x] Implement multi-page `after` cursor pagination for Reddit search workers
- [x] Expand intent search query target matrix across 25 subreddits, RSS, GitHub, and X
- [x] Prevent main asyncio thread starvation and fix terminal `Runtime Elapsed` timer freeze via Telegram status update throttling
- [x] Fix lead discovery stoppage by adding HTTP 429/403 backoff propagation and RSS fallback streams
- [x] Verify full test suite passing (**97/97 tests passing**)

## Active Roadmap
- [ ] Monitor real-time lead ingestion velocity across expanded search streams
- [ ] Add web search API fallbacks (DuckDuckGo / Google CSE) for deep web buying signals
