from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, logout_user, login_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User, ResearchUser, Research
from app import db, limiter

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Email o password non corretti.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_name':
            new_name = request.form.get('full_name', '').strip()
            if new_name:
                current_user.full_name = new_name
                db.session.commit()
                flash('Nome aggiornato con successo.', 'success')
        elif action == 'change_password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            if not check_password_hash(current_user.password_hash, old_pw):
                flash('Password attuale non corretta.', 'error')
            elif len(new_pw) < 6:
                flash('La nuova password deve avere almeno 6 caratteri.', 'error')
            else:
                current_user.password_hash = generate_password_hash(new_pw)
                db.session.commit()
                flash('Password cambiata con successo.', 'success')
        return redirect(url_for('auth.profile'))

    # FIX: query diretta per evitare cache SQLAlchemy
    memberships = ResearchUser.query.filter_by(user_id=current_user.id).all()
    researches  = [Research.query.get(m.research_id) for m in memberships]
    researches  = [r for r in researches if r]  # filtra eventuali None

    return render_template('profile.html', researches=researches)
