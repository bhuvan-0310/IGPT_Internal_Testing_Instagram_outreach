"""Prospect import (CSV/Excel) with username-based deduplication."""
from dataclasses import dataclass
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models import Prospect

COLUMN_GUESSES = {
    "username": {"username", "user_name", "handle", "instagram_username", "ownerusername"},
}


@dataclass
class ImportResult:
    imported: int
    skipped: int


def guess_username_column(columns: list[str]) -> str | None:
    return next((c for c in columns if c.lower().strip() in COLUMN_GUESSES["username"]), None)


def _cell(row, col: str | None):
    if not col or col == "— None —":
        return None
    value = row.get(col)
    return None if pd.isna(value) else str(value).strip()


def import_dataframe(
    session: Session, df: pd.DataFrame, *, username_col: str,
    display_col: str | None = None, profile_col: str | None = None,
    source_id_col: str | None = None, bio_col: str | None = None,
    reel_col: str | None = None, text_col: str | None = None,
) -> ImportResult:
    """Import rows from a DataFrame, skipping blank usernames and duplicates
    (by normalized/lowercased username, including duplicates already in the
    database or earlier in the same file)."""
    existing = {p.normalized_username for p in session.scalars(select(Prospect)).all()}
    imported = skipped = 0

    for _, row in df.iterrows():
        raw_username = str(row.get(username_col, "")).strip().lstrip("@")
        if not raw_username or raw_username.lower() in {"nan", "none"}:
            skipped += 1
            continue
        normalized = raw_username.lower()
        if normalized in existing:
            skipped += 1
            continue

        profile = _cell(row, profile_col) or f"https://www.instagram.com/{raw_username}/"
        raw_data = {}
        for k, v in row.items():
            try:
                raw_data[str(k)] = None if pd.isna(v) else str(v)
            except (TypeError, ValueError):
                raw_data[str(k)] = str(v)

        session.add(Prospect(
            username=raw_username, normalized_username=normalized,
            source_id=_cell(row, source_id_col), source_platform="import",
            profile_url=profile, display_name=_cell(row, display_col), bio=_cell(row, bio_col),
            source_reel_url=_cell(row, reel_col), source_text=_cell(row, text_col),
            raw_data=raw_data, status="New",
        ))
        existing.add(normalized)
        imported += 1

    session.flush()
    return ImportResult(imported=imported, skipped=skipped)
