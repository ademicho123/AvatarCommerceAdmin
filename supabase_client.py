import os
import uuid
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('supabase_client')

# Load environment variables
load_dotenv()

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

def get_supabase_client():
    """Create and return a Supabase client"""
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and API key must be set in environment variables")
    
    try:
        client = create_client(supabase_url, supabase_key)
        return client
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {str(e)}")
        raise

def sync_data_from_supabase(db, models):
    """
    Sync data from Supabase to local database
    
    Args:
        db: SQLAlchemy database instance
        models: Dictionary mapping table names to model classes
    """
    if not supabase_url or not supabase_key:
        logger.error("Supabase URL or API key not set")
        return False
    
    try:
        logger.info("Starting Supabase data synchronization")
        supabase = get_supabase_client()
        
        # Process each model type
        try:
            sync_influencers(db, supabase, models['influencers'])
            logger.info("Influencers synchronized successfully")
        except Exception as e:
            logger.error(f"Error syncing influencers: {str(e)}")
        
        try:
            sync_fans(db, supabase, models['fans'])
            logger.info("Fans synchronized successfully")
        except Exception as e:
            logger.error(f"Error syncing fans: {str(e)}")
        
        try:
            sync_chat_interactions(db, supabase, models['chat_interactions'])
            logger.info("Chat interactions synchronized successfully")
        except Exception as e:
            logger.error(f"Error syncing chat interactions: {str(e)}")
        
        try:
            sync_affiliate_links(db, supabase, models['affiliate_links'])
            logger.info("Affiliate links synchronized successfully")
        except Exception as e:
            logger.error(f"Error syncing affiliate links: {str(e)}")
        
        logger.info("Supabase data synchronization completed")
        return True
    except Exception as e:
        logger.error(f"Error in Supabase synchronization: {str(e)}")
        return False

def sync_influencers(db, supabase, InfluencerModel):
    """Sync influencers from Supabase"""
    # Fetch influencers from Supabase
    try:
        response = supabase.table('influencers').select('*').execute()
        influencers_data = response.data
        logger.info(f"Retrieved {len(influencers_data)} influencers from Supabase")
        
        for item in influencers_data:
            # Check if influencer already exists
            existing = InfluencerModel.query.filter_by(id=item.get('id')).first()
            
            if existing:
                # Update existing influencer
                existing.username = item.get('username', existing.username)
                existing.email = item.get('email', existing.email)
                existing.heygen_avatar_id = item.get('heygen_avatar_id')
                existing.original_asset_path = item.get('original_asset_path')
                existing.voice_id = item.get('voice_id')
                existing.affiliate_id = item.get('affiliate_id')
                existing.chat_page_url = item.get('chat_page_url')
                existing.bio = item.get('bio')
                existing.updated_at = datetime.utcnow()
            else:
                # Create new influencer
                new_influencer = InfluencerModel(
                    id=item.get('id', str(uuid.uuid4())),
                    username=item.get('username', f"user_{uuid.uuid4().hex[:8]}"),
                    email=item.get('email', f"email_{uuid.uuid4().hex[:8]}@example.com"),
                    password_hash=item.get('password_hash', ''),
                    heygen_avatar_id=item.get('heygen_avatar_id'),
                    original_asset_path=item.get('original_asset_path'),
                    voice_id=item.get('voice_id'),
                    affiliate_id=item.get('affiliate_id'),
                    chat_page_url=item.get('chat_page_url'),
                    bio=item.get('bio')
                )
                db.session.add(new_influencer)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sync_influencers: {str(e)}")
        raise

# Similar error handling for the other sync functions...
def sync_fans(db, supabase, FanModel):
    """Sync fans from Supabase"""
    try:
        # Fetch fans from Supabase
        response = supabase.table('fans').select('*').execute()
        fans_data = response.data
        logger.info(f"Retrieved {len(fans_data)} fans from Supabase")
        
        for item in fans_data:
            # Check if fan already exists
            existing = FanModel.query.filter_by(id=item.get('id')).first()
            
            if existing:
                # Update existing fan
                existing.username = item.get('username', existing.username)
                existing.email = item.get('email', existing.email)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new fan
                new_fan = FanModel(
                    id=item.get('id', str(uuid.uuid4())),
                    username=item.get('username', f"fan_{uuid.uuid4().hex[:8]}"),
                    email=item.get('email', f"fan_{uuid.uuid4().hex[:8]}@example.com"),
                    password_hash=item.get('password_hash', '')
                )
                db.session.add(new_fan)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sync_fans: {str(e)}")
        raise

def sync_chat_interactions(db, supabase, ChatInteractionModel):
    """Sync chat interactions from Supabase"""
    try:
        # Fetch chat interactions from Supabase
        response = supabase.table('chat_interactions').select('*').execute()
        chats_data = response.data
        logger.info(f"Retrieved {len(chats_data)} chat interactions from Supabase")
        
        for item in chats_data:
            # Check if chat interaction already exists
            existing = ChatInteractionModel.query.filter_by(id=item.get('id')).first()
            
            if not existing:
                # Create new chat interaction
                new_chat = ChatInteractionModel(
                    id=item.get('id', str(uuid.uuid4())),
                    influencer_id=item.get('influencer_id'),
                    fan_id=item.get('fan_id'),
                    user_message=item.get('user_message', ''),
                    bot_response=item.get('bot_response', ''),
                    product_recommendations=item.get('product_recommendations', False)
                )
                db.session.add(new_chat)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sync_chat_interactions: {str(e)}")
        raise

def sync_affiliate_links(db, supabase, AffiliateModel):
    """Sync affiliate links from Supabase"""
    try:
        # Fetch affiliate links from Supabase
        response = supabase.table('affiliate_links').select('*').execute()
        affiliates_data = response.data
        logger.info(f"Retrieved {len(affiliates_data)} affiliate links from Supabase")
        
        for item in affiliates_data:
            # Check if affiliate link already exists
            existing = AffiliateModel.query.filter_by(id=item.get('id')).first()
            
            if existing:
                # Update existing affiliate link
                existing.platform = item.get('platform', existing.platform)
                existing.affiliate_id = item.get('affiliate_id', existing.affiliate_id)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new affiliate link
                new_affiliate = AffiliateModel(
                    id=item.get('id', str(uuid.uuid4())),
                    influencer_id=item.get('influencer_id'),
                    platform=item.get('platform', 'unknown'),
                    affiliate_id=item.get('affiliate_id', '')
                )
                db.session.add(new_affiliate)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sync_affiliate_links: {str(e)}")
        raise