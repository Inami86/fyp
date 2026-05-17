from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Notification

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def list_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
                               .order_by(Notification.created_at.desc())\
                               .limit(60).all()
    # Segna tutte come lette all'apertura della pagina
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@notifications_bp.route('/mark-read', methods=['POST'])
@login_required
def mark_read():
    notif_id = request.json.get('id')
    if notif_id:
        n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
        if n: n.is_read = True; db.session.commit()
    return jsonify({'ok': True})

@notifications_bp.route('/api/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})
