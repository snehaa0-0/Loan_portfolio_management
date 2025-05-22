"""
Database initialization and management module.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from config.config import get_database_uri

logger = logging.getLogger(__name__)

def init_db(db_uri=None):
    """
    Initialize the database.
    
    Args:
        db_uri: Database URI to use. If None, use the configured URI.
        
    Returns:
        SQLAlchemy engine
    """
    if db_uri is None:
        db_uri = get_database_uri()
    
    logger.info(f"Initializing database with URI: {db_uri}")
    engine = create_engine(db_uri)
    
    # Create all tables
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")
    
    return engine

def get_session(engine):
    """
    Create a database session.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        SQLAlchemy session
    """
    Session = sessionmaker(bind=engine)
    return Session()