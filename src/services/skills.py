"""CRUD helpers for skill profiles and rules, plus the built-in defaults."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models import SkillProfile, SkillRule

DEFAULT_RULES = [
    {
        "name": "Personalization using verified information only",
        "instructions": (
            "Personalize using only facts explicitly present in the prospect or campaign "
            "context provided. Never invent details, relationships, interests, or shared "
            "connections that are not stated."
        ),
        "priority": 1,
    },
    {
        "name": "Tone and style",
        "instructions": "Match the requested tone. Sound like a real person, not a template or a bot.",
        "priority": 2,
    },
    {
        "name": "Product/service factual accuracy",
        "instructions": (
            "Only state product or service facts that are given in the campaign's product/service "
            "description or asset notes. Do not fabricate pricing, features, or availability."
        ),
        "priority": 1,
    },
    {
        "name": "Relevance",
        "instructions": "Tie the message to the prospect's stated context or the campaign's objective.",
        "priority": 3,
    },
    {
        "name": "Call to action",
        "instructions": "End with a single clear, low-pressure call to action appropriate to the campaign objective.",
        "priority": 3,
    },
    {
        "name": "Message length",
        "instructions": "Respect the requested length preset (short ~2 sentences, medium ~4 sentences, long ~6-8 sentences).",
        "priority": 4,
    },
    {
        "name": "Language",
        "instructions": "Write entirely in the requested language.",
        "priority": 2,
    },
    {
        "name": "Repetition control",
        "instructions": "Avoid repeating phrasing used in other variants for the same prospect; vary opening lines.",
        "priority": 5,
    },
    {
        "name": "Compliance and respectful contact",
        "instructions": (
            "Never include stealth, deceptive, or manipulative language. Never claim a relationship "
            "that doesn't exist. Make it easy to decline or ignore. Do not pressure or guilt the recipient."
        ),
        "priority": 1,
    },
    {
        "name": "Output formatting",
        "instructions": "Output plain message text only, no markdown, no subject line, no quotation marks around the whole message.",
        "priority": 6,
    },
]


def seed_default_profile(session: Session) -> SkillProfile:
    """Create the built-in 'Default' skill profile with default rules if it
    doesn't already exist. Idempotent."""
    existing = session.scalar(select(SkillProfile).where(SkillProfile.name == "Default"))
    if existing:
        return existing
    profile = SkillProfile(name="Default", description="Starter rule set covering personalization, tone, accuracy, and compliance.")
    session.add(profile)
    session.flush()
    for rule in DEFAULT_RULES:
        session.add(SkillRule(profile_id=profile.id, enabled=True, **rule))
    session.flush()
    return profile


def list_profiles(session: Session) -> list[SkillProfile]:
    return list(session.scalars(select(SkillProfile).order_by(SkillProfile.name)).all())


def duplicate_profile(session: Session, profile_id: int, new_name: str) -> SkillProfile:
    source = session.get(SkillProfile, profile_id)
    if source is None:
        raise ValueError("Source skill profile not found.")
    existing = session.scalar(select(SkillProfile).where(SkillProfile.name == new_name))
    if existing:
        raise ValueError(f"A skill profile named '{new_name}' already exists.")
    clone = SkillProfile(name=new_name, description=source.description)
    session.add(clone)
    session.flush()
    for rule in source.rules:
        session.add(SkillRule(
            profile_id=clone.id, name=rule.name, instructions=rule.instructions,
            enabled=rule.enabled, priority=rule.priority, example=rule.example,
            constraints=rule.constraints,
        ))
    session.flush()
    return clone
