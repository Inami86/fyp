# Find Your Place (FyP) — v0.2.0

Dashboard collaborativa per la ricerca e gestione di immobili in Italia.
Progettata per team che cercano proprietà su una o più regioni, con mappa interattiva, tracciamento stati, log attività e notifiche.

---

## Stack tecnico

| Layer | Tecnologia |
|-------|-----------|
| Backend | Flask 3.1.0 + SQLAlchemy 3.1.1 |
| Auth | Flask-Login 0.6.3 (sessioni, RBAC admin/editor/viewer) |
| Sicurezza | Flask-WTF (CSRF), Flask-Limiter (rate limiting) |
| Database | SQLite (sviluppo) / PostgreSQL (produzione) |
| Migrazioni | Flask-Migrate + Alembic |
| Frontend | Jinja2 + CSS custom (variabili, dark mode) |
| Mappa | Leaflet.js 1.9.4 + GeoJSON regioni italiane |
| Grafici | Chart.js 4.4.0 |
| PWA | Service Worker + Web Manifest |

---

## Avvio in sviluppo

```bash
# 1. Installa dipendenze
pip install -r requirements.txt

# 2. Avvia l'app
python run.py
```

L'app sarà disponibile su `http://localhost:5000` e su tutta la rete locale (`http://<ip>:5000`).

Il database SQLite viene creato automaticamente in `instance/fyp.sqlite` al primo avvio.

---

## Gestione schema DB (Flask-Migrate)

Dopo ogni modifica ai modelli in `app/models.py`:

```bash
python -m flask --app "app:create_app('development')" db migrate -m "descrizione"
python -m flask --app "app:create_app('development')" db upgrade
```

---

## Struttura

```
fyp/
├── app/
│   ├── __init__.py          # factory, estensioni
│   ├── models.py            # User, Research, Property, Contact, ...
│   ├── utils.py             # helpers: editor_required, notify_team, ...
│   ├── routes/
│   │   ├── auth.py          # login, logout, profilo
│   │   ├── main.py          # dashboard, mappa, API
│   │   ├── properties.py    # CRUD immobili
│   │   ├── contacts.py      # CRUD contatti
│   │   ├── researches.py    # CRUD ricerche
│   │   ├── admin.py         # gestione utenti
│   │   └── notifications.py
│   ├── templates/
│   └── static/
├── config.py                # DevelopmentConfig / ProductionConfig
├── run.py                   # entry point sviluppo
├── wsgi.py                  # entry point produzione (Gunicorn)
├── Procfile                 # per Render/Heroku
└── migrations/              # Alembic (Flask-Migrate)
```

---

## Funzionalità principali

- **Mappa interattiva** per regione con stati comune (esplorato / parziale / inesplorato)
- **CRUD immobili** con foto, URL annuncio, assegnazione a membro del team
- **CRUD contatti** (agenzie, privati, notai) con geolocalizzazione
- **Dashboard** con KPI, 3 grafici (stati, prezzi per comune, inserimenti nel tempo)
- **Commenti e storico modifiche** per ogni immobile
- **Notifiche in-app** per aggiornamenti del team
- **Log attività** completo con filtri per azione e autore
- **Export CSV** degli immobili
- **Ruoli**: admin (tutto), editor (CRUD), viewer (sola lettura)
- **PWA**: installabile su mobile, funziona offline (dati già caricati)

---

## Sicurezza

- CSRF protection su tutti i form (Flask-WTF)
- Rate limiting sul login: 10 tentativi/minuto → HTTP 429
- Password hashate con Werkzeug (PBKDF2)
- SECRET_KEY obbligatoria in produzione (RuntimeError se assente)
- XSS fix: escape dati utente in template e in JavaScript

---

## Deployment (Render + PostgreSQL)

Vedere il piano di deployment per i dettagli. In sintesi:

```bash
# Variabili d'ambiente richieste in produzione
FLASK_ENV=production
SECRET_KEY=<stringa-random-32-byte>
DATABASE_URL=postgresql://...
```

```bash
# Generare SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Account demo (sviluppo)

| Ruolo  | Email              | Password  |
|--------|--------------------|-----------|
| Admin  | admin@fyp.local    | admin123  |
| Editor | editor@fyp.local   | editor123 |
| Viewer | viewer@fyp.local   | viewer123 |
