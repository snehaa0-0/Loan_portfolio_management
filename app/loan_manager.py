"""
Core business logic for syndicated loan management.
This module handles loan operations, calculations, and business rules.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import (
    Borrower, Loan, LoanStatus, RiskRating, SyndicateParticipant, 
    SyndicatePortion, Covenant, Payment, FinancialStatement
)

logger = logging.getLogger(__name__)

class LoanManager:
    """Core class for managing syndicated loans and related operations."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the loan manager with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    # ----- Loan Management -----
    
    def create_loan(self, 
                   loan_number: str,
                   borrower_id: int,
                   amount: float,
                   origination_date: datetime,
                   maturity_date: datetime,
                   interest_rate: float,
                   purpose: str = None,
                   risk_rating: RiskRating = None,
                   status: LoanStatus = LoanStatus.PENDING) -> Loan:
        """
        Create a new syndicated loan.
        
        Args:
            loan_number: Unique loan identifier
            borrower_id: ID of the borrower
            amount: Total loan amount
            origination_date: Date when the loan starts
            maturity_date: Date when the loan ends
            interest_rate: Base interest rate of the loan
            purpose: Purpose of the loan
            risk_rating: Risk rating of the loan
            status: Initial status of the loan
            
        Returns:
            The newly created Loan object
        """
        # Validate dates
        if maturity_date <= origination_date:
            raise ValueError("Maturity date must be after origination date")
        
        # Validate loan amount
        if amount <= 0:
            raise ValueError("Loan amount must be positive")
        
        # Check if loan number already exists
        if self.db.query(Loan).filter(Loan.loan_number == loan_number).first():
            raise ValueError(f"Loan with number {loan_number} already exists")
        
        # Create new loan object
        loan = Loan(
            loan_number=loan_number,
            borrower_id=borrower_id,
            amount=amount,
            origination_date=origination_date,
            maturity_date=maturity_date,
            interest_rate=interest_rate,
            purpose=purpose,
            risk_rating=risk_rating,
            status=status
        )
        
        # Add to database
        self.db.add(loan)
        self.db.commit()
        logger.info(f"Created new loan: {loan_number} for borrower ID {borrower_id}")
        return loan
    
    def update_loan_status(self, loan_id: int, new_status: LoanStatus) -> Loan:
        """
        Update the status of a loan.
        
        Args:
            loan_id: ID of the loan to update
            new_status: New status to set
            
        Returns:
            Updated Loan object
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        old_status = loan.status
        loan.status = new_status
        self.db.commit()
        logger.info(f"Updated loan {loan.loan_number} status from {old_status} to {new_status}")
        return loan
    
    def get_loan(self, loan_id: int) -> Optional[Loan]:
        """
        Get a loan by its ID.
        
        Args:
            loan_id: ID of the loan
            
        Returns:
            Loan object or None if not found
        """
        return self.db.query(Loan).filter(Loan.id == loan_id).first()
    
    def get_all_loans(self, 
                     status: LoanStatus = None, 
                     borrower_id: int = None, 
                     risk_rating: RiskRating = None) -> List[Loan]:
        """
        Get loans with optional filtering.
        
        Args:
            status: Filter by loan status
            borrower_id: Filter by borrower ID
            risk_rating: Filter by risk rating
            
        Returns:
            List of Loan objects
        """
        query = self.db.query(Loan)
        
        if status:
            query = query.filter(Loan.status == status)
        if borrower_id:
            query = query.filter(Loan.borrower_id == borrower_id)
        if risk_rating:
            query = query.filter(Loan.risk_rating == risk_rating)
            
        return query.all()
    
    # ----- Syndication Management -----
    
    def add_syndicate_portion(self, 
                             loan_id: int, 
                             participant_id: int, 
                             amount: float, 
                             participation_date: datetime) -> SyndicatePortion:
        """
        Add a syndicate portion to a loan.
        
        Args:
            loan_id: ID of the loan
            participant_id: ID of the syndicate participant
            amount: Amount of participation
            participation_date: Date of participation
            
        Returns:
            The created SyndicatePortion object
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        # Validate the amount doesn't exceed the loan amount
        current_syndicated = loan.total_syndicated
        if current_syndicated + amount > loan.amount:
            raise ValueError(f"Cannot syndicate more than the loan amount. "
                            f"Current syndicated: {current_syndicated}, "
                            f"Loan amount: {loan.amount}, "
                            f"Requested syndication: {amount}")
        
        # Create new syndicate portion
        portion = SyndicatePortion(
            loan_id=loan_id,
            participant_id=participant_id,
            amount=amount,
            participation_date=participation_date
        )
        
        self.db.add(portion)
        self.db.commit()
        logger.info(f"Added syndicate portion of {amount} to loan {loan.loan_number} "
                   f"for participant ID {participant_id}")
        return portion
    
    def get_loan_syndication_status(self, loan_id: int) -> Dict:
        """
        Get the syndication status of a loan.
        
        Args:
            loan_id: ID of the loan
            
        Returns:
            Dict with syndication details
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        total_syndicated = loan.total_syndicated
        remaining = loan.amount - total_syndicated
        syndication_percentage = (total_syndicated / loan.amount) * 100 if loan.amount > 0 else 0
        
        return {
            "loan_id": loan_id,
            "loan_number": loan.loan_number,
            "total_amount": loan.amount,
            "total_syndicated": total_syndicated,
            "remaining_to_syndicate": remaining,
            "syndication_percentage": syndication_percentage,
            "portions": [
                {
                    "participant_id": p.participant_id,
                    "participant_name": p.participant.name,
                    "amount": p.amount,
                    "percentage": (p.amount / loan.amount) * 100 if loan.amount > 0 else 0,
                    "participation_date": p.participation_date
                } for p in loan.syndicate_portions
            ]
        }
    
    # ----- Payment Management -----
    
    def register_payment(self,
                        loan_id: int,
                        payment_date: datetime,
                        principal_amount: float = 0.0,
                        interest_amount: float = 0.0,
                        fees_amount: float = 0.0) -> Payment:
        """
        Register an actual payment for a loan.
        
        Args:
            loan_id: ID of the loan
            payment_date: Date of the payment
            principal_amount: Principal amount paid
            interest_amount: Interest amount paid
            fees_amount: Fees amount paid
            
        Returns:
            Created Payment object
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        # Validate payment amounts
        if principal_amount < 0 or interest_amount < 0 or fees_amount < 0:
            raise ValueError("Payment amounts cannot be negative")
        
        # Check if principal amount exceeds remaining principal
        if principal_amount > loan.remaining_principal:
            raise ValueError(f"Principal payment ({principal_amount}) exceeds "
                           f"remaining principal ({loan.remaining_principal})")
        
        # Create payment record
        payment = Payment(
            loan_id=loan_id,
            payment_date=payment_date,
            principal_amount=principal_amount,
            interest_amount=interest_amount,
            fees_amount=fees_amount,
            is_scheduled=False  # This is an actual payment
        )
        
        self.db.add(payment)
        self.db.commit()
        
        # Update loan status if fully paid
        if loan.remaining_principal <= 0:
            self.update_loan_status(loan_id, LoanStatus.PAID_OFF)
        
        logger.info(f"Registered payment for loan {loan.loan_number}: "
                   f"Principal: {principal_amount}, Interest: {interest_amount}, Fees: {fees_amount}")
        return payment
    
    def schedule_payments(self, 
                         loan_id: int, 
                         start_date: datetime, 
                         frequency_months: int = 1, 
                         num_payments: int = None) -> List[Payment]:
        """
        Schedule future payments for a loan.
        
        Args:
            loan_id: ID of the loan
            start_date: Date of the first payment
            frequency_months: Frequency of payments in months
            num_payments: Number of payments to schedule (default: until maturity)
            
        Returns:
            List of scheduled Payment objects
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        # Calculate number of payments if not specified
        if not num_payments:
            months_to_maturity = ((loan.maturity_date.year - start_date.year) * 12 + 
                                loan.maturity_date.month - start_date.month)
            num_payments = (months_to_maturity // frequency_months) + 1
        
        # Calculate payment amounts (simple amortization)
        remaining_principal = loan.remaining_principal
        principal_per_payment = remaining_principal / num_payments
        
        payments = []
        current_date = start_date
        
        # Delete any existing scheduled payments
        self.db.query(Payment).filter(
            and_(Payment.loan_id == loan_id, Payment.is_scheduled == True)
        ).delete()
        
        # Create scheduled payments
        for i in range(num_payments):
            # For the last payment, use the remaining principal
            if i == num_payments - 1:
                principal_amount = remaining_principal
            else:
                principal_amount = principal_per_payment
            
            # Calculate interest (simple interest)
            interest_amount = remaining_principal * loan.interest_rate / 12
            
            payment = Payment(
                loan_id=loan_id,
                payment_date=current_date,
                principal_amount=principal_amount,
                interest_amount=interest_amount,
                fees_amount=0.0,
                is_scheduled=True
            )
            
            payments.append(payment)
            self.db.add(payment)
            
            # Update remaining principal and date for next iteration
            remaining_principal -= principal_amount
            current_date = self._add_months(current_date, frequency_months)
        
        self.db.commit()
        logger.info(f"Scheduled {len(payments)} payments for loan {loan.loan_number}")
        return payments
    
    def _add_months(self, date: datetime, months: int) -> datetime:
        """Add months to a date, handling month/year rollover correctly."""
        month = date.month - 1 + months
        year = date.year + month // 12
        month = month % 12 + 1
        day = min(date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
        return date.replace(year=year, month=month, day=day)
    
    # ----- Covenant Management -----
    
    def add_covenant(self,
                    loan_id: int,
                    description: str,
                    covenant_type: str,
                    threshold_value: float = None) -> Covenant:
        """
        Add a covenant to a loan.
        
        Args:
            loan_id: ID of the loan
            description: Description of the covenant
            covenant_type: Type of covenant (Financial, Operational, etc.)
            threshold_value: Threshold value for the covenant
            
        Returns:
            Created Covenant object
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        covenant = Covenant(
            loan_id=loan_id,
            description=description,
            covenant_type=covenant_type,
            threshold_value=threshold_value,
            is_active=True
        )
        
        self.db.add(covenant)
        self.db.commit()
        logger.info(f"Added covenant to loan {loan.loan_number}: {covenant_type}")
        return covenant
    
    # ----- Risk and Analytics -----
    
    def calculate_loan_metrics(self, loan_id: int) -> Dict:
        """
        Calculate key metrics for a loan.
        
        Args:
            loan_id: ID of the loan
            
        Returns:
            Dict with loan metrics
        """
        loan = self.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        # Calculate total payments made
        actual_payments = [p for p in loan.payments if not p.is_scheduled]
        total_principal_paid = sum(p.principal_amount for p in actual_payments)
        total_interest_paid = sum(p.interest_amount for p in actual_payments)
        total_fees_paid = sum(p.fees_amount for p in actual_payments)
        
        # Calculate remaining amounts
        remaining_principal = loan.amount - total_principal_paid
        
        # Calculate days to maturity
        days_to_maturity = (loan.maturity_date - datetime.now().date()).days
        
        # Get latest risk rating
        risk_rating = loan.risk_rating.value if loan.risk_rating else "Not rated"
        
        return {
            "loan_id": loan_id,
            "loan_number": loan.loan_number,
            "borrower_name": loan.borrower.name,
            "original_amount": loan.amount,
            "remaining_principal": remaining_principal,
            "principal_paid": total_principal_paid,
            "interest_paid": total_interest_paid,
            "fees_paid": total_fees_paid,
            "days_to_maturity": max(0, days_to_maturity),
            "syndication_percentage": (loan.total_syndicated / loan.amount) * 100 if loan.amount > 0 else 0,
            "risk_rating": risk_rating,
            "status": loan.status.value
        }
    
    def get_portfolio_overview(self) -> Dict:
        """
        Get an overview of the entire loan portfolio.
        
        Returns:
            Dict with portfolio summary metrics
        """
        # Get all active loans
        loans = self.db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).all()
        
        # Calculate portfolio metrics
        total_exposure = sum(loan.amount for loan in loans)
        total_syndicated = sum(loan.total_syndicated for loan in loans)
        retained_exposure = total_exposure - total_syndicated
        
        # Group by risk rating
        risk_breakdown = {}
        for loan in loans:
            rating = loan.risk_rating.value if loan.risk_rating else "Not rated"
            if rating not in risk_breakdown:
                risk_breakdown[rating] = 0
            risk_breakdown[rating] += loan.amount - loan.total_syndicated
        
        # Group by borrower industry
        industry_breakdown = {}
        for loan in loans:
            industry = loan.borrower.industry or "Not specified"
            if industry not in industry_breakdown:
                industry_breakdown[industry] = 0
            industry_breakdown[industry] += loan.amount - loan.total_syndicated
        
        return {
            "total_portfolio_size": total_exposure,
            "total_syndicated": total_syndicated,
            "retained_exposure": retained_exposure,
            "syndication_percentage": (total_syndicated / total_exposure) * 100 if total_exposure > 0 else 0,
            "active_loans_count": len(loans),
            "risk_breakdown": risk_breakdown,
            "industry_breakdown": industry_breakdown
        }