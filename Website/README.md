
# KUE Transportdrohne – Prototyp

Lokaler Prototyp einer seriösen, mehrseitigen Website mit Adress-Erfassung.
- Frontend: HTML/CSS (Jinja2-Templates via Flask)
- Backend: Python Flask
- Speicherung: SQLite (orders.db)
- Admin-Seite: Basic Auth (Nutzer: `admin`, Passwort: `kue-secret` per ENV überschreibbar)

## Start (lokal)
```bash
# im Projektordner
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install flask werkzeug
python app.py
# Browser: http://127.0.0.1:5000
```

## Struktur
```
app.py
templates/
  base.html, home.html, about.html, order.html, admin.html, imprint.html
static/
  css/style.css
  assets/logo.svg
```

## Deployment (später)
- z.B. Render, Railway, Fly.io oder eigener Server (uWSGI/Gunicorn + Nginx + TLS).
- SQLite kann durch PostgreSQL ersetzt werden.
