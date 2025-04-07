from flask_admin.contrib.sqla import ModelView
from flask import session, redirect, url_for, request
from flask_admin import expose
from sqlalchemy import func
from wtforms import PasswordField

class AuthModelView(ModelView):
    """Base view with authentication"""
    def is_accessible(self):
        return 'admin_user_id' in session
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

class InfluencerView(AuthModelView):
    """Custom view for influencers"""
    column_list = ('id', 'username', 'email', 'affiliate_id', 'created_at', 'has_avatar', 'has_voice')
    column_searchable_list = ['username', 'email']
    column_filters = ['created_at', 'affiliate_id']
    column_sortable_list = ['username', 'email', 'created_at']
    column_formatters = {
        'has_avatar': lambda v, c, m, p: 'Yes' if m.heygen_avatar_id else 'No',
        'has_voice': lambda v, c, m, p: 'Yes' if m.voice_id else 'No'
    }
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'email': 'Email',
        'affiliate_id': 'Affiliate ID',
        'created_at': 'Created',
        'has_avatar': 'Has Avatar',
        'has_voice': 'Has Voice'
    }
    column_default_sort = ('created_at', True)
    
    # Custom fields for forms
    form_columns = ('username', 'email', 'bio', 'affiliate_id')
    form_widget_args = {
        'id': {'disabled': True},
        'password_hash': {'disabled': True},
        'created_at': {'disabled': True},
        'updated_at': {'disabled': True}
    }
    
    # Add stats
    @expose('/stats/<influencer_id>')
    def stats_view(self, influencer_id):
        if not self.is_accessible():
            return redirect(url_for('login'))
        
        from models import InfluencerModel, ChatInteractionModel
        
        influencer = InfluencerModel.query.get(influencer_id)
        if not influencer:
            return redirect(url_for('admin.index'))
        
        # Total chats
        total_chats = ChatInteractionModel.query.filter_by(influencer_id=influencer_id).count()
        
        # Product recommendations
        product_recs = ChatInteractionModel.query.filter_by(
            influencer_id=influencer_id,
            product_recommendations=True
        ).count()
        
        # Fan engagement
        unique_fans = ChatInteractionModel.query.filter(
            ChatInteractionModel.influencer_id == influencer_id,
            ChatInteractionModel.fan_id != None
        ).distinct(ChatInteractionModel.fan_id).count()
        
        return self.render('admin/influencer_stats.html',
                          influencer=influencer,
                          total_chats=total_chats,
                          product_recs=product_recs,
                          unique_fans=unique_fans)

class FanView(AuthModelView):
    """Custom view for fans"""
    column_list = ('id', 'username', 'email', 'created_at', 'chat_count')
    column_searchable_list = ['username', 'email']
    column_filters = ['created_at']
    column_sortable_list = ['username', 'email', 'created_at']
    column_default_sort = ('created_at', True)
    
    # Custom fields for forms
    form_columns = ('username', 'email')
    form_widget_args = {
        'id': {'disabled': True},
        'password_hash': {'disabled': True},
        'created_at': {'disabled': True},
        'updated_at': {'disabled': True}
    }
    
    def _chat_count(view, context, model, name):
        from models import ChatInteractionModel
        return ChatInteractionModel.query.filter_by(fan_id=model.id).count()
    
    column_formatters = {
        'chat_count': _chat_count
    }
    
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'email': 'Email',
        'created_at': 'Created',
        'chat_count': 'Total Chats'
    }

class ChatInteractionView(AuthModelView):
    """Custom view for chat interactions"""
    column_list = ('id', 'influencer', 'fan', 'user_message_preview', 'product_recommendations', 'created_at')
    column_searchable_list = ['user_message', 'bot_response']
    column_filters = ['created_at', 'product_recommendations', 'influencer_id', 'fan_id']
    column_sortable_list = ['created_at', 'product_recommendations']
    column_default_sort = ('created_at', True)
    
    def _user_message_preview(view, context, model, name):
        return model.user_message[:50] + '...' if len(model.user_message) > 50 else model.user_message
    
    column_formatters = {
        'user_message_preview': _user_message_preview,
        'influencer': lambda v, c, m, p: m.influencer.username if m.influencer else None,
        'fan': lambda v, c, m, p: m.fan.username if m.fan else 'Anonymous'
    }
    
    column_labels = {
        'id': 'ID',
        'influencer': 'Influencer',
        'fan': 'Fan',
        'user_message_preview': 'User Message',
        'product_recommendations': 'Product Rec.',
        'created_at': 'Date & Time'
    }
    
    # Disable editing
    can_edit = False
    can_create = False
    
    # Custom detail view
    @expose('/details/<chat_id>')
    def details_view(self, chat_id):
        if not self.is_accessible():
            return redirect(url_for('login'))
        
        from models import ChatInteractionModel
        
        chat = ChatInteractionModel.query.get(chat_id)
        if not chat:
            return redirect(url_for('admin.index'))
        
        return self.render('admin/chat_details.html', chat=chat)

class AffiliateView(AuthModelView):
    """Custom view for affiliate links"""
    column_list = ('id', 'influencer', 'platform', 'affiliate_id', 'created_at')
    column_searchable_list = ['platform', 'affiliate_id']
    column_filters = ['platform', 'influencer_id', 'created_at']
    column_sortable_list = ['platform', 'created_at']
    column_default_sort = ('created_at', True)
    
    column_formatters = {
        'influencer': lambda v, c, m, p: m.influencer.username if m.influencer else None
    }
    
    column_labels = {
        'id': 'ID',
        'influencer': 'Influencer',
        'platform': 'Platform',
        'affiliate_id': 'Affiliate ID',
        'created_at': 'Created'
    }