from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.loan_manager import LoanManager
from app import get_session
from datetime import datetime

# Create Blueprint for loan views
loan_bp = Blueprint('loans', __name__, url_prefix='/loans')

@loan_bp.route('/')
def loan_list():
    """Display list of all loans with filtering options"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    # Get filter parameters from request
    status = request.args.get('status')
    risk_rating = request.args.get('risk_rating')
    
    # Apply filters if provided
    filters = {}
    if status:
        filters['status'] = status
    if risk_rating:
        filters['risk_rating'] = risk_rating
    
    # Get loans with optional filters
    loans = loan_manager.get_all_loans(filters)
    
    # Get portfolio overview for summary metrics
    portfolio_overview = loan_manager.get_portfolio_overview()
    
    return render_template('loans/index.html', 
                          loans=loans, 
                          portfolio_overview=portfolio_overview)

@loan_bp.route('/<int:loan_id>')
def loan_details(loan_id):
    """Display detailed information about a specific loan"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    loan = loan_manager.get_loan(loan_id)
    if not loan:
        flash('Loan not found', 'error')
        return redirect(url_for('loans.loan_list'))
    
    # Get additional information for the loan
    metrics = loan_manager.calculate_loan_metrics(loan_id)
    syndication = loan_manager.get_loan_syndication_status(loan_id)
    
    return render_template('loan_details.html',
                          loan=loan,
                          metrics=metrics,
                          syndication=syndication)

@loan_bp.route('/create', methods=['GET', 'POST'])
def create_loan():
    """Create a new loan"""
    if request.method == 'POST':
        session = get_session()
        loan_manager = LoanManager()
        loan_manager.initialize(session)
        
        try:
            # Get form data
            loan_data = {
                'loan_number': request.form.get('loan_number'),
                'borrower_id': int(request.form.get('borrower_id')),
                'amount': float(request.form.get('amount')),
                'origination_date': datetime.strptime(request.form.get('origination_date'), '%Y-%m-%d'),
                'maturity_date': datetime.strptime(request.form.get('maturity_date'), '%Y-%m-%d'),
                'interest_rate': float(request.form.get('interest_rate')),
                'purpose': request.form.get('purpose'),
                'risk_rating': int(request.form.get('risk_rating')),
                'status': request.form.get('status', 'ACTIVE')
            }
            
            # Create the loan
            loan = loan_manager.create_loan(**loan_data)
            flash(f'Loan #{loan.loan_number} created successfully', 'success')
            return redirect(url_for('loans.loan_details', loan_id=loan.id))
            
        except Exception as e:
            flash(f'Error creating loan: {str(e)}', 'error')
            return render_template('loans/create.html')
    
    # GET request - show the form
    return render_template('loans/create.html')

@loan_bp.route('/<int:loan_id>/update-status', methods=['POST'])
def update_loan_status(loan_id):
    """Update the status of a loan"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    new_status = request.form.get('status')
    
    try:
        loan = loan_manager.update_loan_status(loan_id, new_status)
        flash(f'Loan status updated to {new_status}', 'success')
    except Exception as e:
        flash(f'Error updating loan status: {str(e)}', 'error')
    
    return redirect(url_for('loans.loan_details', loan_id=loan_id))

@loan_bp.route('/<int:loan_id>/payments')
def loan_payments(loan_id):
    """View loan payment schedule and history"""
    # Implementation will depend on your payment model structure
    # This is a placeholder for the endpoint
    return render_template('loans/payments.html', loan_id=loan_id)

@loan_bp.route('/<int:loan_id>/register-payment', methods=['GET', 'POST'])
def register_payment(loan_id):
    """Register a new payment for a loan"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    if request.method == 'POST':
        try:
            payment_data = {
                'loan_id': loan_id,
                'payment_date': datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d'),
                'principal': float(request.form.get('principal', 0)),
                'interest': float(request.form.get('interest', 0)),
                'fees': float(request.form.get('fees', 0))
            }
            
            payment = loan_manager.register_payment(**payment_data)
            flash('Payment registered successfully', 'success')
            return redirect(url_for('loans.loan_details', loan_id=loan_id))
            
        except Exception as e:
            flash(f'Error registering payment: {str(e)}', 'error')
    
    loan = loan_manager.get_loan(loan_id)
    metrics = loan_manager.calculate_loan_metrics(loan_id)
    
    return render_template('loans/register_payment.html', 
                          loan=loan,
                          metrics=metrics)

@loan_bp.route('/<int:loan_id>/syndicate', methods=['GET', 'POST'])
def syndicate_loan(loan_id):
    """Add syndication portion to a loan"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    if request.method == 'POST':
        try:
            syndication_data = {
                'loan_id': loan_id,
                'participant_id': int(request.form.get('participant_id')),
                'amount': float(request.form.get('amount')),
                'participation_date': datetime.strptime(request.form.get('participation_date'), '%Y-%m-%d')
            }
            
            portion = loan_manager.add_syndicate_portion(**syndication_data)
            flash('Syndication portion added successfully', 'success')
            return redirect(url_for('loans.loan_details', loan_id=loan_id))
            
        except Exception as e:
            flash(f'Error adding syndication portion: {str(e)}', 'error')
    
    loan = loan_manager.get_loan(loan_id)
    syndication = loan_manager.get_loan_syndication_status(loan_id)
    
    return render_template('loans/syndicate.html',
                          loan=loan,
                          syndication=syndication)

@loan_bp.route('/<int:loan_id>/schedule-payments', methods=['GET', 'POST'])
def schedule_payments(loan_id):
    """Schedule payments for a loan"""
    session = get_session()
    loan_manager = LoanManager()
    loan_manager.initialize(session)
    
    if request.method == 'POST':
        try:
            schedule_data = {
                'loan_id': loan_id,
                'start_date': datetime.strptime(request.form.get('start_date'), '%Y-%m-%d'),
                'frequency_months': int(request.form.get('frequency_months', 1))
            }
            
            # Add num_payments if provided
            if request.form.get('num_payments'):
                schedule_data['num_payments'] = int(request.form.get('num_payments'))
                
            payments = loan_manager.schedule_payments(**schedule_data)
            flash(f'{len(payments)} payments scheduled successfully', 'success')
            return redirect(url_for('loans.loan_payments', loan_id=loan_id))
            
        except Exception as e:
            flash(f'Error scheduling payments: {str(e)}', 'error')
    
    loan = loan_manager.get_loan(loan_id)
    
    return render_template('loans/schedule_payments.html', loan=loan)