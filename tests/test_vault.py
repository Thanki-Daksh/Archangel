import pytest
from pathlib import Path
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend
from archangel.vault.agent import VaultAgent
from archangel.vault.builder import VaultBuilder


def test_vault_builder_and_notes(tmp_path):
    vault_dir = tmp_path / "vault"
    builder = VaultBuilder(vault_dir=vault_dir)

    post = RawPost(
        source="github",
        author="octocat",
        content="Looking for Rust WebAssembly developer for AcmeCorp project",
        url="http://github.com/issues/100",
    )

    enrichment = {
        "company_name": "AcmeCorp",
        "domain": "acme.com",
        "detected_tech": ["Rust"],
        "social_links": [],
    }

    drafts = {"email": "Hi Octocat, I can help with Rust Wasm."}

    note_path = builder.build_lead_note(
        post=post,
        raw_post_id=102,
        status="contacted",
        enrichment=enrichment,
        drafts=drafts,
    )

    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "[[Company:AcmeCorp]]" in content
    assert "[[Tech:Rust]]" in content
    assert "```dataview" in content
    assert "id: 102" in content

    # Check Company note created
    company_note = vault_dir / "Companies" / "Company-AcmeCorp.md"
    assert company_note.exists()
    assert "[[Lead-102]]" in company_note.read_text(encoding="utf-8")

    # Check Canvas map generated
    canvas_path = vault_dir / "Canvases" / "LeadPipeline.canvas"
    assert canvas_path.exists()


def test_vault_agent_event_flow(tmp_path):
    vault_dir = tmp_path / "vault"
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_vault.db")
    builder = VaultBuilder(vault_dir=vault_dir)
    agent = VaultAgent(event_bus=bus, storage=storage, builder=builder)

    post = RawPost(source="reddit", author="startup_founder", content="Hiring Python engineer", url="http://reddit.com/job5")
    post_id = storage.store_raw_post(post)

    bus.publish("lead.enriched", {"raw_post_id": post_id, "enrichment": {"company_name": "TechInc", "detected_tech": ["Python"]}})

    note_file = vault_dir / "Leads" / f"Lead-{post_id}.md"
    assert note_file.exists()

    storage.close()
