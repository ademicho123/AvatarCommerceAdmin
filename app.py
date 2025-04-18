from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
from datetime import datetime, timedelta
import os
from models import db, AdminUser, InfluencerModel, FanModel, ChatInteractionModel, AffiliateModel, InfluencerProductModel, InfluencerPromotionSettingsModel, ConversationCounterModel
import requests
from werkzeug.utils import secure_filename
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
    product_count = InfluencerProductModel.query.count()
    
    # Recent chats
    recent_chats = db.session.query(
        ChatInteractionModel,
        InfluencerModel.username.label('influencer_name')
    ).join(
        InfluencerModel, ChatInteractionModel.influencer_id == InfluencerModel.id
    ).order_by(
        ChatInteractionModel.created_at.desc()
    ).limit(5).all()
    
    # Get promotions data
    promotions_count = ChatInteractionModel.query.filter_by(product_recommendations=True).count()
    promotion_rate = 0
    if chat_count > 0:
        promotion_rate = (promotions_count / chat_count) * 100
    
    # Top influencers by chat count
    top_influencers = db.session.query(
        InfluencerModel.username,
        db.func.count(ChatInteractionModel.id).label('chat_count')
    ).join(
        ChatInteractionModel, InfluencerModel.id == ChatInteractionModel.influencer_id
    ).group_by(
        InfluencerModel.id
    ).order_by(
        db.func.count(ChatInteractionModel.id).desc()
    ).limit(5).all()
    
    # Get monthly chat data for the chart
    current_year = datetime.utcnow().year
    monthly_chats = []
    monthly_promotions = []
    
    for month in range(1, 13):
        # Count chats for this month
        month_chats = ChatInteractionModel.query.filter(
            db.extract('year', ChatInteractionModel.created_at) == current_year,
            db.extract('month', ChatInteractionModel.created_at) == month
        ).count()
        
        # Count promotions for this month
        month_promotions = ChatInteractionModel.query.filter(
            db.extract('year', ChatInteractionModel.created_at) == current_year,
            db.extract('month', ChatInteractionModel.created_at) == month,
            ChatInteractionModel.product_recommendations == True
        ).count()
        
        monthly_chats.append(month_chats)
        monthly_promotions.append(month_promotions)
    
    return render_template('dashboard.html', 
                          influencer_count=influencer_count,
                          fan_count=fan_count,
                          chat_count=chat_count,
                          affiliate_count=affiliate_count,
                          product_count=product_count,
                          recent_chats=recent_chats,
                          promotions_count=promotions_count,
                          promotion_rate=round(promotion_rate, 2),
                          top_influencers=top_influencers,
                          monthly_chats=monthly_chats,
                          monthly_promotions=monthly_promotions,
                          datetime=datetime)

# Influencer routes
@app.route('/influencers')
@login_required
def influencers():
    influencers = InfluencerModel.query.all()
    return render_template('influencers.html', influencers=influencers)

# Update the influencer form to include avatar and chatbot integration
@app.route('/influencers/new', methods=['GET', 'POST'])
@login_required
def new_influencer():
    if request.method == 'POST':
        try:
            # Generate unique ID
            influencer_id = str(uuid.uuid4())
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password', '')
            bio = request.form.get('bio')
            affiliate_id = request.form.get('affiliate_id')
            
            # Hash password if provided
            password_hash = ''
            if password:
                password_hash = generate_password_hash(password)
            
            # Create influencer in local database
            influencer = InfluencerModel(
                id=influencer_id,
                username=username,
                email=email,
                password_hash=password_hash,
                bio=bio,
                affiliate_id=affiliate_id,
                chat_page_url=f"/chat/{username}"
            )
            
            # Process avatar if file is uploaded
            if 'avatar_file' in request.files and request.files['avatar_file'].filename:
                avatar_file = request.files['avatar_file']
                
                try:
                    # Save file temporarily
                    temp_filename = secure_filename(avatar_file.filename)
                    avatar_path = os.path.join('temp', temp_filename)
                    os.makedirs('temp', exist_ok=True)
                    avatar_file.save(avatar_path)
                    
                    # Get configuration
                    from config import Config
                    heygen_api_key = Config.HEYGEN_API_KEY
                    
                    if heygen_api_key:
                        # Call HeyGen API to create avatar
                        with open(avatar_path, 'rb') as file:
                            file_content = file.read()
                        
                        # Upload to HeyGen API
                        headers = {
                            "X-Api-Key": heygen_api_key,
                            "Accept": "application/json"
                        }
                        
                        # Store file info
                        influencer.original_asset_path = avatar_path
                        
                        # Use the avatar ID from the first available avatar
                        # In a real implementation, you'd create a new avatar
                        test_response = requests.get(
                            "https://api.heygen.com/v2/avatars",
                            headers=headers,
                            timeout=10
                        )
                        
                        if test_response.status_code == 200:
                            avatars = test_response.json().get("data", {}).get("avatars", [])
                            if avatars:
                                avatar_id = avatars[0].get("avatar_id")
                                influencer.heygen_avatar_id = avatar_id
                                flash(f'Avatar assigned with ID: {avatar_id}', 'success')
                            else:
                                flash('No avatars available in HeyGen account', 'warning')
                        else:
                            flash(f'Error connecting to HeyGen API: {test_response.text}', 'warning')
                    else:
                        flash('HeyGen API key not configured', 'warning')
                    
                    # Clean up
                    os.remove(avatar_path)
                    
                except Exception as avatar_error:
                    flash(f'Error processing avatar: {str(avatar_error)}', 'warning')
            
            db.session.add(influencer)
            
            # Create default promotion settings
            settings = InfluencerPromotionSettingsModel(
                id=str(uuid.uuid4()),
                influencer_id=influencer_id,
                promotion_frequency=3,
                promote_at_end=False
            )
            db.session.add(settings)
            
            # Add affiliate link if provided
            if affiliate_id:
                affiliate = AffiliateModel(
                    id=str(uuid.uuid4()),
                    influencer_id=influencer_id,
                    platform="amazon",
                    affiliate_id=affiliate_id
                )
                db.session.add(affiliate)
            
            db.session.commit()
            flash('Influencer created successfully', 'success')
            return redirect(url_for('influencers'))
        except Exception as e:
            db.session.rollback()  # Add this to rollback any partial changes
            flash(f'Error creating influencer: {str(e)}', 'danger')
    
    # Make sure there's a return statement for the GET case
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
            'affiliate_links': AffiliateModel,
            'promotion_settings': InfluencerPromotionSettingsModel,
            'conversation_counters': ConversationCounterModel,
            'influencer_products': InfluencerProductModel
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
                'affiliate_links': AffiliateModel,
                'promotion_settings': InfluencerPromotionSettingsModel,
                'conversation_counters': ConversationCounterModel,
                'influencer_products': InfluencerProductModel
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

@app.route('/products')
@login_required
def products():
    """List all products"""
    products = db.session.query(
        InfluencerProductModel,
        InfluencerModel.username.label('influencer_name')
    ).join(
        InfluencerModel, InfluencerProductModel.influencer_id == InfluencerModel.id
    ).all()
    
    return render_template('products.html', products=products)

@app.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Create a new product"""
    if request.method == 'POST':
        try:
            # Get form data
            influencer_id = request.form.get('influencer_id')
            product_name = request.form.get('product_name')
            product_query = request.form.get('product_query')
            is_default = 'is_default' in request.form
            
            # Check if this product should be the default
            if is_default:
                # Unset any existing default products for this influencer
                existing_defaults = InfluencerProductModel.query.filter_by(
                    influencer_id=influencer_id,
                    is_default=True
                ).all()
                
                for product in existing_defaults:
                    product.is_default = False
                
                # Also update the promotion settings
                settings = InfluencerPromotionSettingsModel.query.filter_by(
                    influencer_id=influencer_id
                ).first()
                
                if settings:
                    settings.default_product = product_query
                else:
                    # Create new settings
                    settings = InfluencerPromotionSettingsModel(
                        id=str(uuid.uuid4()),
                        influencer_id=influencer_id,
                        promotion_frequency=3,
                        promote_at_end=False,
                        default_product=product_query
                    )
                    db.session.add(settings)
            
            # Create new product
            product = InfluencerProductModel(
                id=str(uuid.uuid4()),
                influencer_id=influencer_id,
                product_name=product_name,
                product_query=product_query,
                is_default=is_default
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('Product created successfully', 'success')
            return redirect(url_for('products'))
        except Exception as e:
            flash(f'Error creating product: {str(e)}', 'danger')
    
    influencers = InfluencerModel.query.all()
    return render_template('product_form.html', product=None, influencers=influencers)

# Promotion settings routes
@app.route('/influencers/<string:id>/promotion-settings', methods=['GET', 'POST'])
@login_required
def promotion_settings(id):
    """Manage promotion settings for an influencer"""
    influencer = InfluencerModel.query.get_or_404(id)
    settings = InfluencerPromotionSettingsModel.query.filter_by(influencer_id=id).first()
    products = InfluencerProductModel.query.filter_by(influencer_id=id).all()
    counters = ConversationCounterModel.query.filter_by(influencer_id=id).all()
    
    if request.method == 'POST':
        try:
            # Get form data
            promotion_frequency = int(request.form.get('promotion_frequency', 3))
            promote_at_end = 'promote_at_end' in request.form
            default_product = request.form.get('default_product')
            
            if settings:
                # Update existing settings
                settings.promotion_frequency = promotion_frequency
                settings.promote_at_end = promote_at_end
                settings.default_product = default_product
                settings.updated_at = datetime.utcnow()
            else:
                # Create new settings
                settings = InfluencerPromotionSettingsModel(
                    id=str(uuid.uuid4()),
                    influencer_id=id,
                    promotion_frequency=promotion_frequency,
                    promote_at_end=promote_at_end,
                    default_product=default_product
                )
                db.session.add(settings)
            
            # Update the default product flag
            if default_product:
                # First, unset all default products
                for product in products:
                    product.is_default = False
                
                # Set the selected product as default
                matching_product = next((p for p in products if p.product_query == default_product), None)
                if matching_product:
                    matching_product.is_default = True
            
            db.session.commit()
            
            flash('Promotion settings updated successfully', 'success')
            return redirect(url_for('promotion_settings', id=id))
        except Exception as e:
            flash(f'Error updating promotion settings: {str(e)}', 'danger')
    
    return render_template('promotion_settings.html', 
                          influencer=influencer, 
                          settings=settings, 
                          products=products,
                          counters=counters)

@app.route('/conversation-counters/reset/<string:id>', methods=['POST'])
@login_required
def reset_counter(id):
    """Reset a conversation counter"""
    counter = ConversationCounterModel.query.get_or_404(id)
    influencer_id = counter.influencer_id
    
    try:
        counter.message_count = 0
        counter.last_promotion_at = None
        counter.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Conversation counter reset successfully', 'success')
    except Exception as e:
        flash(f'Error resetting counter: {str(e)}', 'danger')
    
    return redirect(url_for('promotion_settings', id=influencer_id))
  
@app.route('/products/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    """Edit a product"""
    product = InfluencerProductModel.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Get form data
            influencer_id = request.form.get('influencer_id')
            product_name = request.form.get('product_name')
            product_query = request.form.get('product_query')
            is_default = 'is_default' in request.form
            
            # Check if this product should be the default
            if is_default and not product.is_default:
                # Unset any existing default products for this influencer
                existing_defaults = InfluencerProductModel.query.filter_by(
                    influencer_id=influencer_id,
                    is_default=True
                ).all()
                
                for p in existing_defaults:
                    p.is_default = False
                
                # Also update the promotion settings
                settings = InfluencerPromotionSettingsModel.query.filter_by(
                    influencer_id=influencer_id
                ).first()
                
                if settings:
                    settings.default_product = product_query
                else:
                    # Create new settings
                    settings = InfluencerPromotionSettingsModel(
                        id=str(uuid.uuid4()),
                        influencer_id=influencer_id,
                        promotion_frequency=3,
                        promote_at_end=False,
                        default_product=product_query
                    )
                    db.session.add(settings)
            
            # Update product
            product.influencer_id = influencer_id
            product.product_name = product_name
            product.product_query = product_query
            product.is_default = is_default
            product.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash('Product updated successfully', 'success')
            return redirect(url_for('products'))
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'danger')
    
    influencers = InfluencerModel.query.all()
    return render_template('product_form.html', product=product, influencers=influencers)

@app.route('/products/delete/<string:id>', methods=['POST'])
@login_required
def delete_product(id):
    """Delete a product"""
    product = InfluencerProductModel.query.get_or_404(id)
    
    try:
        # If this is the default product, also update the promotion settings
        if product.is_default:
            settings = InfluencerPromotionSettingsModel.query.filter_by(
                influencer_id=product.influencer_id
            ).first()
            
            if settings and settings.default_product == product.product_query:
                settings.default_product = None
        
        db.session.delete(product)
        db.session.commit()
        
        flash('Product deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/products/<string:id>/set-default', methods=['GET'])
@login_required
def set_default_product(id):
    """Set a product as default"""
    product = InfluencerProductModel.query.get_or_404(id)
    
    try:
        # Unset any existing default products for this influencer
        existing_defaults = InfluencerProductModel.query.filter_by(
            influencer_id=product.influencer_id,
            is_default=True
        ).all()
        
        for p in existing_defaults:
            p.is_default = False
        
        # Set this product as default
        product.is_default = True
        
        # Also update the promotion settings
        settings = InfluencerPromotionSettingsModel.query.filter_by(
            influencer_id=product.influencer_id
        ).first()
        
        if settings:
            settings.default_product = product.product_query
        else:
            # Create new settings
            settings = InfluencerPromotionSettingsModel(
                id=str(uuid.uuid4()),
                influencer_id=product.influencer_id,
                promotion_frequency=3,
                promote_at_end=False,
                default_product=product.product_query
            )
            db.session.add(settings)
        
        db.session.commit()
        
        flash('Product set as default successfully', 'success')
    except Exception as e:
        flash(f'Error setting default product: {str(e)}', 'danger')
    
    return redirect(url_for('products'))

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