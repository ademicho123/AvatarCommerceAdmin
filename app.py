from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
from datetime import datetime, timedelta
import os
from models import db, AdminUser, InfluencerModel, FanModel, ChatInteractionModel, AffiliateModel
from utils.auth import login_required, admin_required
from config import Config
from supabase_client import sync_data_from_supabase
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = AdminUser.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username
            session['is_super_admin'] = user.is_super_admin
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=12)
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard route
@app.route('/')
@login_required
def dashboard():
    # Basic metrics
    influencer_count = InfluencerModel.query.count()
    fan_count = FanModel.query.count()
    chat_count = ChatInteractionModel.query.count()
    affiliate_count = AffiliateModel.query.count()
    
    # Recent chats
    recent_chats = db.session.query(
        ChatInteractionModel,
        InfluencerModel.username.label('influencer_name')
    ).join(
        InfluencerModel, ChatInteractionModel.influencer_id == InfluencerModel.id
    ).order_by(
        ChatInteractionModel.created_at.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html', 
                          influencer_count=influencer_count,
                          fan_count=fan_count,
                          chat_count=chat_count,
                          affiliate_count=affiliate_count,
                          recent_chats=recent_chats)

# Influencer routes
@app.route('/influencers')
@login_required
def influencers():
    influencers = InfluencerModel.query.all()
    return render_template('influencers.html', influencers=influencers)

@app.route('/influencers/new', methods=['GET', 'POST'])
@login_required
def new_influencer():
    if request.method == 'POST':
        # Create new influencer
        try:
            influencer = InfluencerModel(
                id=str(uuid.uuid4()),
                username=request.form.get('username'),
                email=request.form.get('email'),
                bio=request.form.get('bio'),
                heygen_avatar_id=request.form.get('heygen_avatar_id'),
                voice_id=request.form.get('voice_id'),
                affiliate_id=request.form.get('affiliate_id'),
                chat_page_url=request.form.get('chat_page_url')
            )
            
            db.session.add(influencer)
            db.session.commit()
            flash('Influencer created successfully', 'success')
            return redirect(url_for('influencers'))
        except Exception as e:
            flash(f'Error creating influencer: {str(e)}', 'danger')
    
    return render_template('influencer_form.html', influencer=None)

@app.route('/influencers/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_influencer(id):
    influencer = InfluencerModel.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            influencer.username = request.form.get('username')
            influencer.email = request.form.get('email')
            influencer.bio = request.form.get('bio')
            influencer.heygen_avatar_id = request.form.get('heygen_avatar_id')
            influencer.voice_id = request.form.get('voice_id')
            influencer.affiliate_id = request.form.get('affiliate_id')
            influencer.chat_page_url = request.form.get('chat_page_url')
            
            db.session.commit()
            flash('Influencer updated successfully', 'success')
            return redirect(url_for('influencers'))
        except Exception as e:
            flash(f'Error updating influencer: {str(e)}', 'danger')
    
    return render_template('influencer_form.html', influencer=influencer)

@app.route('/influencers/delete/<string:id>', methods=['POST'])
@login_required
def delete_influencer(id):
    influencer = InfluencerModel.query.get_or_404(id)
    
    try:
        db.session.delete(influencer)
        db.session.commit()
        flash('Influencer deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting influencer: {str(e)}', 'danger')
    
    return redirect(url_for('influencers'))

# Fan routes
@app.route('/fans')
@login_required
def fans():
    fans = FanModel.query.all()
    return render_template('fans.html', fans=fans)

@app.route('/fans/new', methods=['GET', 'POST'])
@login_required
def new_fan():
    if request.method == 'POST':
        try:
            fan = FanModel(
                id=str(uuid.uuid4()),
                username=request.form.get('username'),
                email=request.form.get('email')
            )
            
            db.session.add(fan)
            db.session.commit()
            flash('Fan created successfully', 'success')
            return redirect(url_for('fans'))
        except Exception as e:
            flash(f'Error creating fan: {str(e)}', 'danger')
    
    return render_template('fan_form.html', fan=None)

@app.route('/fans/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_fan(id):
    """Edit a fan"""
    fan = FanModel.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update fan data
            fan.username = request.form.get('username')
            fan.email = request.form.get('email')
            fan.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Fan updated successfully', 'success')
            return redirect(url_for('fans'))
        except Exception as e:
            flash(f'Error updating fan: {str(e)}', 'danger')
    
    return render_template('fan_form.html', fan=fan)

@app.route('/fans/delete/<string:id>', methods=['POST'])
@login_required
def delete_fan(id):
    """Delete a fan"""
    fan = FanModel.query.get_or_404(id)
    
    try:
        db.session.delete(fan)
        db.session.commit()
        flash('Fan deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting fan: {str(e)}', 'danger')
    
    return redirect(url_for('fans'))

# Chat interactions
@app.route('/chats')
@login_required
def chats():
    chats = db.session.query(
        ChatInteractionModel,
        InfluencerModel.username.label('influencer_name'),
        FanModel.username.label('fan_name')
    ).join(
        InfluencerModel, ChatInteractionModel.influencer_id == InfluencerModel.id
    ).outerjoin(
        FanModel, ChatInteractionModel.fan_id == FanModel.id
    ).order_by(
        ChatInteractionModel.created_at.desc()
    ).all()
    
    return render_template('chats.html', chats=chats)

# Affiliate routes
@app.route('/affiliates')
@login_required
def affiliates():
    affiliates = db.session.query(
        AffiliateModel,
        InfluencerModel.username.label('influencer_name')
    ).join(
        InfluencerModel, AffiliateModel.influencer_id == InfluencerModel.id
    ).all()
    
    return render_template('affiliates.html', affiliates=affiliates)

@app.route('/affiliates/new', methods=['GET', 'POST'])
@login_required
def new_affiliate():
    if request.method == 'POST':
        try:
            affiliate = AffiliateModel(
                id=str(uuid.uuid4()),
                influencer_id=request.form.get('influencer_id'),
                platform=request.form.get('platform'),
                affiliate_id=request.form.get('affiliate_id')
            )
            
            db.session.add(affiliate)
            db.session.commit()
            flash('Affiliate link created successfully', 'success')
            return redirect(url_for('affiliates'))
        except Exception as e:
            flash(f'Error creating affiliate link: {str(e)}', 'danger')
    
    influencers = InfluencerModel.query.all()
    return render_template('affiliate_form.html', affiliate=None, influencers=influencers)
@app.route('/affiliates/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_affiliate(id):
    """Edit an affiliate link"""
    affiliate = AffiliateModel.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update affiliate data
            affiliate.influencer_id = request.form.get('influencer_id')
            affiliate.platform = request.form.get('platform')
            affiliate.affiliate_id = request.form.get('affiliate_id')
            affiliate.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Affiliate link updated successfully', 'success')
            return redirect(url_for('affiliates'))
        except Exception as e:
            flash(f'Error updating affiliate link: {str(e)}', 'danger')
    
    influencers = InfluencerModel.query.all()
    return render_template('affiliate_form.html', affiliate=affiliate, influencers=influencers)

@app.route('/affiliates/delete/<string:id>', methods=['POST'])
@login_required
def delete_affiliate(id):
    """Delete an affiliate link"""
    affiliate = AffiliateModel.query.get_or_404(id)
    
    try:
        db.session.delete(affiliate)
        db.session.commit()
        flash('Affiliate link deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting affiliate link: {str(e)}', 'danger')
    
    return redirect(url_for('affiliates'))

# Admin user management (Super Admin only)
@app.route('/admin-users')
@login_required
@admin_required
def admin_users():
    admins = AdminUser.query.all()
    return render_template('admin_users.html', admins=admins)

@app.route('/admin-users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_admin():
    if request.method == 'POST':
        try:
            admin = AdminUser(
                username=request.form.get('username'),
                email=request.form.get('email'),
                password_hash=generate_password_hash(request.form.get('password')),
                is_super_admin='is_super_admin' in request.form
            )
            
            db.session.add(admin)
            db.session.commit()
            flash('Admin user created successfully', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error creating admin user: {str(e)}', 'danger')
    
    return render_template('admin_form.html', admin=None)

@app.route('/admin-users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_admin(id):
    """Edit an admin user"""
    admin = AdminUser.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update admin data
            admin.username = request.form.get('username')
            admin.email = request.form.get('email')
            
            # Only update password if provided
            password = request.form.get('password')
            if password and password.strip():
                admin.password_hash = generate_password_hash(password)
            
            # Update super admin status if checkbox is present
            admin.is_super_admin = 'is_super_admin' in request.form
            
            db.session.commit()
            flash('Admin user updated successfully', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Error updating admin: {str(e)}', 'danger')
    
    return render_template('admin_form.html', admin=admin)

@app.route('/admin-users/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_admin(id):
    """Delete an admin user"""
    # Prevent deleting self
    if id == session.get('admin_user_id'):
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin_users'))
    
    admin = AdminUser.query.get_or_404(id)
    
    try:
        db.session.delete(admin)
        db.session.commit()
        flash('Admin user deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting admin: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users'))

# Supabase sync route
@app.route('/sync-supabase')
@login_required
@admin_required
def sync_supabase():
    try:
        models = {
            'influencers': InfluencerModel,
            'fans': FanModel,
            'chat_interactions': ChatInteractionModel,
            'affiliate_links': AffiliateModel
        }
        
        success = sync_data_from_supabase(db, models)
        
        if success:
            flash('Data synchronized successfully from Supabase', 'success')
        else:
            flash('Error synchronizing data from Supabase', 'danger')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# Initialize the scheduler
scheduler = BackgroundScheduler()

def scheduled_sync_job():
    """Function to run the Supabase sync on schedule"""
    with app.app_context():
        try:
            models = {
                'influencers': InfluencerModel,
                'fans': FanModel,
                'chat_interactions': ChatInteractionModel,
                'affiliate_links': AffiliateModel
            }
            
            success = sync_data_from_supabase(db, models)
            
            if success:
                print(f"Scheduled sync completed successfully at {datetime.utcnow()}")
            else:
                print(f"Scheduled sync failed at {datetime.utcnow()}")
        except Exception as e:
            print(f"Error in scheduled sync: {str(e)}")

# Add the job to the scheduler
scheduler.add_job(
    func=scheduled_sync_job,
    trigger=IntervalTrigger(hours=1),
    id='supabase_sync_job',
    name='Sync data from Supabase every hour',
    replace_existing=True
)

# Start the scheduler
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if we need to create a default admin
        if not AdminUser.query.first():
            from werkzeug.security import generate_password_hash
            admin_user = AdminUser(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_super_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user: admin/admin123")
    
    app.run(debug=True, port=5001)