#!/usr/bin/env python
"""
Script to initialize the database and create tables.
"""
import os
import logging
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import get_database_uri
from app.models import init_db

logger = logging.getLogger(__name__)

def main():
    """Initialize the database."""
    try:
        # Get database URI from config
        db_uri = get_database_uri()
        
        # Initialize database
        engine = init_db(db_uri)
        
        logger.info("Database initialization complete.")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run initialization
    main()