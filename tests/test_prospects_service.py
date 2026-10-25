import pandas as pd
import pytest
from src.models import Campaign, Prospect
from src.services import prospects as prospects_service


def test_guess_username_column_matches_common_variants():
    assert prospects_service.guess_username_column(["ownerUsername", "bio"]) == "ownerUsername"
    assert prospects_service.guess_username_column(["Handle", "Name"]) == "Handle"
    assert prospects_service.guess_username_column(["foo", "bar"]) is None


def test_import_dataframe_adds_rows_and_defaults_profile_url(db_session):
    df = pd.DataFrame([
        {"username": "alice", "bio": "Runner"},
        {"username": "bob", "bio": "Baker"},
    ])
    result = prospects_service.import_dataframe(db_session, df, username_col="username", bio_col="bio")
    assert result.imported == 2
    assert result.skipped == 0
    prospects = db_session.query(Prospect).order_by(Prospect.username).all()
    assert [p.username for p in prospects] == ["alice", "bob"]
    assert prospects[0].profile_url == "https://www.instagram.com/alice/"
    assert prospects[0].bio == "Runner"


def test_import_dataframe_skips_blank_usernames(db_session):
    df = pd.DataFrame([{"username": ""}, {"username": "   "}, {"username": "valid_user"}])
    result = prospects_service.import_dataframe(db_session, df, username_col="username")
    assert result.imported == 1
    assert result.skipped == 2


def test_import_dataframe_deduplicates_within_file_and_against_existing(db_session):
    db_session.add(Prospect(username="Carol", normalized_username="carol", status="New"))
    db_session.flush()

    df = pd.DataFrame([
        {"username": "carol"},    # duplicate of existing (case-insensitive)
        {"username": "dave"},
        {"username": "Dave"},     # duplicate within this file
    ])
    result = prospects_service.import_dataframe(db_session, df, username_col="username")
    assert result.imported == 1  # only "dave"
    assert result.skipped == 2
    usernames = {p.normalized_username for p in db_session.query(Prospect).all()}
    assert usernames == {"carol", "dave"}


def test_import_dataframe_strips_leading_at_sign(db_session):
    df = pd.DataFrame([{"username": "@eve"}])
    prospects_service.import_dataframe(db_session, df, username_col="username")
    prospect = db_session.query(Prospect).filter_by(normalized_username="eve").one()
    assert prospect.username == "eve"


def test_assign_campaign_updates_only_selected_prospects(db_session):
    campaign = Campaign(name="AI course", status="Active")
    selected = Prospect(username="alice", normalized_username="alice", status="New")
    unselected = Prospect(username="bob", normalized_username="bob", status="New")
    db_session.add_all([campaign, selected, unselected])
    db_session.flush()

    updated = prospects_service.assign_campaign(db_session, [selected.id], campaign.id)

    assert updated == 1
    assert selected.campaign_id == campaign.id
    assert unselected.campaign_id is None


def test_assign_campaign_rejects_unknown_campaign(db_session):
    prospect = Prospect(username="alice", normalized_username="alice", status="New")
    db_session.add(prospect)
    db_session.flush()

    with pytest.raises(ValueError, match="does not exist"):
        prospects_service.assign_campaign(db_session, [prospect.id], campaign_id=999)
