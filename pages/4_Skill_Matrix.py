import streamlit as st
from sqlalchemy import select
from src.database import get_session
from src.models import SkillProfile, SkillRule
from src.services import skills as skills_service
from src.ui import page_header, require_database

st.set_page_config(page_title="Skill Matrix | Outreach Studio", layout="wide")
require_database()
page_header("Skill Matrix", "Create reusable skills and descriptions that steer AI message generation. You can choose individual enabled skills in Message Studio.")

with get_session() as session:
    skills_service.seed_default_profile(session)
    skills_service.seed_marketing_course_profile(session)

with get_session() as session:
    profiles = skills_service.list_profiles(session)
    profile_names = [p.name for p in profiles]

col1, col2 = st.columns([2, 1])
with col1:
    selected_name = st.selectbox("Skill profile", profile_names, index=0)
with col2:
    with st.popover("New / duplicate skill profile"):
        new_name = st.text_input("New profile name")
        duplicate_from = st.selectbox("Start from", ["— Blank —"] + profile_names)
        if st.button("Create profile"):
            if not new_name.strip():
                st.error("Enter a name.")
            else:
                try:
                    with get_session() as session:
                        if duplicate_from == "— Blank —":
                            if session.scalar(select(SkillProfile).where(SkillProfile.name == new_name.strip())):
                                raise ValueError(f"A skill profile named '{new_name.strip()}' already exists.")
                            session.add(SkillProfile(name=new_name.strip()))
                        else:
                            source = session.scalar(select(SkillProfile).where(SkillProfile.name == duplicate_from))
                            skills_service.duplicate_profile(session, source.id, new_name.strip())
                    st.success(f"Created '{new_name.strip()}'.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

st.divider()

with get_session() as session:
    profile = session.scalar(select(SkillProfile).where(SkillProfile.name == selected_name))
    if profile is None:
        st.info("No skill profile selected.")
        st.stop()

    with st.form("profile_meta"):
        desc = st.text_area("Profile description", value=profile.description or "")
        if st.form_submit_button("Save description"):
            profile.description = desc.strip() or None
            st.success("Description saved.")

    st.subheader(f"Skills in '{profile.name}'")
    rules = list(profile.rules)
    for rule in rules:
        with st.expander(f"{'✅' if rule.enabled else '⬜'} {rule.name} (priority {rule.priority})", expanded=False):
            with st.form(f"rule_{rule.id}"):
                name = st.text_input("Skill name", value=rule.name, key=f"name_{rule.id}")
                instructions = st.text_area("Skill description and instructions", value=rule.instructions, key=f"instr_{rule.id}", height=100)
                example = st.text_input("Example (optional)", value=rule.example or "", key=f"ex_{rule.id}")
                c1, c2, c3 = st.columns(3)
                enabled = c1.checkbox("Enabled", value=rule.enabled, key=f"en_{rule.id}")
                priority = c2.number_input("Priority (lower = applied first)", min_value=1, max_value=99, value=rule.priority, key=f"pr_{rule.id}")
                saved = c3.form_submit_button("Save skill")
                deleted = st.form_submit_button("Delete skill", type="secondary")
                if saved:
                    rule.name, rule.instructions, rule.example = name, instructions, example or None
                    rule.enabled, rule.priority = enabled, priority
                    st.success("Skill saved.")
                    st.rerun()
                if deleted:
                    with get_session() as del_session:
                        del_session.delete(del_session.get(SkillRule, rule.id))
                    st.success("Skill deleted.")
                    st.rerun()

    st.subheader("Add a new skill")
    with st.form("new_rule", clear_on_submit=True):
        rn = st.text_input("Skill name")
        ri = st.text_area("Skill description and instructions", help="Describe exactly how this skill should shape the generated message.")
        re_ = st.text_input("Example (optional)")
        rp = st.number_input("Priority", min_value=1, max_value=99, value=10)
        if st.form_submit_button("Add skill"):
            if not rn.strip() or not ri.strip():
                st.error("Name and description are required.")
            else:
                with get_session() as session2:
                    session2.add(SkillRule(profile_id=profile.id, name=rn.strip(), instructions=ri.strip(),
                                            example=re_.strip() or None, priority=rp, enabled=True))
                st.success("Skill added.")
                st.rerun()
