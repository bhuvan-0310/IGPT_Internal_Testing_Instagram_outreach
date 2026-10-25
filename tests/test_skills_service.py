from sqlalchemy import select
from src.models import SkillProfile
from src.services import skills as skills_service


def test_seed_default_profile_is_idempotent(db_session):
    first = skills_service.seed_default_profile(db_session)
    db_session.commit()
    second = skills_service.seed_default_profile(db_session)
    assert first.id == second.id
    assert db_session.scalar(select(SkillProfile).where(SkillProfile.name == "Default")) is not None
    count = len(db_session.scalars(select(SkillProfile)).all())
    assert count == 1


def test_default_profile_has_enabled_rules(db_session):
    profile = skills_service.seed_default_profile(db_session)
    assert len(profile.rules) > 0
    assert all(r.enabled for r in profile.rules)


def test_duplicate_profile_copies_rules_and_rejects_name_collision(db_session):
    source = skills_service.seed_default_profile(db_session)
    db_session.commit()
    clone = skills_service.duplicate_profile(db_session, source.id, "Default Copy")
    assert clone.id != source.id
    assert len(clone.rules) == len(source.rules)

    try:
        skills_service.duplicate_profile(db_session, source.id, "Default Copy")
        assert False, "expected ValueError for duplicate name"
    except ValueError:
        pass
