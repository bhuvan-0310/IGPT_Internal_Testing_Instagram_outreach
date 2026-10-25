from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, JSON, Boolean, Integer, BigInteger, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utcnow():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Prospect(Base):
    __tablename__ = "prospects"
    __table_args__ = (UniqueConstraint("normalized_username", name="uq_prospect_normalized_username"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    normalized_username: Mapped[str] = mapped_column(String(255), index=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reel_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="New", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    campaign: Mapped["Campaign | None"] = relationship(back_populates="prospects")

class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    product_service: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_preset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prospects: Mapped[list["Prospect"]] = relationship(back_populates="campaign")


class SkillProfile(Base):
    """A reusable, editable set of drafting rules that steers AI message
    generation (tone, personalization limits, compliance, etc.)."""
    __tablename__ = "skill_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    rules: Mapped[list["SkillRule"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="SkillRule.priority"
    )
    drafts: Mapped[list["MessageDraft"]] = relationship(back_populates="skill_profile")


class SkillRule(Base):
    """One editable rule within a skill profile, e.g. 'Personalization using
    verified information only'. Enabled rules are compiled into the prompt
    sent to the model, in priority order."""
    __tablename__ = "skill_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("skill_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    instructions: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    profile: Mapped["SkillProfile"] = relationship(back_populates="rules")


class MessageDraft(Base):
    """One generated or edited message variant for a prospect/campaign.

    Regenerating a variant creates a new row with an incremented `version`
    and `parent_id` pointing at the prior version, so history is preserved.
    `is_current` marks the latest version within a variant lineage.
    """
    __tablename__ = "message_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    skill_profile_id: Mapped[int | None] = mapped_column(ForeignKey("skill_profiles.id"), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("message_drafts.id"), nullable=True)
    variant_label: Mapped[str] = mapped_column(String(10), default="A")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    tone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language: Mapped[str | None] = mapped_column(String(80), nullable=True)
    length_preset: Mapped[str | None] = mapped_column(String(40), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="Draft", index=True)  # Draft, Approved, Rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prospect: Mapped["Prospect"] = relationship()
    campaign: Mapped["Campaign"] = relationship()
    skill_profile: Mapped["SkillProfile | None"] = relationship(back_populates="drafts")
    parent: Mapped["MessageDraft | None"] = relationship(remote_side=[id])


class Asset(Base):
    """A managed file or link in the product/catalogue asset library: PDF,
    image, audio, or an external catalogue URL. File bytes live under
    ASSET_DIRECTORY; this row holds metadata only."""
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(40), index=True)  # pdf, image, audio, link
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    campaign: Mapped["Campaign | None"] = relationship()


class VoiceAsset(Base):
    """A generated-or-uploaded audio asset: a voice script turned into speech
    (or an uploaded recording), tied to a campaign and optionally a draft."""
    __tablename__ = "voice_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    source_draft_id: Mapped[int | None] = mapped_column(ForeignKey("message_drafts.id"), nullable=True)
    script_text: Mapped[str] = mapped_column(Text)
    voice: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="generated")  # generated, uploaded
    stored_filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    campaign: Mapped["Campaign"] = relationship()
    source_draft: Mapped["MessageDraft | None"] = relationship()


OUTREACH_STATUSES = [
    "New", "Qualified", "Draft Ready", "Approved", "Contacted", "Replied",
    "Converted", "Skipped", "Not Eligible", "Do Not Contact", "Archived",
]


class OutreachEvent(Base):
    """A manually-confirmed outreach activity: 'I sent/completed this action
    myself.' Never created automatically — recording an event is always a
    human confirmation step, not an automated send."""
    __tablename__ = "outreach_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("message_drafts.id"), nullable=True)
    contact_method: Mapped[str] = mapped_column(String(40), default="Instagram DM")
    contact_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    response_status: Mapped[str] = mapped_column(String(40), default="No response")  # No response, Replied, Positive, Negative, Converted
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    prospect: Mapped["Prospect"] = relationship()
    campaign: Mapped["Campaign"] = relationship()
    draft: Mapped["MessageDraft | None"] = relationship()


class FollowUpTask(Base):
    """A scheduled follow-up reminder. Follow-up messages are never sent
    automatically; this only tracks that a follow-up is due."""
    __tablename__ = "follow_up_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True)  # Pending, Done, Skipped
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prospect: Mapped["Prospect"] = relationship()
    campaign: Mapped["Campaign"] = relationship()


class AuditEvent(Base):
    """Lightweight audit trail for important state changes. Never stores
    secrets, credentials, or full message content with sensitive data."""
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
