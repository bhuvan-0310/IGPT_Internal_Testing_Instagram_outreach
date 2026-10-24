# Instagram Outreach Studio

A local-first Streamlit application scaffold. Phase 1 provides PostgreSQL-backed prospect import, deduplication, prospect browsing, campaign creation, and a dashboard. Phases 2–5 are scaffolded as separate pages for incremental implementation.

## Requirements

- Python 3.11 or 3.12 recommended
- PostgreSQL 14+
- Git (optional)

## 1. Create the PostgreSQL database

Open `psql` as a PostgreSQL administrator, then run:

```sql
CREATE USER outreach_app WITH PASSWORD 'replace-with-a-strong-password';
CREATE DATABASE instagram_outreach OWNER outreach_app;
```

Use a strong local password. If you already have PostgreSQL configured, create a database and user using your normal administration method.

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

If PowerShell blocks activation, use Command Prompt and run `.venv\\Scripts\\activate.bat`, or invoke `.venv\\Scripts\\python.exe` directly.

## 3. Configure the environment

Copy `.env.example` to `.env`, then edit `DATABASE_URL`.

Example:

```dotenv
DATABASE_URL=postgresql+psycopg://outreach_app:YOUR_PASSWORD@localhost:5432/instagram_outreach
```

If the password contains URL-reserved characters, URL-encode them in the connection string. Do not commit `.env` to version control.

## 4. Launch

From the project root with the virtual environment active:

```bash
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`.

The database tables are created automatically on first launch. Keep PostgreSQL running.

## 5. First workflow

1. Open **Prospects**.
2. Upload an Apify CSV/JSON-export-as-CSV or Excel file.
3. Map the username column and any optional fields.
4. Preview the rows and import.
5. Open **Campaigns** and create a campaign.
6. Assign prospects to the campaign from the prospect editor.

The importer currently accepts CSV and Excel files. Convert JSON exports to CSV first if needed. Import deduplication is based on normalized username.

## Architecture

- `app.py`: dashboard and application entry point
- `pages/`: Streamlit pages for all five phases
- `src/models.py`: SQLAlchemy data models
- `src/database.py`: PostgreSQL engine and session management
- `src/config.py`: environment-based configuration
- `data/`: local runtime files; excluded from version control

## Current implementation status

- Phase 1: initial working foundation
- Phase 2: Message Studio and Skill Matrix placeholders
- Phase 3: Voice Studio and Asset Library placeholders
- Phase 4: Outreach Tracker and Playwright Workspace placeholders
- Phase 5: additional tests, security review, backup and packaging work

Do not treat the placeholder pages as completed integrations. OpenAI, Apify API access, audio generation, Playwright browser actions and event-based outreach tracking are not wired up yet.

## Safety and account security

- Instagram login should happen directly in the dedicated browser profile; do not put Instagram passwords into `.env` or the application.
- Keep API tokens out of source code and logs.
- Review messages before using them.
- Use data and messaging features only where collection and contact are permitted.
- This scaffold does not implement stealth or bot-detection evasion, or unattended bulk unsolicited follow requests/DMs.
