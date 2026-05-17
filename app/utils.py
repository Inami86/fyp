from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def editor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role not in ['admin', 'editor']:
            flash('Non hai i permessi per eseguire questa azione.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            flash('Accesso riservato agli amministratori.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def region_to_slug(region: str) -> str:
    """Converte il nome regione nel nome file GeoJSON corrispondente."""
    return (region
        .replace(' ', '_')
        .replace('/', '_')
        .replace("'", '')
        .replace('é', 'e')
        .replace('ü', 'u')
    )


def get_research_municipalities(research):
    """Comuni della regione della ricerca, ordinati per nome."""
    from app.models import Municipality
    if not research:
        return []
    return Municipality.query.filter_by(region=research.region).order_by(Municipality.name).all()


def get_research_members(research_id):
    """Utenti membri della ricerca."""
    from app.models import ResearchUser, User
    if not research_id:
        return []
    mem_ids = [m.user_id for m in ResearchUser.query.filter_by(research_id=research_id).all()]
    return User.query.filter(User.id.in_(mem_ids)).all()


def notify_team(research_id, exclude_user_id, message, link=None):
    """Crea una notifica per tutti i membri della ricerca, escluso chi ha fatto l'azione."""
    from app.models import ResearchUser, Notification
    from app import db
    members = ResearchUser.query.filter_by(research_id=research_id).all()
    for m in members:
        if m.user_id != exclude_user_id:
            db.session.add(Notification(
                user_id=m.user_id, message=message, link=link, is_read=False
            ))
