from flask import Flask, url_for, redirect, render_template, request, session
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from werkzeug.security import check_password_hash
import os
from datetime import datetime, timedelta

from models import db, AdminUser, InfluencerModel, FanModel, ChatInteractionModel, AffiliateModel
from auth import login_required, authenticate_admin
from dashboard import DashboardView, AnalyticsView
from views import InfluencerView, FanView, ChatInteractionView, AffiliateView
from config import Config

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create custom base model view with authentication
class AuthModelView(ModelView):
    def is_accessible(self):
        return 'admin_user_id' in session
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

# Create custom index view with authentication
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return super(MyAdminIndexView, self).index()

# Initialize Flask-Admin
admin = Admin(
    app, 
    name='AvatarCommerce Admin', 
    template_mode='bootstrap4',
    index_view=MyAdminIndexView(name='Dashboard', template='admin/index.html', url='/')
)

# Add model views
admin.add_view(InfluencerView(InfluencerModel, db.session, name='Influencers'))
admin.add_view(FanView(FanModel, db.session, name='Fans'))
admin.add_view(ChatInteractionView(ChatInteractionModel, db.session, name='Chat Interactions'))
admin.add_view(AffiliateView(AffiliateModel, db.session, name='Affiliate Links'))

# Add analytics view
admin.add_view(AnalyticsView(name='Analytics', endpoint='analytics'))

# Add login/logout links
admin.add_link(MenuLink(name='Logout', url='/logout'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = AdminUser.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=12)
            
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(url_for('admin.index'))
        else:
            error = 'Invalid credentials'
    
    return render_template('admin/login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('login'))

@app.route('/init-admin', methods=['GET'])
def init_admin():
    """Initialize the first admin user - ONLY FOR FIRST SETUP, THEN DISABLE!"""
    if os.environ.get('ALLOW_ADMIN_INIT') != 'true':
        return "Disabled for security. Set ALLOW_ADMIN_INIT=true to enable."
    
    if AdminUser.query.first() is not None:
        return "Admin users already exist."
    
    from werkzeug.security import generate_password_hash
    default_password = 'admin123'  # Change immediately after first login!
    admin_user = AdminUser(
        username='admin',
        password_hash=generate_password_hash(default_password),
        email='admin@example.com'
    )
    
    with app.app_context():
        db.session.add(admin_user)
        db.session.commit()
    
    return f"Admin user created with username 'admin' and password '{default_password}'. Please change the password immediately."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)  # Use a different port from your main app