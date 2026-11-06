# TrustVault — Secure Document Sharing

TrustVault is a Flask application demonstrating authenticated document sharing with server-side authorization, permission revocation, and a hash-linked audit log.

## Features

- Account registration and login with Werkzeug password hashing.
- New accounts receive the least-privilege `viewer` role.
- `owner` accounts can upload files and share them with named users.
- Separate view and download permissions, checked on every request.
- Revocation disables future access requests immediately.
- Files are stored outside Flask's public `static` directory under random server-generated names.
- File extension allowlist and 10 MB upload limit.
- Admin console for user overview, recent audit events, and audit-chain verification.
- CSRF protection on forms and security response headers.
- Pytest tests for registration, upload/download, denied access, revocation, and audit tampering.

## Important limitations

This is a hiring-challenge demonstration, not a production document vault. It does not provide end-to-end encryption, malware scanning, multi-factor authentication, rate limiting, external object storage, or protection against a compromised server/admin. A user who already downloaded a file cannot be made to forget that copy. Revocation blocks future requests; it cannot recall bytes already delivered. The audit chain is tamper-evident, not tamper-proof: a privileged attacker able to rewrite the entire database can recompute hashes. Production systems should anchor audit checkpoints outside the application/database.

The admin role can inspect users and audit events and can access document routes. Only owners (or admins) can grant/revoke permissions. Do not upload real sensitive or regulated documents.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- Git (optional for local run; required for GitHub workflow)

## Run on Windows

Open PowerShell in the project directory.

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run this once in the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Set a local secret key in `.env` before running. Example only; generate your own random value.

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `.env` as `SECRET_KEY=...`.

Initialize the database:

```powershell
flask --app app init-db
```

Create the first administrator interactively:

```powershell
flask --app app create-admin
```

Run the server:

```powershell
flask --app app run --debug
```

Open http://127.0.0.1:5000 in your browser. Stop the server with Ctrl+C.

## Create an Owner account

New self-registered accounts are viewers. Create an account in the browser, then promote it to owner using the local SQLite database. The simplest approach is to use the included Flask shell:

```powershell
flask --app app shell
```

Then enter:

```python
from models import User
from extensions import db
u = User.query.filter_by(email="your-email@example.com").first()
u.role = "owner"
db.session.commit()
exit()
```

For the challenge, create an admin account with the CLI first. You may use the admin account to upload and share documents. Admin access is intentionally powerful; use it only for demonstration.

## Run tests

```powershell
pytest -q
```

## GitHub publication

1. Create a new **Public** repository named `trustvault`.
2. Do not upload `.env`, `instance/`, the database, or private documents.
3. In the project folder:

```powershell
git init
git add .
git commit -m "Build TrustVault secure document sharing MVP"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/trustvault.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

## Deployment notes

A production deployment needs a persistent disk/volume for SQLite and uploaded files, or a managed database plus object storage. A typical free web-service filesystem may be ephemeral, so files and SQLite data can disappear on restart/redeploy. Do not claim persistent production storage unless you configure it.

For a basic Render deployment:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Set `SECRET_KEY` to a strong random secret.
- Set `COOKIE_SECURE=1` when served over HTTPS.
- Set `UPLOAD_FOLDER` to a persistent disk path.
- Set `DATABASE_URL` to a persistent SQLite path or supported PostgreSQL URL. If using PostgreSQL, install a compatible PostgreSQL driver and adapt the dependency/configuration before deployment.
- Run `flask --app app init-db` as a one-time setup command or through a controlled release command.
- Create the admin account through a secure one-time shell/CLI process; never hard-code credentials.

The current project is SQLite-first and is not automatically configured for PostgreSQL.

## Security model

- The browser never receives the internal storage filename.
- Downloads go through an authenticated route.
- The route checks current owner/admin status or an active download permission in the database on every request.
- Share and revoke actions are POST-only and CSRF-protected.
- Audit entries are linked using SHA-256 hashes; the admin page verifies the chain.

## Challenge documentation

See `THREATS.md` for the threat model and `PROMPTS.md` for an honest AI-use log. Update `PROMPTS.md` with the actual prompts, dates, AI outputs, mistakes, and your own verification/fixes as you work. Do not claim checks you have not personally run.

See [RENDER_DEPLOY.md](RENDER_DEPLOY.md) for the current Render setup, including first-admin bootstrapping and storage limitations.
