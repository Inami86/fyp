import os
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
    SECRET_KEY = os.environ.get('SECRET_KEY', '')


config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
