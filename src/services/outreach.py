"""Outreach event recording and Do Not Contact enforcement.

Every event here represents a human-confirmed action that already happened
manually (in the browser workspace or elsewhere) — this module never sends
anything. Do Not Contact is enforced here, not just in the UI, so no code
path can record or schedule outreach for a prospect marked Do Not Contact.
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models import AuditEvent, FollowUpTask, OutreachEvent, Prospect

DO_NOT_CONTACT_STATUS = "Do Not Contact"


class DoNotContactError(ValueError):
    pass


def _audit(session: Session, event_type: str, entity_type: str, entity_id: int | None, summary: str):
    session.add(AuditEvent(event_type=event_type, entity_type=entity_type, entity_id=entity_id, summary=summary))


def assert_contactable(prospect: Prospect):
    if prospect.status == DO_NOT_CONTACT_STATUS:
        raise DoNotContactError(
            f"@{prospect.username} is marked Do Not Contact. Change their status before recording outreach."
        )


def record_event(
    session: Session, prospect: Prospect, campaign_id: int, *, contact_method: str,
    response_status: str = "No response", outcome: str | None = None, notes: str | None = None,
    draft_id: int | None = None, error_details: str | None = None,
) -> OutreachEvent:
    assert_contactable(prospect)
    event = OutreachEvent(
        prospect_id=prospect.id, campaign_id=campaign_id, draft_id=draft_id,
        contact_method=contact_method, response_status=response_status,
        outcome=outcome, notes=notes, error_details=error_details,
    )
    session.add(event)
    # An outreach event is always performed in the selected campaign. Keep the
    # prospect's current campaign in sync so the Prospects view can show it and
    # users can filter the prospect from that campaign later.
    prospect.campaign_id = campaign_id
    prospect.status = "Contacted" if response_status == "No response" else (
        "Replied" if response_status in {"Replied", "Positive", "Negative"} else prospect.status
    )
    if response_status == "Converted":
        prospect.status = "Converted"
    session.flush()
    _audit(session, "outreach_recorded", "prospect", prospect.id,
           f"Recorded {contact_method} outreach for @{prospect.username} ({response_status}).")
    session.flush()
    return event


def set_do_not_contact(session: Session, prospect: Prospect, reason: str | None = None):
    prospect.status = DO_NOT_CONTACT_STATUS
    session.flush()
    _audit(session, "do_not_contact_set", "prospect", prospect.id,
           f"@{prospect.username} marked Do Not Contact." + (f" Reason: {reason}" if reason else ""))
    session.flush()


def history_for(session: Session, prospect_id: int) -> list[OutreachEvent]:
    stmt = select(OutreachEvent).where(OutreachEvent.prospect_id == prospect_id).order_by(OutreachEvent.contact_date.desc())
    return list(session.scalars(stmt).all())


def completed_prospect_ids(
    session: Session, campaign_id: int, contact_methods: list[str]
) -> set[int]:
    """Return prospects with a recorded manual completion for this campaign.

    The Browser Workspace uses this to show campaign progress. It never
    performs outreach; an ID appears here only after the user records an
    action they already completed manually.
    """
    if not contact_methods:
        return set()
    stmt = select(OutreachEvent.prospect_id).where(
        OutreachEvent.campaign_id == campaign_id,
        OutreachEvent.contact_method.in_(contact_methods),
    ).distinct()
    return set(session.scalars(stmt).all())
