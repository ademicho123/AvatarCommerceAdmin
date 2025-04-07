import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'development-admin-key')
    DEBUG = os.environ.get('ADMIN_DEBUG', 'False').lower() == 'true'
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost/avatarcommerce'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Admin configuration
    FLASK_ADMIN_SWATCH = 'cerulean'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)