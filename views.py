from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, url_for
from wtforms import form, fields

class BaseAuthModelView(ModelView):
    def is_accessible(self):
        return 'admin_user_id' in session
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

class InfluencerView(BaseAuthModelView):
    column_list = ['username', 'email', 'heygen_avatar_id', 'created_at']
    column_searchable_list = ['username', 'email']
    column_sortable_list = ['username', 'email', 'created_at']
    column_filters = ['created_at']
    
    # Fix: Convert tuple to dictionary in form_columns
    form_columns = {
        'username': fields.StringField('Username'),
        'email': fields.StringField('Email'),
        'heygen_avatar_id': fields.StringField('HeyGen Avatar ID'),
        'voice_id': fields.StringField('Voice ID'),
        'affiliate_id': fields.StringField('Affiliate ID'),
        'chat_page_url': fields.StringField('Chat Page URL'),
        'bio': fields.TextAreaField('Bio')
    }

class FanView(BaseAuthModelView):
    column_list = ['username', 'email', 'created_at']
    column_searchable_list = ['username', 'email']
    column_sortable_list = ['username', 'email', 'created_at']
    column_filters = ['created_at']
    
    # Fix: Convert tuple to dictionary in form_columns
    form_columns = {
        'username': fields.StringField('Username'),
        'email': fields.StringField('Email')
    }

class ChatInteractionView(BaseAuthModelView):
    column_list = ['influencer.username', 'fan.username', 'user_message', 'product_recommendations', 'created_at']
    column_searchable_list = ['user_message', 'bot_response']
    column_sortable_list = ['created_at']
    column_filters = ['created_at', 'product_recommendations']
    
    # Using list format instead of dict for form_columns
    form_columns = ['influencer', 'fan', 'user_message', 'bot_response', 'product_recommendations']

class AffiliateView(BaseAuthModelView):
    column_list = ['influencer.username', 'platform', 'affiliate_id', 'created_at']
    column_searchable_list = ['platform', 'affiliate_id']
    column_sortable_list = ['platform', 'created_at']
    column_filters = ['platform', 'created_at']
    
    # Fix: Using list format instead of tuple for form_columns
    form_columns = ['influencer', 'platform', 'affiliate_id']