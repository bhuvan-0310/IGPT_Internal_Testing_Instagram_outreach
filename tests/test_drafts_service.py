import pytest
from src.models import Campaign, Prospect
from src.services import drafts as drafts_service
from src.services import skills as skills_service


@pytest.fixture()
def campaign_and_prospect(db_session):
    campaign = Campaign(name="Test Campaign", product_service="Widgets", status="Draft")
    prospect = Prospect(username="alice", normalized_username="alice", status="New")
    db_session.add_all([campaign, prospect])
    db_session.flush()
    return campaign, prospect


def test_generate_variants_creates_persisted_drafts(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)

    monkeypatch.setattr(
        drafts_service, "generate_text",
        lambda system_prompt, user_prompt, model=None: "Hi there!\n---VARIANT---\nHello!\n---VARIANT---\nHey!",
    )

    created = drafts_service.generate_variants(
        db_session, prospect, campaign, profile,
        tone="friendly", language="English", length_preset="short", variant_count=3,
    )

    assert len(created) == 3
    assert {d.variant_label for d in created} == {"A", "B", "C"}
    assert all(d.status == "Draft" and d.is_current and d.version == 1 for d in created)
    assert [d.content for d in created] == ["Hi there!", "Hello!", "Hey!"]


def test_generate_variants_uses_only_selected_skills(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)
    selected_rule = profile.rules[0]
    captured = {}

    def fake_generate_text(system_prompt, user_prompt, model=None):
        captured["system_prompt"] = system_prompt
        return "Tailored message"

    monkeypatch.setattr(drafts_service, "generate_text", fake_generate_text)
    drafts_service.generate_variants(
        db_session, prospect, campaign, profile,
        tone="friendly", language="English", length_preset="short", variant_count=1,
        skill_rule_ids=[selected_rule.id],
    )

    assert selected_rule.name in captured["system_prompt"]
    assert profile.rules[1].name not in captured["system_prompt"]


def test_regenerate_variant_creates_new_version_and_retires_old(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "Original message")
    draft = drafts_service.generate_variants(db_session, prospect, campaign, profile, "friendly", "English", "short", 1)[0]

    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "Regenerated message")
    new_draft = drafts_service.regenerate_variant(db_session, draft)

    assert new_draft.version == 2
    assert new_draft.parent_id == draft.id
    assert new_draft.is_current is True
    assert draft.is_current is False
    assert new_draft.content == "Regenerated message"


def test_version_history_walks_parent_chain(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "v1")
    v1 = drafts_service.generate_variants(db_session, prospect, campaign, profile, "friendly", "English", "short", 1)[0]
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "v2")
    v2 = drafts_service.regenerate_variant(db_session, v1)
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "v3")
    v3 = drafts_service.regenerate_variant(db_session, v2)

    history = drafts_service.version_history(db_session, v3)
    assert [d.content for d in history] == ["v1", "v2", "v3"]


def test_set_status_validates_allowed_values(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "hello")
    draft = drafts_service.generate_variants(db_session, prospect, campaign, profile, "friendly", "English", "short", 1)[0]

    drafts_service.set_status(db_session, draft, "Approved")
    assert draft.status == "Approved"

    with pytest.raises(ValueError):
        drafts_service.set_status(db_session, draft, "Sent")  # approval must never imply sending


def test_save_edit_persists_manual_content_change(db_session, campaign_and_prospect, monkeypatch):
    campaign, prospect = campaign_and_prospect
    profile = skills_service.seed_default_profile(db_session)
    monkeypatch.setattr(drafts_service, "generate_text", lambda *a, **k: "auto content")
    draft = drafts_service.generate_variants(db_session, prospect, campaign, profile, "friendly", "English", "short", 1)[0]

    drafts_service.save_edit(db_session, draft, "manually edited content")
    assert draft.content == "manually edited content"
