from flask import Blueprint, render_template, jsonify, current_app
from app.loan_manager import LoanManager
from app import get_session
import datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint for dashboard - REMOVED url_prefix to fix routing
dashboard_bp = Blueprint('dashboard', __name__)

# Function for command-line interface as referenced in run.py
def display_dashboard(session):
    """
    Display dashboard for command-line interface.
    This function bridges the gap between Flask app and CLI app.
    """
    try:
        loan_manager = LoanManager(session)
        
        # Get overall portfolio metrics
        portfolio = loan_manager.get_portfolio_overview()
        
        # Get all active loans for dashboard display
        from app.models import LoanStatus
        active_loans = loan_manager.get_all_loans(status=LoanStatus.ACTIVE)
        
        # Print dashboard summary
        print("\n===== LOAN PORTFOLIO DASHBOARD =====")
        print(f"Total portfolio value: ${portfolio.get('total_value', 0):,.2f}")
        print(f"Active loans: {len(active_loans)}")
        print(f"Syndicated exposure: ${portfolio.get('syndicated_exposure', 0):,.2f}")
        print(f"Retained exposure: ${portfolio.get('retained_exposure', 0):,.2f}")
        
        # Print active loans
        print("\n----- ACTIVE LOANS -----")
        for loan in active_loans:
            try:
                print(f"Loan #{loan.loan_number}: {loan.borrower.name} - ${loan.amount:,.2f}")
                print(f"  Status: {loan.status}")
                print(f"  Maturity: {loan.maturity_date.strftime('%Y-%m-%d')}")
                print("")
            except AttributeError as e:
                logger.warning(f"Error displaying loan data: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error displaying dashboard: {e}")
        print(f"Error: Failed to display dashboard - {e}")

@dashboard_bp.route('/')
def index():
    """Main dashboard view displaying portfolio summary"""
    session = None
    try:
        session = get_session()
        loan_manager = LoanManager(session)  # Pass session directly to constructor
        
        # Get overall portfolio metrics
        portfolio = loan_manager.get_portfolio_overview() or {}
        
        # Get all active loans for dashboard display
        filters = {'status': 'ACTIVE'}
        active_loans = loan_manager.get_all_loans(filters) or []
        
        # Get some upcoming payments (for notification section)
        upcoming_payments = []
        today = datetime.date.today()
        thirty_days_later = today + datetime.timedelta(days=30)
        
        return render_template('dashboard.html',
                              portfolio=portfolio,
                              active_loans=active_loans,
                              upcoming_payments=upcoming_payments)
    except Exception as e:
        logger.error(f"Error in dashboard index: {e}")
        # Return a simple error page instead of relying on template
        return f"""
        <html>
        <head><title>Dashboard Error</title></head>
        <body>
            <h1>Dashboard Error</h1>
            <p>Error loading dashboard: {str(e)}</p>
            <p>Please check the application logs for more details.</p>
            <a href="/">Try Again</a>
        </body>
        </html>
        """, 500
    finally:
        if session:
            session.close()

@dashboard_bp.route('/test')
def test():
    """Simple test route to verify the blueprint is working"""
    return """
    <html>
    <head><title>Dashboard Test</title></head>
    <body>
        <h1>Dashboard Blueprint is Working!</h1>
        <p>This confirms that the Flask app and blueprint are properly configured.</p>
        <ul>
            <li><a href="/">Go to Dashboard</a></li>
            <li><a href="/risk-summary">Risk Summary (JSON)</a></li>
            <li><a href="/maturity-profile">Maturity Profile (JSON)</a></li>
        </ul>
    </body>
    </html>
    """

@dashboard_bp.route('/risk-summary')
def risk_summary():
    """Dashboard component showing risk allocation"""
    session = None
    try:
        session = get_session()
        loan_manager = LoanManager(session)  # Pass session directly
        
        portfolio = loan_manager.get_portfolio_overview() or {}
        
        # For API/AJAX calls returning JSON data
        return jsonify({
            'risk_distribution': portfolio.get('risk_distribution', {}),
            'total_exposure': portfolio.get('total_exposure', 0),
            'retained_exposure': portfolio.get('retained_exposure', 0)
        })
    except Exception as e:
        logger.error(f"Error in risk summary: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            session.close()

@dashboard_bp.route('/maturity-profile')
def maturity_profile():
    """Dashboard component showing maturity timeline of loans"""
    session = None
    try:
        session = get_session()
        loan_manager = LoanManager(session)  # Pass session directly
        
        # Get all active loans
        filters = {'status': 'ACTIVE'}
        loans = loan_manager.get_all_loans(filters) or []
        
        # Group loans by maturity timeframe
        today = datetime.date.today()
        maturity_buckets = {
            '0-3 months': 0.0,
            '3-6 months': 0.0,
            '6-12 months': 0.0,
            '1-2 years': 0.0,
            '2-5 years': 0.0,
            '5+ years': 0.0
        }
        
        # Calculate days to maturity for each loan and put in appropriate bucket
        for loan in loans:
            try:
                # Calculate remaining principal for each loan
                metrics = loan_manager.calculate_loan_metrics(loan.id) or {}
                remaining_principal = metrics.get('remaining_principal', 0)
                
                # Safely get maturity date with error handling
                if not hasattr(loan, 'maturity_date'):
                    logger.warning(f"Loan {getattr(loan, 'id', 'unknown')} missing maturity_date")
                    continue
                    
                # Calculate days to maturity
                days_to_maturity = (loan.maturity_date - today).days
                
                if days_to_maturity <= 90:  # 0-3 months
                    maturity_buckets['0-3 months'] += remaining_principal
                elif days_to_maturity <= 180:  # 3-6 months
                    maturity_buckets['3-6 months'] += remaining_principal
                elif days_to_maturity <= 365:  # 6-12 months
                    maturity_buckets['6-12 months'] += remaining_principal
                elif days_to_maturity <= 730:  # 1-2 years
                    maturity_buckets['1-2 years'] += remaining_principal
                elif days_to_maturity <= 1825:  # 2-5 years
                    maturity_buckets['2-5 years'] += remaining_principal
                else:  # 5+ years
                    maturity_buckets['5+ years'] += remaining_principal
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error processing loan maturity: {e}")
                continue
        
        # For API/AJAX calls returning JSON data
        return jsonify({
            'maturity_profile': maturity_buckets
        })
    except Exception as e:
        logger.error(f"Error in maturity profile: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            session.close()

@dashboard_bp.route('/payment-forecast')
def payment_forecast():
    """Dashboard component showing expected incoming payments"""
    session = None
    try:
        session = get_session()
        loan_manager = LoanManager(session)  # Pass session directly
        
        # Get all active loans
        filters = {'status': 'ACTIVE'}
        loans = loan_manager.get_all_loans(filters) or []
        
        # In a real application, you would implement a method to retrieve scheduled payments
        # This is a simplified placeholder
        forecast = {
            'next_30_days': {
                'principal': 0.0,
                'interest': 0.0,
                'total': 0.0
            },
            'next_90_days': {
                'principal': 0.0,
                'interest': 0.0,
                'total': 0.0
            },
            'next_180_days': {
                'principal': 0.0,
                'interest': 0.0,
                'total': 0.0
            }
        }
        
        # For API/AJAX calls returning JSON data
        return jsonify({
            'payment_forecast': forecast
        })
    except Exception as e:
        logger.error(f"Error in payment forecast: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            session.close()

@dashboard_bp.route('/portfolio-alerts')
def portfolio_alerts():
    """Dashboard component showing alerts for loan portfolio"""
    session = None
    try:
        session = get_session()
        loan_manager = LoanManager(session)  # Pass session directly
        
        # Get all loans
        loans = loan_manager.get_all_loans() or []
        
        # Initialize alerts list
        alerts = []
        today = datetime.date.today()
        
        # Check for loans with upcoming maturity
        for loan in loans:
            try:
                # Safely get attributes with error handling
                if not hasattr(loan, 'maturity_date'):
                    continue
                
                days_to_maturity = (loan.maturity_date - today).days
                
                # Alert for loans maturing in 30 days
                if 0 <= days_to_maturity <= 30:
                    loan_id = getattr(loan, 'id', 'unknown')
                    loan_number = getattr(loan, 'loan_number', 'unknown')
                    
                    alerts.append({
                        'type': 'Maturity',
                        'severity': 'High',
                        'loan_id': loan_id,
                        'loan_number': loan_number,
                        'message': f'Loan #{loan_number} maturing in {days_to_maturity} days'
                    })
            except (AttributeError, TypeError) as e:
                logger.warning(f"Error processing loan alert: {e}")
                continue
        
        # In a real app, you'd also check for covenant breaches, past due payments, etc.
        
        # For API/AJAX calls returning JSON data
        return jsonify({
            'alerts': alerts
        })
    except Exception as e:
        logger.error(f"Error in portfolio alerts: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if session:
            session.close()