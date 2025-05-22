#!/usr/bin/env python
#sample data.py
"""
Script to generate sample data for testing the Syndicated Loan Manager.
"""
import sys
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # safer date arithmetic
from sqlalchemy.orm import Session

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import (
    Borrower, Loan, LoanStatus, RiskRating, SyndicateParticipant, 
    SyndicatePortion, Covenant, Payment, FinancialStatement, init_db
)
from app.loan_manager import LoanManager
from config.config import get_database_uri

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_borrowers(session: Session):
    """Create sample borrowers."""
    borrowers = [
        Borrower(name="Acme Corporation", industry="Manufacturing", credit_rating=RiskRating.BBB),
        Borrower(name="TechNova Inc.", industry="Technology", credit_rating=RiskRating.A),
        Borrower(name="Oceanic Shipping Ltd.", industry="Transportation", credit_rating=RiskRating.BB),
        Borrower(name="Global Energy Partners", industry="Energy", credit_rating=RiskRating.AA),
        Borrower(name="Atlas Construction", industry="Construction", credit_rating=RiskRating.B),
        Borrower(name="MediHealth Systems", industry="Healthcare", credit_rating=RiskRating.BBB)
    ]
    session.add_all(borrowers)
    session.commit()
    logger.info(f"Created {len(borrowers)} sample borrowers")
    return borrowers

def create_financial_statements(session: Session, borrowers: list):
    """Create sample financial statements for borrowers."""
    statements = []
    current_date = datetime.now().date()

    for borrower in borrowers:
        for year_offset in range(3):
            statement_date = datetime(current_date.year - year_offset, 12, 31).date()
            base_revenue = random.uniform(100_000_000, 1_000_000_000)
            yearly_revenue = base_revenue * (1 + 0.05 * year_offset)

            if borrower.industry == "Technology":
                ebitda_margin = random.uniform(0.25, 0.35)
                net_income_margin = random.uniform(0.15, 0.25)
                asset_turnover = random.uniform(0.8, 1.2)
                debt_to_assets = random.uniform(0.1, 0.3)
            elif borrower.industry == "Manufacturing":
                ebitda_margin = random.uniform(0.15, 0.25)
                net_income_margin = random.uniform(0.08, 0.15)
                asset_turnover = random.uniform(0.6, 0.9)
                debt_to_assets = random.uniform(0.3, 0.5)
            elif borrower.industry == "Energy":
                ebitda_margin = random.uniform(0.3, 0.4)
                net_income_margin = random.uniform(0.12, 0.2)
                asset_turnover = random.uniform(0.4, 0.7)
                debt_to_assets = random.uniform(0.4, 0.6)
            else:
                ebitda_margin = random.uniform(0.1, 0.3)
                net_income_margin = random.uniform(0.05, 0.15)
                asset_turnover = random.uniform(0.5, 1.0)
                debt_to_assets = random.uniform(0.2, 0.5)

            ebitda = yearly_revenue * ebitda_margin
            net_income = yearly_revenue * net_income_margin
            total_assets = yearly_revenue / asset_turnover
            total_debt = total_assets * debt_to_assets

            statement = FinancialStatement(
                borrower_id=borrower.id,
                statement_date=statement_date,
                revenue=yearly_revenue,
                ebitda=ebitda,
                net_income=net_income,
                total_assets=total_assets,
                total_debt=total_debt
            )
            statements.append(statement)

    session.add_all(statements)
    session.commit()
    logger.info(f"Created {len(statements)} sample financial statements")

def create_syndicate_participants(session: Session):
    """Create sample syndicate participants."""
    participants = [
        SyndicateParticipant(name="Global Investment Bank", institution_type="Investment Bank", contact_email="syndications@gib.com"),
        SyndicateParticipant(name="First National Bank", institution_type="Commercial Bank", contact_email="loan.desk@fnb.com"),
        SyndicateParticipant(name="Pacific Coast Bank", institution_type="Regional Bank", contact_email="syndications@pcb.com"),
        SyndicateParticipant(name="Horizon Insurance Company", institution_type="Insurance", contact_email="investments@horizon.com"),
        SyndicateParticipant(name="Summit Debt Fund", institution_type="Investment Fund", contact_email="deals@summit.com")
    ]
    session.add_all(participants)
    session.commit()
    logger.info(f"Created {len(participants)} sample syndicate participants")
    return participants

def create_sample_loans(session: Session, borrowers: list):
    """Create sample loans using the LoanManager."""
    loan_manager = LoanManager(session)
    loans = []
    current_date = datetime.now().date()

    for borrower in borrowers:
        for j in range(random.randint(1, 3)):
            loan_number = f"L{borrower.id}{j+1:02d}-{random.randint(1000, 9999)}"

            if borrower.credit_rating in [RiskRating.AAA, RiskRating.AA, RiskRating.A]:
                amount = random.uniform(50_000_000, 250_000_000)
            elif borrower.credit_rating in [RiskRating.BBB, RiskRating.BB]:
                amount = random.uniform(20_000_000, 100_000_000)
            else:
                amount = random.uniform(5_000_000, 50_000_000)

            amount = round(amount / 1000) * 1000

            days_ago = random.randint(30, 730)  # 1 month to 2 years ago
            origination_date = current_date - timedelta(days=days_ago)

            # Use relativedelta to safely add years
            maturity_years = random.randint(3, 7)
            maturity_date = origination_date + relativedelta(years=maturity_years)

            if borrower.credit_rating in [RiskRating.AAA, RiskRating.AA]:
                interest_rate = random.uniform(0.035, 0.055)
            elif borrower.credit_rating in [RiskRating.A, RiskRating.BBB]:
                interest_rate = random.uniform(0.055, 0.075)
            else:
                interest_rate = random.uniform(0.075, 0.12)

            if borrower.industry == "Manufacturing":
                purpose = random.choice([
                    "Equipment acquisition",
                    "Factory expansion",
                    "Working capital",
                    "Refinancing existing debt"
                ])
            elif borrower.industry == "Technology":
                purpose = random.choice([
                    "R&D investment",
                    "Acquisition financing",
                    "Infrastructure expansion",
                    "Working capital"
                ])
            elif borrower.industry == "Energy":
                purpose = random.choice([
                    "New plant construction",
                    "Equipment modernization",
                    "Renewable energy project",
                    "Refinancing"
                ])
            else:
                purpose = random.choice([
                    "Business expansion",
                    "Refinancing",
                    "Working capital",
                    "Capital expenditure"
                ])

            status = LoanStatus.ACTIVE if random.random() < 0.8 else random.choice([
                LoanStatus.PENDING,
                LoanStatus.RESTRUCTURED,
                LoanStatus.PAID_OFF
            ])

            loan = loan_manager.create_loan(
                loan_number=loan_number,
                borrower_id=borrower.id,
                amount=amount,
                origination_date=origination_date,
                maturity_date=maturity_date,
                interest_rate=interest_rate,
                purpose=purpose,
                risk_rating=borrower.credit_rating,
                status=status
            )
            loans.append(loan)

    logger.info(f"Created {len(loans)} sample loans")
    return loans

def create_covenants(session: Session, loans: list):
    """Create sample covenants for loans."""
    covenants = []

    for loan in loans:
        for _ in range(random.randint(2, 4)):
            covenant_type = random.choice(["Financial", "Operational", "Informational", "Negative"])

            if covenant_type == "Financial":
                description = random.choice([
                    "Maintain minimum Debt Service Coverage Ratio (DSCR)",
                    "Maintain maximum Debt to EBITDA ratio",
                    "Maintain minimum Current Ratio",
                    "Maintain minimum Interest Coverage Ratio",
                    "Maintain minimum Net Worth"
                ])
                threshold_value = random.uniform(1.25, 3.0) if "minimum" in description else random.uniform(3.0, 6.0)
            elif covenant_type == "Operational":
                description = random.choice([
                    "Maintain insurance coverage",
                    "Provide quarterly operational reports",
                    "Maintain environmental compliance"
                ])
                threshold_value = None
            elif covenant_type == "Informational":
                description = random.choice([
                    "Provide audited financial statements within 90 days",
                    "Provide monthly sales reports",
                    "Notify lender of any material adverse changes"
                ])
                threshold_value = None
            else:
                description = random.choice([
                    "No additional debt without lender approval",
                    "No asset sales exceeding $1 million without approval",
                    "No change in management without notification"
                ])
                threshold_value = None

            covenant = Covenant(
                loan_id=loan.id,
                covenant_type=covenant_type,
                description=description,
                threshold_value=threshold_value
            )
            covenants.append(covenant)

    session.add_all(covenants)
    session.commit()
    logger.info(f"Created {len(covenants)} sample covenants")

def create_syndicate_portions(session: Session, loans: list, participants: list):
    """Create sample syndicate portions for loans."""
    loan_manager = LoanManager(session)
    portions = []
    
    for loan in loans:
        num_participants = random.randint(2, min(5, len(participants)))
        selected_participants = random.sample(participants, num_participants)
        total_amount = loan.amount
        remaining_amount = total_amount

        # Generate random portion sizes that sum to loan amount
        random_shares = [random.random() for _ in range(num_participants)]
        total_shares = sum(random_shares)
        shares = [share / total_shares for share in random_shares]

        for idx, participant in enumerate(selected_participants):
            if idx == num_participants - 1:
                portion_amount = remaining_amount  # assign remainder to last
            else:
                portion_amount = round(total_amount * shares[idx] / 1000) * 1000
                if portion_amount > remaining_amount:
                    portion_amount = remaining_amount
                remaining_amount -= portion_amount
            
            # Use the LoanManager method instead of creating directly
            try:
                portion = loan_manager.add_syndicate_portion(
                    loan_id=loan.id,
                    participant_id=participant.id,
                    amount=portion_amount,
                    participation_date=loan.origination_date + timedelta(days=random.randint(0, 30))
                )
                portions.append(portion)
            except Exception as e:
                logger.warning(f"Error creating syndicate portion: {e}")
                continue

    logger.info(f"Created {len(portions)} sample syndicate portions")
def create_payments(session: Session, loans: list):
    """Create sample loan payments."""
    payments = []
    for loan in loans:
        # Generate 1 to 6 payments, evenly spaced from origination to maturity
        num_payments = random.randint(1, 6)
        delta_days = (loan.maturity_date - loan.origination_date).days // (num_payments + 1)
        payment_dates = [loan.origination_date + timedelta(days=delta_days * (i+1)) for i in range(num_payments)]

        for date in payment_dates:
            principal_paid = round(random.uniform(0.01, 0.2) * loan.amount / 1000) * 1000
            interest_paid = round(loan.amount * loan.interest_rate / 12 / 1000) * 1000
            total_paid = principal_paid + interest_paid
            if total_paid > loan.amount:
                principal_paid = loan.amount - interest_paid
                if principal_paid < 0:
                    principal_paid = 0
                    interest_paid = loan.amount

            payment = Payment(
                loan_id=loan.id,
                payment_date=date,
                principal_amount=principal_paid,
                interest_amount=interest_paid,
                
            )
            payments.append(payment)

    session.add_all(payments)
    session.commit()
    logger.info(f"Created {len(payments)} sample payments")

def main():
    """Main entry point to generate sample data."""
    logger.info("Starting sample data generation...")

    engine = init_db(get_database_uri())
    with Session(engine) as session:
        borrowers = create_sample_borrowers(session)
        create_financial_statements(session, borrowers)
        participants = create_syndicate_participants(session)
        loans = create_sample_loans(session, borrowers)
        create_covenants(session, loans)
        create_syndicate_portions(session, loans, participants)
        create_payments(session, loans)

    logger.info("Sample data generation completed.")

if __name__ == "__main__":
    main()
