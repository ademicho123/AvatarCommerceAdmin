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
from sqlalchemy import func, desc
import json
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)
app.config['FLASK_ADMIN_TEMPLATE_MODE'] = 'bootstrap4'
app.config['FLASK_ADMIN_TEMPLATES_AUTO_RELOAD'] = True

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
            
        # Key metrics
        influencer_count = InfluencerModel.query.count()
        fan_count = FanModel.query.count()
        chat_count = ChatInteractionModel.query.count()
        product_rec_count = ChatInteractionModel.query.filter_by(product_recommendations=True).count()
        
        # Calculate product recommendation rate
        if chat_count > 0:
            product_rec_rate = (product_rec_count / chat_count) * 100
        else:
            product_rec_rate = 0
            
        # Activity over time (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_chats = db.session.query(
            func.date(ChatInteractionModel.created_at).label('date'),
            func.count().label('count')
        ).filter(ChatInteractionModel.created_at >= thirty_days_ago) \
         .group_by(func.date(ChatInteractionModel.created_at)) \
         .order_by(func.date(ChatInteractionModel.created_at)) \
         .all()
        
        # Format for chart
        dates = [d.date.strftime('%Y-%m-%d') for d in daily_chats]
        counts = [d.count for d in daily_chats]
        
        # Top influencers by chat volume
        top_influencers = db.session.query(
            InfluencerModel.username,
            func.count(ChatInteractionModel.id).label('chat_count')
        ).join(ChatInteractionModel, InfluencerModel.id == ChatInteractionModel.influencer_id) \
         .group_by(InfluencerModel.username) \
         .order_by(desc('chat_count')) \
         .limit(5) \
         .all()
            
        # Recent activity
        recent_chats = db.session.query(
            ChatInteractionModel,
            InfluencerModel.username.label('influencer_name'),
            FanModel.username.label('fan_name')
        ).join(InfluencerModel, ChatInteractionModel.influencer_id == InfluencerModel.id) \
         .outerjoin(FanModel, ChatInteractionModel.fan_id == FanModel.id) \
         .order_by(ChatInteractionModel.created_at.desc()) \
         .limit(10) \
         .all()
        
        return self.render('admin/index.html',
                          influencer_count=influencer_count,
                          fan_count=fan_count,
                          chat_count=chat_count,
                          product_rec_count=product_rec_count,
                          product_rec_rate=product_rec_rate,
                          dates_json=json.dumps(dates),
                          counts_json=json.dumps(counts),
                          top_influencers=top_influencers,
                          recent_chats=recent_chats)

# Initialize Flask-Admin
admin = Admin(
    app, 
    name='AvatarCommerce Admin', 
    template_mode='bootstrap4',
    index_view=MyAdminIndexView(name='Dashboard', template='admin/index.html', url='/')
)

# Add model views
admin.add_view(InfluencerView(InfluencerModel, db.session, name='Influencers', endpoint='influencermodel'))
admin.add_view(FanView(FanModel, db.session, name='Fans', endpoint='fanmodel'))
admin.add_view(ChatInteractionView(ChatInteractionModel, db.session, name='Chat Interactions', endpoint='chatinteractionmodel'))
admin.add_view(AffiliateView(AffiliateModel, db.session, name='Affiliate Links', endpoint='affiliatemodel'))

# Add analytics view with explicit endpoint name
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
        db.create_all()  # This creates all tables in the database
    app.run(debug=True, port=5001)