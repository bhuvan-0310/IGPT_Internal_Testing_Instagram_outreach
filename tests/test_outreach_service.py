from datetime import datetime, timedelta, timezone
import pytest
from src.models import AuditEvent, Campaign, Prospect
from src.services import outreach as outreach_service
from src.services import followups as followups_service


@pytest.fixture()
def campaign_and_prospect(db_session):
    campaign = Campaign(name="Outreach Test Campaign", status="Active")
    prospect = Prospect(username="bob", normalized_username="bob", status="Approved")
    db_session.add_all([campaign, prospect])
    db_session.flush()
    return campaign, prospect


def test_record_event_updates_prospect_status_and_writes_audit(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    assert prospect.campaign_id is None
    outreach_service.record_event(
        db_session, prospect, campaign.id, contact_method="Instagram DM", response_status="No response",
    )
    assert prospect.status == "Contacted"
    assert prospect.campaign_id == campaign.id
    audit = db_session.query(AuditEvent).filter_by(entity_type="prospect", entity_id=prospect.id).all()
    assert len(audit) == 1
    assert "outreach" in audit[0].event_type


def test_record_event_converted_sets_converted_status(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    outreach_service.record_event(db_session, prospect, campaign.id, contact_method="Instagram DM", response_status="Converted")
    assert prospect.status == "Converted"


def test_completed_prospect_ids_returns_only_matching_campaign_actions(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    other_campaign = Campaign(name="Other campaign", status="Active")
    other_prospect = Prospect(username="alice", normalized_username="alice", status="New")
    db_session.add_all([other_campaign, other_prospect])
    db_session.flush()

    outreach_service.record_event(
        db_session, prospect, campaign.id,
        contact_method="Instagram follow request", response_status="No response",
    )
    outreach_service.record_event(
        db_session, other_prospect, other_campaign.id,
        contact_method="Instagram follow request", response_status="No response",
    )
    outreach_service.record_event(
        db_session, prospect, campaign.id,
        contact_method="Other", response_status="No response",
    )

    completed = outreach_service.completed_prospect_ids(
        db_session, campaign.id, ["Instagram follow request"]
    )
    assert completed == {prospect.id}


def test_do_not_contact_blocks_recording_outreach(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    outreach_service.set_do_not_contact(db_session, prospect, reason="Explicit opt-out")
    assert prospect.status == "Do Not Contact"
    with pytest.raises(outreach_service.DoNotContactError):
        outreach_service.record_event(db_session, prospect, campaign.id, contact_method="Instagram DM")


def test_do_not_contact_blocks_scheduling_followups(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    outreach_service.set_do_not_contact(db_session, prospect)
    with pytest.raises(outreach_service.DoNotContactError):
        followups_service.schedule_follow_up(db_session, prospect, campaign.id, datetime.now(timezone.utc))


def test_due_vs_upcoming_tasks_split_correctly(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    now = datetime.now(timezone.utc)
    overdue = followups_service.schedule_follow_up(db_session, prospect, campaign.id, now - timedelta(days=1))
    future = followups_service.schedule_follow_up(db_session, prospect, campaign.id, now + timedelta(days=3))

    due = followups_service.due_tasks(db_session, as_of=now)
    upcoming = followups_service.upcoming_tasks(db_session, as_of=now)

    assert overdue in due and overdue not in upcoming
    assert future in upcoming and future not in due


def test_mark_done_and_skipped_remove_task_from_due_list(db_session, campaign_and_prospect):
    campaign, prospect = campaign_and_prospect
    now = datetime.now(timezone.utc)
    task = followups_service.schedule_follow_up(db_session, prospect, campaign.id, now - timedelta(hours=1))
    followups_service.mark_done(db_session, task)
    assert task.status == "Done"
    assert task.completed_at is not None
    assert task not in followups_service.due_tasks(db_session, as_of=now)
