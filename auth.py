from functools import wraps
from flask import session, redirect, url_for, request
from models import AdminUser

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def authenticate_admin(username, password):
    """Authenticate admin user"""
    user = AdminUser.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        return user
    
    return None

def is_admin_authenticated():
    """Check if admin is authenticated"""
    return 'admin_user_id' in session