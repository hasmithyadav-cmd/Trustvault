# Deploy TrustVault on Render

These settings are for the current Flask project structure. The repository contains
`app.py`, `requirements.txt`, and `Procfile` at the repository root, so leave
Render's **Root Directory** blank.

## Create the web service

1. Sign in at https://render.com/.
2. Choose **New + → Web Service**.
3. Connect GitHub and select `hasmithyadav-cmd/Trustvault`.
4. Select branch `main`.
5. Runtime/language: **Python 3**.
6. Root Directory: **leave blank**.
7. Build Command: `pip install -r requirements.txt`
8. Start Command:

   `flask --app app init-db && flask --app app bootstrap-admin && gunicorn app:app`

9. Choose the Free plan only for a temporary challenge demonstration, then create the service.

## Add environment variables in Render

In the service's Environment section, add:

- `SECRET_KEY`: a fresh random value generated locally with
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- `COOKIE_SECURE`: `1`
- `BOOTSTRAP_ADMIN_EMAIL`: the admin email you want to use on the live site.
- `BOOTSTRAP_ADMIN_NAME`: the admin display name.
- `BOOTSTRAP_ADMIN_PASSWORD`: a unique password at least 12 characters long.

Do not put these secrets in GitHub or send them in chat. Enter them only in Render's
Environment settings. Save changes and let Render redeploy.

The start command creates the database tables, creates the first administrator
from the environment variables if no admin exists, and starts Gunicorn. The
bootstrap command is safe to run on later starts: it skips creation if an admin
already exists.

## Important storage warning

This app currently uses SQLite and stores uploaded documents on the local
filesystem. Render Free services have an ephemeral filesystem and spin down
after inactivity. The SQLite database and uploaded files can therefore be lost
after a restart, redeploy, or spin-down. Use only disposable sample documents.
Do not present this deployment as persistent or production-secure storage.

For persistent storage, move to a managed database plus object storage, or use a
paid Render service with a persistent disk mounted at a path that matches the
app's database and upload configuration. This requires additional configuration.
