from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class AdminUser(db.Model):
    """Admin users for the admin panel"""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'

class InfluencerModel(db.Model):
    """Model for influencers - maps to the main app's influencers table"""
    __tablename__ = 'influencers'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    heygen_avatar_id = db.Column(db.String(64))
    original_asset_path = db.Column(db.String(256))
    voice_id = db.Column(db.String(64))
    affiliate_id = db.Column(db.String(64))
    chat_page_url = db.Column(db.String(128))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    
    chat_interactions = db.relationship('ChatInteractionModel', back_populates='influencer')
    affiliate_links = db.relationship('AffiliateModel', back_populates='influencer')
    
    def __repr__(self):
        return f'<Influencer {self.username}>'

class FanModel(db.Model):
    """Model for fans - maps to the main app's fans table"""
    __tablename__ = 'fans'
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    
    chat_interactions = db.relationship('ChatInteractionModel', back_populates='fan')
    
    def __repr__(self):
        return f'<Fan {self.username}>'

class ChatInteractionModel(db.Model):
    """Model for chat interactions - maps to the main app's chat_interactions table"""
    __tablename__ = 'chat_interactions'
    
    id = db.Column(db.String(36), primary_key=True)
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'))
    fan_id = db.Column(db.String(36), db.ForeignKey('fans.id'), nullable=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    product_recommendations = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    
    influencer = db.relationship('InfluencerModel', back_populates='chat_interactions')
    fan = db.relationship('FanModel', back_populates='chat_interactions', nullable=True)
    
    def __repr__(self):
        return f'<ChatInteraction {self.id}>'

class AffiliateModel(db.Model):
    """Model for affiliate links - maps to the main app's affiliate_links table"""
    __tablename__ = 'affiliate_links'
    
    id = db.Column(db.String(36), primary_key=True)
    influencer_id = db.Column(db.String(36), db.ForeignKey('influencers.id'))
    platform = db.Column(db.String(64), nullable=False)
    affiliate_id = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    
    influencer = db.relationship('InfluencerModel', back_populates='affiliate_links')
    
    def __repr__(self):
        return f'<AffiliateLink {self.platform}:{self.affiliate_id}>'