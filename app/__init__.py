from flask import Flask, session, send_from_directory, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from pathlib import Path

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf    = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
migrate = Migrate()

def create_app(env='development'):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from config import config_map
    cfg = config_map.get(env, config_map['default'])
    app.config.from_object(cfg)

    # Fail-fast: in produzione SECRET_KEY è obbligatoria
    if env == 'production' and not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            "SECRET_KEY environment variable is required in production")

    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    from .models import User, Research, ResearchUser, Property, Notification

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.context_processor
    def inject_globals():
        ctx = {
            'active_research':  None,
            'badge_da_valutare': 0,
            'unread_notifications': 0,
            'app_version': '0.2.0'
        }
        if current_user.is_authenticated:
            research_id = session.get('active_research_id')
            if not research_id:
                m = ResearchUser.query.filter_by(user_id=current_user.id).first()
                if m:
                    session['active_research_id'] = m.research_id
                    research_id = m.research_id
            if research_id:
                r = Research.query.get(research_id)
                ctx['active_research'] = r
                ctx['badge_da_valutare'] = Property.query.filter_by(
                    research_id=research_id, status='Da valutare').count()
            ctx['unread_notifications'] = Notification.query.filter_by(
                user_id=current_user.id, is_read=False).count()
        return ctx

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(403)
    def forbidden(e):    return render_template('errors/403.html'), 403
    @app.errorhandler(404)
    def not_found(e):    return render_template('errors/404.html'), 404
    @app.errorhandler(500)
    def server_error(e): return render_template('errors/500.html'), 500

    from .routes.auth          import auth_bp
    from .routes.main          import main_bp
    from .routes.properties    import properties_bp
    from .routes.contacts      import contacts_bp
    from .routes.admin         import admin_bp
    from .routes.researches    import researches_bp
    from .routes.notifications import notifications_bp

    for bp in [auth_bp, main_bp, properties_bp, contacts_bp,
               admin_bp, researches_bp, notifications_bp]:
        app.register_blueprint(bp)

    return app
