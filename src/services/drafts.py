"""Message draft generation, persistence, versioning, and review."""
import string
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.integrations.openai_client import generate_text
from src.config import OPENAI_TEXT_MODEL
from src.models import Campaign, MessageDraft, Prospect, SkillProfile
from src.prompts.message_prompt import DraftRequest, build_system_prompt, build_user_prompt, split_variants


def generate_variants(
    session: Session,
    prospect: Prospect,
    campaign: Campaign,
    skill_profile: SkillProfile | None,
    tone: str,
    language: str,
    length_preset: str,
    variant_count: int,
    skill_rule_ids: list[int] | None = None,
) -> list[MessageDraft]:
    """Generate `variant_count` new drafts (version 1, variant labels A, B, C...)
    for this prospect/campaign and persist them as Draft status."""
    rules = skill_profile.rules if skill_profile else []
    if skill_rule_ids is not None:
        selected_ids = set(skill_rule_ids)
        rules = [rule for rule in rules if rule.id in selected_ids]
    request = DraftRequest(
        prospect=prospect, campaign=campaign, rules=rules,
        tone=tone, language=language, length_preset=length_preset, variant_count=variant_count,
    )
    system_prompt = build_system_prompt(rules)
    user_prompt = build_user_prompt(request)
    raw = generate_text(system_prompt, user_prompt, model=OPENAI_TEXT_MODEL)
    variants = split_variants(raw, variant_count)

    labels = string.ascii_uppercase
    created = []
    for i, content in enumerate(variants):
        draft = MessageDraft(
            prospect_id=prospect.id,
            campaign_id=campaign.id,
            skill_profile_id=skill_profile.id if skill_profile else None,
            variant_label=labels[i % len(labels)],
            version=1,
            is_current=True,
            tone=tone,
            language=language,
            length_preset=length_preset,
            model_name=OPENAI_TEXT_MODEL,
            content=content,
            status="Draft",
        )
        session.add(draft)
        created.append(draft)
    session.flush()
    return created


def regenerate_variant(session: Session, draft: MessageDraft) -> MessageDraft:
    """Regenerate a single variant, creating a new version linked to the
    prior one. The prior version is marked not-current but kept for history."""
    prospect = session.get(Prospect, draft.prospect_id)
    campaign = session.get(Campaign, draft.campaign_id)
    skill_profile = session.get(SkillProfile, draft.skill_profile_id) if draft.skill_profile_id else None
    rules = skill_profile.rules if skill_profile else []

    request = DraftRequest(
        prospect=prospect, campaign=campaign, rules=rules,
        tone=draft.tone or "friendly", language=draft.language or "English",
        length_preset=draft.length_preset or "short", variant_count=1,
    )
    system_prompt = build_system_prompt(rules)
    user_prompt = build_user_prompt(request)
    raw = generate_text(system_prompt, user_prompt, model=OPENAI_TEXT_MODEL)
    content = split_variants(raw, 1)[0]

    draft.is_current = False
    new_draft = MessageDraft(
        prospect_id=draft.prospect_id,
        campaign_id=draft.campaign_id,
        skill_profile_id=draft.skill_profile_id,
        parent_id=draft.id,
        variant_label=draft.variant_label,
        version=draft.version + 1,
        is_current=True,
        tone=draft.tone,
        language=draft.language,
        length_preset=draft.length_preset,
        model_name=OPENAI_TEXT_MODEL,
        content=content,
        status="Draft",
    )
    session.add(new_draft)
    session.flush()
    return new_draft


def save_edit(session: Session, draft: MessageDraft, new_content: str) -> MessageDraft:
    """Persist a manual edit to a draft's content without calling the API."""
    draft.content = new_content
    session.flush()
    return draft


def set_status(session: Session, draft: MessageDraft, status: str) -> MessageDraft:
    """Set a draft's review status. 'Approved' means the content is cleared
    for manual use in outreach — it does NOT mean a message was sent."""
    if status not in {"Draft", "Approved", "Rejected"}:
        raise ValueError(f"Invalid draft status: {status}")
    draft.status = status
    session.flush()
    return draft


def current_variants_for(session: Session, prospect_id: int, campaign_id: int) -> list[MessageDraft]:
    stmt = (
        select(MessageDraft)
        .where(
            MessageDraft.prospect_id == prospect_id,
            MessageDraft.campaign_id == campaign_id,
            MessageDraft.is_current.is_(True),
        )
        .order_by(MessageDraft.variant_label)
    )
    return list(session.scalars(stmt).all())


def version_history(session: Session, draft: MessageDraft) -> list[MessageDraft]:
    """Walk the parent chain to return all versions of this variant lineage,
    oldest first."""
    chain = [draft]
    current = draft
    while current.parent_id:
        current = session.get(MessageDraft, current.parent_id)
        if current is None:
            break
        chain.append(current)
    return list(reversed(chain))
