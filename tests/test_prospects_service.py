import pandas as pd
from src.models import Prospect
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
