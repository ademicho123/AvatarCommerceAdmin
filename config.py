import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'development-admin-key')
    DEBUG = os.environ.get('ADMIN_DEBUG', 'False').lower() == 'true'
    
    # Use SQLite for development
    SQLALCHEMY_DATABASE_URI = 'sqlite:///avatarcommerce.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Admin configuration
    FLASK_ADMIN_SWATCH = 'cerulean'
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)