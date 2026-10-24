from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, JSON
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
