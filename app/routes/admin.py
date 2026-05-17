from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db, limiter
from app.models import User, ActivityLog, Research, ResearchUser, Property, Contact
from app.utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    users       = User.query.order_by(User.full_name).all()
    researches  = Research.query.order_by(Research.name).all()
    logs        = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(40).all()
    memberships = ResearchUser.query.all()
    mem_map     = {}
    for m in memberships:
        mem_map.setdefault(m.research_id, []).append(m.user_id)

    # KPI globali di sistema
    kpi = dict(
        total_users      = User.query.count(),
        total_researches = Research.query.count(),
        total_properties = Property.query.count(),
        total_contacts   = Contact.query.count(),
        total_logs       = ActivityLog.query.count(),
    )
    return render_template('admin.html', users=users, logs=logs,
                           researches=researches, mem_map=mem_map, kpi=kpi)

# ── CREA UTENTE ───────────────────────────────────────────────────────────────
@admin_bp.route('/users/new', methods=['POST'])
@login_required
@admin_required
@limiter.limit("20 per minute")
def new_user():
    email = request.form.get('email', '').strip()
    if User.query.filter_by(email=email).first():
        flash('Email già in uso.', 'error')
        return redirect(url_for('admin.dashboard'))
    user = User(
        full_name     = request.form.get('full_name', '').strip(),
        email         = email,
        role          = request.form.get('role', 'viewer'),
        password_hash = generate_password_hash(request.form.get('password', 'changeme'))
    )
    db.session.add(user)
    db.session.commit()
    flash(f'Utente {user.full_name} creato.', 'success')
    return redirect(url_for('admin.dashboard'))

# ── MODIFICA UTENTE ───────────────────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
@limiter.limit("20 per minute")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Non puoi modificare il tuo stesso account da qui. Usa "Il mio profilo".', 'error')
        return redirect(url_for('admin.dashboard'))
    new_email = request.form.get('email', '').strip()
    existing  = User.query.filter_by(email=new_email).first()
    if existing and existing.id != user_id:
        flash('Email già usata da un altro utente.', 'error')
        return redirect(url_for('admin.dashboard'))
    user.full_name = request.form.get('full_name', '').strip() or user.full_name
    user.email     = new_email or user.email
    user.role      = request.form.get('role', user.role)
    new_pw         = request.form.get('new_password', '').strip()
    if new_pw:
        if len(new_pw) < 6:
            flash('Password troppo corta (min. 6 caratteri).', 'error')
            return redirect(url_for('admin.dashboard'))
        user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    flash(f'Utente {user.full_name} aggiornato.', 'success')
    return redirect(url_for('admin.dashboard'))

# ── ELIMINA UTENTE ────────────────────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
@limiter.limit("20 per minute")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Non puoi eliminare il tuo stesso account.', 'error')
        return redirect(url_for('admin.dashboard'))
    name = user.full_name
    ResearchUser.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f'Utente {name} eliminato.', 'success')
    return redirect(url_for('admin.dashboard'))

# ── CAMBIA RUOLO (shortcut) ───────────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    user.role = request.form.get('role', user.role)
    db.session.commit()
    flash(f'Ruolo di {user.full_name} aggiornato.', 'success')
    return redirect(url_for('admin.dashboard'))

# ── ASSEGNA UTENTE A RICERCA ──────────────────────────────────────────────────
@admin_bp.route('/research/<int:research_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_user(research_id):
    user_id = int(request.form.get('user_id'))
    if not ResearchUser.query.filter_by(research_id=research_id, user_id=user_id).first():
        db.session.add(ResearchUser(research_id=research_id, user_id=user_id))
        db.session.commit()
        flash('Utente aggiunto alla ricerca.', 'success')
    return redirect(url_for('admin.dashboard'))

# ── RIMUOVI UTENTE DA RICERCA ─────────────────────────────────────────────────
@admin_bp.route('/research/<int:research_id>/remove/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_user(research_id, user_id):
    mem = ResearchUser.query.filter_by(research_id=research_id, user_id=user_id).first()
    if mem:
        db.session.delete(mem)
        db.session.commit()
        flash('Utente rimosso dalla ricerca.', 'success')
    return redirect(url_for('admin.dashboard'))
