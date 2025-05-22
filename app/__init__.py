"""
Syndicated Loan Manager Application.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from config.config import get_database_uri, APP_CONFIG
from app.models import Base

# Set up logging
logging.basicConfig(
    level=getattr(logging, APP_CONFIG['log_level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(get_database_uri())

# Create session factory
session_factory = sessionmaker(bind=engine, expire_on_commit=False)
Session = scoped_session(session_factory)

def init_app():
    """Initialize the application and database."""
    logger.info(f"Initializing application in {APP_CONFIG['environment']} environment")
    
    # Create all tables
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise
    
    return True

def get_session():
    """Get a database session."""
    return Session()