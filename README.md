# Instagram Outreach Studio

A local-first Streamlit application for managing prospects, campaigns, AI-assisted message drafting, voice assets, a product/catalogue asset library, and human-reviewed outreach tracking — including a dedicated, manually-operated browser workspace for completing outreach on Instagram yourself.

**Nothing in this app sends a message, follows an account, or posts a comment automatically.** AI drafting produces editable drafts; approving a draft only marks it ready for you to use manually. Outreach events are recorded after you've already performed the action yourself.

## Implementation status

| Phase | Area | Status |
|---|---|---|
| 1 | PostgreSQL foundation, prospect import/dedup, campaigns, migrations | Done |
| 2 | Message Studio (AI drafting, versioning, approval) + Skill Matrix (editable rule profiles) | Done |
| 3 | Voice Studio (TTS generation/upload) + Asset Library (PDFs, images, audio, links) | Done |
| 4 | Outreach Tracker (events, follow-ups, Do Not Contact) + Playwright Browser Workspace | Done |
| 5 | Automated tests, security hardening, migrations, docs | Done |

AI drafting and text-to-speech require your own `OPENAI_API_KEY` in `.env` — without it, those pages show an actionable error instead of failing silently. The Browser Workspace requires Playwright's Chromium binary to be installed locally (see below).

## Requirements

- Python 3.11 or 3.12 recommended (tested on 3.13)
- PostgreSQL 14+ running locally
- Git (optional)

## 1. Create the PostgreSQL role and database

This app connects as a **dedicated, least-privilege role** (`outreach_app`), not the PostgreSQL superuser. Create it once using an admin connection (psql, or your GUI admin tool such as pgAdmin):

```sql
CREATE ROLE outreach_app LOGIN PASSWORD 'replace-with-a-strong-password';
CREATE DATABASE instagram_outreach OWNER outreach_app;
GRANT ALL PRIVILEGES ON DATABASE instagram_outreach TO outreach_app;
```

If you don't know your local PostgreSQL superuser password, use a GUI tool (pgAdmin, Postgres.app, etc.) that already has an authenticated session, and run the same SQL there.

## 2. Create a virtual environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Always run the app and its tools through `.venv`** (`.venv/bin/python`, `.venv/bin/streamlit`, `.venv/bin/pytest`, `.venv/bin/alembic`), not a system or Anaconda Python — mixing interpreters is the most common cause of `ModuleNotFoundError: No module named 'psycopg'`.

### Playwright (required for the Browser Workspace)

```bash
.venv/bin/playwright install chromium
```

## 3. Configure the environment

Copy `.env.example` to `.env`, then edit `DATABASE_URL` to match the role/database you created:

```dotenv
DATABASE_URL=postgresql+psycopg://outreach_app:YOUR_PASSWORD@localhost:5432/instagram_outreach
```

If the password contains URL-reserved characters (`@ : / ? #`), URL-encode them. Add `OPENAI_API_KEY` to enable Message Studio and Voice Studio. Never commit `.env` — it's gitignored.

## 4. Apply database migrations

Schema changes are managed with **Alembic**, not automatic table creation. Run this once after setup, and again after pulling any update that adds a migration file:

```bash
.venv/bin/alembic upgrade head
```

This creates/updates tables without ever dropping or overwriting existing data. To see pending migrations without applying them: `.venv/bin/alembic history`.

## 5. Launch

```bash
.venv/bin/streamlit run app.py
```

Streamlit prints a local URL, usually `http://localhost:8501`. The app binds to `localhost` only by default (see `.streamlit/config.toml`) — it is not exposed to your network.

## 6. First workflow

1. **Prospects** — upload a CSV/Excel export, map the username column (and optional fields), preview, and import. Duplicate usernames (case-insensitive) are skipped automatically.
2. **Campaigns** — create a campaign with product/service, audience, and objective.
3. **Skill Matrix** — review/edit the default rule profile, or create your own.
4. **Message Studio** — generate, edit, regenerate, and approve message drafts per prospect/campaign.
5. **Voice Studio** / **Asset Library** — optionally generate or upload voice assets and manage product/catalogue files.
6. **Outreach Tracker** / **Browser Workspace** — open a prospect's profile in the dedicated browser, sign in to Instagram yourself, perform the action, then record it.

## Running tests

```bash
.venv/bin/pytest
```

Most tests use an isolated in-memory SQLite database and mocked OpenAI/filesystem calls — they need no live services. A small number of tests are marked `requires_postgres` and exercise the real `DATABASE_URL` from `.env`:

```bash
.venv/bin/pytest -m requires_postgres   # needs PostgreSQL running and configured
.venv/bin/pytest -m "not requires_postgres"  # skip the live-DB test
```

## Database backup and restore

**Backup:**
```bash
pg_dump --format=custom --file=backup.dump "postgresql://outreach_app:YOUR_PASSWORD@localhost:5432/instagram_outreach"
```

**Restore** (into an existing empty database):
```bash
pg_restore --clean --if-exists --dbname="postgresql://outreach_app:YOUR_PASSWORD@localhost:5432/instagram_outreach" backup.dump
```

Back up `data/assets/` and `data/audio/` alongside the database — asset/voice-asset rows reference files on disk by filename, and a database-only restore will show broken file links.

## Data retention and deletion

- All records persist in PostgreSQL until you explicitly delete them in the app.
- Deleting an asset or voice asset also deletes its file from `data/` immediately.
- The dedicated browser profile (`data/browser_profile/`) holds your Instagram session cookies for that profile only; delete the folder to sign out everywhere.
- The app never auto-deletes or auto-expires data.

## Architecture

- `app.py` — dashboard and entry point
- `pages/` — one Streamlit page per feature area
- `src/models.py` — SQLAlchemy models (single source of schema truth)
- `src/database.py` — engine, session management, connectivity diagnostics
- `src/config.py` — environment-based configuration with validation
- `src/services/` — business logic (prospects, skills, drafts, assets, voice, outreach, follow-ups) — independent of Streamlit, directly unit-testable
- `src/integrations/` — external systems (OpenAI, Playwright browser)
- `src/prompts/` — LLM prompt construction
- `migrations/` — Alembic migration history
- `data/` — local runtime files (assets, audio, browser profile); gitignored
- `tests/` — pytest suite

## Troubleshooting

**`password authentication failed`** — `DATABASE_URL` doesn't match an existing role/password, or you're missing a line in `.env`. Re-run the role/database setup in Step 1, and check Settings → Database in the app for a masked connection string and live status.

**`ModuleNotFoundError: No module named 'psycopg'`** — you're running a Python interpreter outside `.venv` (commonly Anaconda's `python`). Always invoke `.venv/bin/python` / `.venv/bin/streamlit` explicitly, or make sure `.venv` is activated (`which python` should point inside the project's `.venv`).

**`DATABASE_URL is not set`** — copy `.env.example` to `.env` in the project root and fill in `DATABASE_URL`. The app loads `.env` from the project root explicitly, regardless of the directory you ran `streamlit run` from.

**Tables don't exist / stale schema after pulling updates** — run `.venv/bin/alembic upgrade head`.

**Browser Workspace: "Executable doesn't exist"** — run `.venv/bin/playwright install chromium`.

**Postgres requires a password but you don't know it** — if you have an authenticated GUI session (e.g. pgAdmin already logged in), use its Query Tool to run the role/database setup SQL from Step 1 instead of the command line.

## Safety and account security

- Instagram login happens directly in the dedicated browser window; this app never sees, stores, or logs your Instagram password.
- Message drafts remain drafts until you explicitly approve them — approval never means a message was sent.
- No stealth automation, fingerprint spoofing, CAPTCHA bypass, or bot-detection evasion is implemented or planned.
- No unattended bulk follow requests or unsolicited DMs — every outreach event is recorded only after you manually performed it.
- Prospects marked **Do Not Contact** are blocked from new outreach and follow-up scheduling at the service layer, not just hidden in the UI.
- Use imported data and messaging features only where collection and contact are permitted by the platform's terms and applicable law.
