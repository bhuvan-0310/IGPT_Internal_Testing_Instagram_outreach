from src.models import DEFAULT_CAMPAIGN_ACTIONS, Campaign, Prospect

def test_campaign_model_fields():
    campaign = Campaign(name="Test campaign", status="Draft")
    assert campaign.name == "Test campaign"
    assert campaign.status == "Draft"
    assert campaign.campaign_actions is None


def test_campaign_actions_default_to_direct_message(db_session):
    campaign = Campaign(name="Default action campaign")
    db_session.add(campaign)
    db_session.flush()
    assert campaign.campaign_actions == DEFAULT_CAMPAIGN_ACTIONS


def test_campaign_actions_are_persisted(db_session):
    campaign = Campaign(
        name="Multi-action campaign",
        campaign_actions=["follow_request", "message", "pdf", "voice"],
    )
    db_session.add(campaign)
    db_session.flush()
    db_session.expire_all()

    loaded = db_session.get(Campaign, campaign.id)
    assert loaded.campaign_actions == ["follow_request", "message", "pdf", "voice"]

def test_prospect_normalization_is_stored_by_service():
    prospect = Prospect(username="ExampleUser", normalized_username="exampleuser")
    assert prospect.normalized_username == "exampleuser"
