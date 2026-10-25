"""Follow-up task scheduling and tracking. These are reminders only —
nothing here sends a follow-up message automatically."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models import FollowUpTask, Prospect
from src.services.outreach import DoNotContactError, assert_contactable


def schedule_follow_up(session: Session, prospect: Prospect, campaign_id: int, due_date: datetime, notes: str | None = None) -> FollowUpTask:
    assert_contactable(prospect)
    task = FollowUpTask(prospect_id=prospect.id, campaign_id=campaign_id, due_date=due_date, notes=notes, status="Pending")
    session.add(task)
    session.flush()
    return task


def due_tasks(session: Session, as_of: datetime | None = None) -> list[FollowUpTask]:
    as_of = as_of or datetime.now(timezone.utc)
    stmt = (
        select(FollowUpTask)
        .where(FollowUpTask.status == "Pending", FollowUpTask.due_date <= as_of)
        .order_by(FollowUpTask.due_date)
    )
    return list(session.scalars(stmt).all())


def upcoming_tasks(session: Session, as_of: datetime | None = None) -> list[FollowUpTask]:
    as_of = as_of or datetime.now(timezone.utc)
    stmt = (
        select(FollowUpTask)
        .where(FollowUpTask.status == "Pending", FollowUpTask.due_date > as_of)
        .order_by(FollowUpTask.due_date)
    )
    return list(session.scalars(stmt).all())


def mark_done(session: Session, task: FollowUpTask):
    task.status = "Done"
    task.completed_at = datetime.now(timezone.utc)
    session.flush()


def mark_skipped(session: Session, task: FollowUpTask):
    task.status = "Skipped"
    task.completed_at = datetime.now(timezone.utc)
    session.flush()
