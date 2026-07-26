import pytest
from archangel.models import RawPost
from archangel.storage import StorageBackend


@pytest.fixture
def tmp_storage(tmp_path):
    db_file = tmp_path / "test_archangel.db"
    storage = StorageBackend(db_path=db_file)
    yield storage
    storage.close()


def test_lead_sources_table_and_merge(tmp_storage):
    post1 = RawPost(source="reddit", content="Need Dev", url="http://reddit.com/1")
    post2 = RawPost(source="discord", content="Need Dev", url="http://discord.com/1")

    id1 = tmp_storage.store_raw_post(post1)
    id2 = tmp_storage.store_raw_post(post2)

    tmp_storage.link_lead_source(
        canonical_lead_id=id1,
        raw_post_id=id2,
        confidence=0.95,
        merge_reason="high similarity",
        tier_used="tier1",
    )

    sources = tmp_storage.get_lead_sources(canonical_lead_id=id1)
    assert len(sources) == 1
    assert sources[0]["raw_post_id"] == id2
    assert sources[0]["confidence"] == 0.95
    assert sources[0]["tier_used"] == "tier1"
