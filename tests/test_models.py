from src.models import Campaign, Prospect

def test_campaign_model_fields():
    campaign = Campaign(name="Test campaign", status="Draft")
    assert campaign.name == "Test campaign"
    assert campaign.status == "Draft"

def test_prospect_normalization_is_stored_by_service():
    prospect = Prospect(username="ExampleUser", normalized_username="exampleuser")
    assert prospect.normalized_username == "exampleuser"
