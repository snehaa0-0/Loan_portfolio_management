"""
Configuration file for the Syndicated Loan Portfolio Management System.
"""

# Database Configuration
DATABASE = {
    'development': 'sqlite:///loan_portfolio.db',
    'testing': 'sqlite:///:memory:',
    'production': 'sqlite:///production_loan_portfolio.db',  # Change to your production DB
}

# Application Configuration
APP_CONFIG = {
    'debug': True,
    'environment': 'development',  # 'development', 'testing', or 'production'
    'secret_key': 'your_secret_key_here',  # Change this in production!
    'log_level': 'INFO',
}

# Reporting Configuration
REPORT_CONFIG = {
    'chart_style': 'ggplot',
    'default_chart_size': (10, 6),  # Width, Height in inches
    'reports_folder': 'reports/',
}

# User Interface Configuration
UI_CONFIG = {
    'theme': 'default',
    'items_per_page': 10,
    'date_format': '%Y-%m-%d',
    'currency_symbol': '$',
}

# Get active database URI based on environment
def get_database_uri():
    """Return the database URI based on the current environment."""
    return DATABASE[APP_CONFIG['environment']]