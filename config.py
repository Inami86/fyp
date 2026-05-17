import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Carica .env se presente
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass  # python-dotenv non installato, si usano le variabili d'ambiente di sistema


class Config:
    SECRET_KEY           = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER        = str(BASE_DIR / 'app' / 'uploads')
    MAX_CONTENT_LENGTH   = 16 * 1024 * 1024  # 16 MB
    APP_VERSION          = '0.0.6'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{BASE_DIR / 'instance' / 'fyp.sqlite'}"
    )


class ProductionConfig(Config):
    DEBUG = False
    _db_url = os.environ.get('DATABASE_URL', '')
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'connect_args': {'sslmode': 'prefer'}
    }
    # SECRET_KEY validata in create_app() per evitare KeyError all'import
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    UPLOAD_FOLDER = str(BASE_DIR / 'app' / 'uploads')


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
