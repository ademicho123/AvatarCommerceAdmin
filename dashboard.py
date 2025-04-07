from flask_admin import BaseView, expose
from flask import session, redirect, url_for
from sqlalchemy import func, desc, distinct
from datetime import datetime, timedelta
import json

from models import db, InfluencerModel, FanModel, ChatInteractionModel, AffiliateModel

class DashboardView(BaseView):
    @expose('/')
    def index(self):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        
        # Key metrics
        influencer_count = InfluencerModel.query.count()
        fan_count = FanModel.query.count()
        chat_count = ChatInteractionModel.query.count()
        product_rec_count = ChatInteractionModel.query.filter_by(product_recommendations=True).count()
        
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
        
        # Product recommendation rate
        if chat_count > 0:
            product_rec_rate = (product_rec_count / chat_count) * 100
        else:
            product_rec_rate = 0
            
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

class AnalyticsView(BaseView):
    @expose('/')
    def index(self):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        
        # Time ranges
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        # User growth
        new_influencers_today = InfluencerModel.query.filter(
            func.date(InfluencerModel.created_at) == today
        ).count()
        
        new_fans_today = FanModel.query.filter(
            func.date(FanModel.created_at) == today
        ).count()
        
        # Chat volume
        chats_today = ChatInteractionModel.query.filter(
            func.date(ChatInteractionModel.created_at) == today
        ).count()
        
        chats_yesterday = ChatInteractionModel.query.filter(
            func.date(ChatInteractionModel.created_at) == yesterday
        ).count()
        
        chats_growth = 0
        if chats_yesterday > 0:
            chats_growth = ((chats_today - chats_yesterday) / chats_yesterday) * 100
        
        # Product recommendations
        product_recs_today = ChatInteractionModel.query.filter(
            func.date(ChatInteractionModel.created_at) == today,
            ChatInteractionModel.product_recommendations == True
        ).count()
        
        # Monthly trend
        monthly_data = db.session.query(
            func.date(ChatInteractionModel.created_at).label('date'),
            func.count().label('chat_count'),
            func.sum(
                func.cast(ChatInteractionModel.product_recommendations, db.Integer)
            ).label('product_count')
        ).filter(ChatInteractionModel.created_at >= last_month) \
         .group_by(func.date(ChatInteractionModel.created_at)) \
         .order_by(func.date(ChatInteractionModel.created_at)) \
         .all()
        
        # Format for charts
        dates = [d.date.strftime('%Y-%m-%d') for d in monthly_data]
        chat_counts = [d.chat_count for d in monthly_data]
        product_counts = [d.product_count if d.product_count else 0 for d in monthly_data]
        
        # Active users
        active_influencers = db.session.query(
            func.count(distinct(ChatInteractionModel.influencer_id))
        ).filter(ChatInteractionModel.created_at >= last_week).scalar()
        
        active_fans = db.session.query(
            func.count(distinct(ChatInteractionModel.fan_id))
        ).filter(
            ChatInteractionModel.created_at >= last_week,
            ChatInteractionModel.fan_id != None
        ).scalar()
        
        # Platform stats
        platform_stats = db.session.query(
            AffiliateModel.platform,
            func.count().label('count')
        ).group_by(AffiliateModel.platform) \
         .order_by(desc('count')) \
         .all()
        
        platform_labels = [p.platform for p in platform_stats]
        platform_values = [p.count for p in platform_stats]
        
        return self.render('admin/analytics.html',
                          new_influencers_today=new_influencers_today,
                          new_fans_today=new_fans_today,
                          chats_today=chats_today,
                          chats_yesterday=chats_yesterday,
                          chats_growth=chats_growth,
                          product_recs_today=product_recs_today,
                          dates_json=json.dumps(dates),
                          chat_counts_json=json.dumps(chat_counts),
                          product_counts_json=json.dumps(product_counts),
                          active_influencers=active_influencers,
                          active_fans=active_fans,
                          platform_labels_json=json.dumps(platform_labels),
                          platform_values_json=json.dumps(platform_values))