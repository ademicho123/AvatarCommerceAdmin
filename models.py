from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class AdminUser(db.Model):
    """Admin users for the admin panel"""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'

class InfluencerModel(db.Model):
    """Model for influencers"""
    __tablename__ = 'influencers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False, default='')
    heygen_avatar_id = db.Column(db.String(64), nullable=True)
    original_asset_path = db.Column(db.String(256), nullable=True)
    voice_id = db.Column(db.String(64), nullable=True)
    affiliate_id = db.Column(db.String(64), nullable=True)
    chat_page_url = db.Column(db.String(128), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    promotion_settings = db.relationship('InfluencerPromotionSettingsModel', back_populates='influencer', uselist=False)
    conversation_counters = db.relationship('ConversationCounterModel', back_populates='influencer', lazy='dynamic')
    products = db.relationship('InfluencerProductModel', back_populates='influencer', lazy='dynamic')

    
    chat_interactions = db.relationship('ChatInteractionModel', back_populates='influencer', lazy='dynamic')
    affiliate_links = db.relationship('AffiliateModel', back_populates='influencer', lazy='dynamic')
    
    def __repr__(self):
        return f'<Influencer {self.username}>'

class FanModel(db.Model):
    """Model for fans"""
    __tablename__ = 'fans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversation_counters = db.relationship('ConversationCounterModel', back_populates='fan', lazy='dynamic')
    
    chat_interactions = db.relationship('ChatInteractionModel', back_populates='fan', lazy='dynamic')
    
    def __repr__(self):
        return f'<Fan {self.username}>'

class ChatInteractionModel(db.Model):
    """Model for chat interactions"""
    __tablename__ = 'chat_interactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'))
    fan_id = db.Column(db.String(36), db.ForeignKey('fans.id'), nullable=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    product_recommendations = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    influencer = db.relationship('InfluencerModel', back_populates='chat_interactions')
    fan = db.relationship('FanModel', back_populates='chat_interactions')
    
    def __repr__(self):
        return f'<ChatInteraction {self.id}>'

class AffiliateModel(db.Model):
    """Model for affiliate links"""
    __tablename__ = 'affiliate_links'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'))
    platform = db.Column(db.String(64), nullable=False)
    affiliate_id = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    influencer = db.relationship('InfluencerModel', back_populates='affiliate_links')
    
    def __repr__(self):
        return f'<AffiliateLink {self.platform}:{self.affiliate_id}>'
    
class InfluencerPromotionSettingsModel(db.Model):
    """Model for influencer promotion settings"""
    __tablename__ = 'influencer_promotion_settings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'), nullable=False)
    promotion_frequency = db.Column(db.Integer, nullable=False, default=3)
    promote_at_end = db.Column(db.Boolean, nullable=False, default=False)
    default_product = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    influencer = db.relationship('InfluencerModel', back_populates='promotion_settings')
    
    def __repr__(self):
        return f'<PromotionSettings {self.id}>'

class ConversationCounterModel(db.Model):
    """Model for conversation counters between influencers and fans"""
    __tablename__ = 'conversation_counters'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'), nullable=False)
    fan_id = db.Column(db.String(36), db.ForeignKey('fans.id'), nullable=False)
    message_count = db.Column(db.Integer, nullable=False, default=0)
    last_promotion_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    influencer = db.relationship('InfluencerModel', back_populates='conversation_counters')
    fan = db.relationship('FanModel', back_populates='conversation_counters')
    
    def __repr__(self):
        return f'<ConversationCounter {self.influencer_id}:{self.fan_id}>'

class InfluencerProductModel(db.Model):
    """Model for influencer products to promote"""
    __tablename__ = 'influencer_products'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'), nullable=False)
    product_name = db.Column(db.String(256), nullable=False)
    product_query = db.Column(db.String(256), nullable=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    influencer = db.relationship('InfluencerModel', back_populates='products')
    
    def __repr__(self):
        return f'<InfluencerProduct {self.product_name}>'