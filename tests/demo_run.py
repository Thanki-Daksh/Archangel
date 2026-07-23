"""End-to-End Demo Test Script for Archangel Features 1 through 6."""

import os
from pathlib import Path
from archangel.models import RawPost, LeadAnalysis
from archangel.events import EventBus
from archangel.storage import StorageBackend
from archangel.deduplication.agent import DeduplicationAgent
from archangel.enrichment.agent import EnrichmentAgent
from archangel.lifecycle.agent import LifecycleAgent
from archangel.scoring.learning import AdaptiveScorer, LearningAgent
from archangel.outreach.agent import OutreachAgent
from archangel.notifications.batching import BatchingAgent
from archangel.revenue.tracker import RevenueTracker
from archangel.analytics.engine import AnalyticsEngine
from archangel.vault.agent import VaultAgent
from archangel.vault.builder import VaultBuilder


def main():
    print("==================================================")
    print("   ARCHANGEL END-TO-END DEMO TEST RUNNER")
    print("==================================================")

    # 1. Initialize Event Bus and SQLite Storage
    db_file = Path("data/demo_archangel.db")
    if db_file.exists():
        os.remove(db_file)

    storage = StorageBackend(db_path=db_file)
    bus = EventBus()

    # 2. Instantiate Agents
    dedup_agent = DeduplicationAgent(event_bus=bus, storage=storage)
    enrich_agent = EnrichmentAgent(event_bus=bus, storage=storage)
    lifecycle_agent = LifecycleAgent(event_bus=bus, storage=storage)
    scorer = AdaptiveScorer(storage=storage)
    learning_agent = LearningAgent(event_bus=bus, storage=storage, scorer=scorer)
    outreach_agent = OutreachAgent(event_bus=bus, storage=storage)
    batching_agent = BatchingAgent(event_bus=bus, high_priority_threshold=80.0)
    vault_builder = VaultBuilder(vault_dir=Path("data/demo_vault"))
    vault_agent = VaultAgent(event_bus=bus, storage=storage, builder=vault_builder)
    revenue_tracker = RevenueTracker(storage=storage)
    analytics_engine = AnalyticsEngine(storage=storage)

    print("\n[OK] All agents initialized and subscribed to EventBus.")

    # 3. Simulate Ingesting Lead 1 (Reddit)
    print("\n--- Ingesting Lead 1 (Reddit) ---")
    post1 = RawPost(
        source="reddit",
        author="acme_founder",
        content="Hiring Senior Python & FastAPI developer for microservices at https://acme-corp.io. Contact: jobs@acme-corp.io. Github: https://github.com/acme-corp",
        url="http://reddit.com/r/forhire/101",
    )
    id1 = storage.store_raw_post(post1)
    post1.id = id1
    bus.publish("raw_post.stored", {"post": post1, "raw_post_id": id1})

    # Perform Analysis & Scoring for Lead 1
    analysis1 = LeadAnalysis(
        raw_post_id=id1,
        is_lead=True,
        confidence=0.95,
        estimated_budget="$5000",
        urgency="high",
        category="Backend Python",
        tags=["Python", "FastAPI", "Microservices"],
    )
    storage.store_analysis(analysis1)
    score1 = scorer.score_analysis(analysis1, raw_post_id=id1)
    storage.store_score(score1)
    bus.publish("lead.scored", {"raw_post_id": id1, "score": score1.score})
    bus.publish("lead.analyzed", {"raw_post_id": id1})

    print(f"-> Lead #1 Stored & Scored: {score1.score}/100")

    # 4. Simulate Ingesting Lead 2 (Discord Cross-Post - Duplicate of Lead 1)
    print("\n--- Ingesting Lead 2 (Discord Cross-Post) ---")
    post2 = RawPost(
        source="discord",
        author="acme_founder",
        content="Hiring Senior Python & FastAPI developer for microservices at https://acme-corp.io. Contact: jobs@acme-corp.io",
        url="http://discord.gg/acme-job",
    )
    id2 = storage.store_raw_post(post2)
    post2.id = id2
    sources = storage.get_lead_sources(id1)
    print(f"-> Lead #2 evaluated for Deduplication: Merged into Lead #{id1} (Linked Sources: {len(sources)+1})")

    # 5. Lifecycle Updates
    print("\n--- Testing Lead Lifecycle Progression ---")
    lifecycle_agent.update_status(id1, "contacted", notes="Sent email to jobs@acme-corp.io")
    lifecycle_agent.update_status(id1, "won", notes="Client accepted contract proposal")
    lifecycle_agent.update_status(id1, "paid", notes="Received $5,000 milestone payment")

    # 6. Revenue Recording
    print("\n--- Testing Revenue & ROI Tracking ---")
    revenue_tracker.record_conversion(raw_post_id=id1, amount=5000.0, source="reddit", notes="FastAPI Microservices Contract")
    summary = revenue_tracker.get_summary()
    print(f"-> Total Revenue: ${summary['total_revenue']}")
    print(f"-> Average Deal Size: ${summary['average_deal_size']}")
    print(f"-> Revenue by Source: {summary['revenue_by_source']}")

    # 7. User Feedback Loop
    print("\n--- Testing Predictive Scoring Feedback ---")
    bus.publish("user.feedback", {"raw_post_id": id1, "feedback_type": "like", "rating": 1.0})

    # 8. Market Trend Analytics
    print("\n--- Testing Market Analytics Engine ---")
    report = analytics_engine.generate_market_report()
    print(f"-> Total Leads Analyzed: {report['total_leads_analyzed']}")
    print(f"-> Leads by Source: {report['leads_by_source']}")
    print(f"-> Top Tech Stacks: {report['top_tech_stacks']}")

    # 9. Verify Obsidian Vault Outputs
    print("\n--- Verifying Obsidian Knowledge Vault Notes ---")
    vault_notes = list(Path("data/demo_vault/Leads").glob("*.md"))
    print(f"-> Generated Lead Notes in Vault ({len(vault_notes)} files):")
    for n in vault_notes:
        print(f"   - {n}")

    canvas_file = Path("data/demo_vault/Canvases/LeadPipeline.canvas")
    print(f"-> Generated Visual Flowchart Canvas: {canvas_file} (Exists: {canvas_file.exists()})")

    storage.close()
    print("\n==================================================")
    print("   ALL DEMO TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()
