from flask import Blueprint

# Import UI modules
from .dashboard import dashboard_bp
from .loan_view import loan_bp

# Create a unified UI blueprint
ui_bp = Blueprint('ui', __name__)

# Register child blueprints
def register_blueprints(app):
    """Register all UI-related blueprints with the Flask app"""
    app.register_blueprint(ui_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(loan_bp)
    
    return app