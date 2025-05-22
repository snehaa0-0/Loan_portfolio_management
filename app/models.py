"""
Database models for the Syndicated Loan Portfolio Management System.
Uses SQLAlchemy ORM to define the database schema.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, Boolean, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
import datetime

Base = declarative_base()

class RiskRating(enum.Enum):
    """Risk rating classifications for loans and borrowers."""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"

class LoanStatus(enum.Enum):
    """Loan status classifications."""
    PENDING = "Pending"
    ACTIVE = "Active"
    PAID_OFF = "Paid Off"
    DEFAULT = "Default"
    RESTRUCTURED = "Restructured"

class Borrower(Base):
    """Represents a borrower entity that can have multiple loans."""
    __tablename__ = 'borrowers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    industry = Column(String(50))
    credit_rating = Column(Enum(RiskRating))
    financial_statements = relationship("FinancialStatement", back_populates="borrower")
    loans = relationship("Loan", back_populates="borrower")
    
    def __repr__(self):
        return f"<Borrower(id={self.id}, name='{self.name}', industry='{self.industry}')>"

class FinancialStatement(Base):
    """Financial statement data for borrowers."""
    __tablename__ = 'financial_statements'
    
    id = Column(Integer, primary_key=True)
    borrower_id = Column(Integer, ForeignKey('borrowers.id'))
    statement_date = Column(Date, nullable=False)
    revenue = Column(Float)
    ebitda = Column(Float)
    net_income = Column(Float)
    total_assets = Column(Float)
    total_debt = Column(Float)
    
    borrower = relationship("Borrower", back_populates="financial_statements")
    
    def __repr__(self):
        return f"<FinancialStatement(id={self.id}, borrower_id={self.borrower_id}, date='{self.statement_date}')>"

class Loan(Base):
    """
    Core loan model that represents a syndicated loan.
    Has relationships with borrowers, syndicate portions, covenants, and payments.
    """
    __tablename__ = 'loans'
    
    id = Column(Integer, primary_key=True)
    loan_number = Column(String(20), unique=True, nullable=False)
    borrower_id = Column(Integer, ForeignKey('borrowers.id'))
    amount = Column(Float, nullable=False)
    origination_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    interest_rate = Column(Float, nullable=False)  # Base rate
    status = Column(Enum(LoanStatus), default=LoanStatus.PENDING)
    purpose = Column(String(200))
    risk_rating = Column(Enum(RiskRating))
    
    borrower = relationship("Borrower", back_populates="loans")
    syndicate_portions = relationship("SyndicatePortion", back_populates="loan")
    covenants = relationship("Covenant", back_populates="loan")
    payments = relationship("Payment", back_populates="loan")
    
    def __repr__(self):
        return f"<Loan(id={self.id}, number='{self.loan_number}', amount={self.amount})>"
    
    @property
    def total_syndicated(self):
        """Calculate the total amount that has been syndicated to participants."""
        return sum(portion.amount for portion in self.syndicate_portions)
    
    @property
    def remaining_principal(self):
        """Calculate the remaining principal balance on the loan."""
        principal_paid = sum(payment.principal_amount for payment in self.payments 
                             if not payment.is_scheduled)
        return self.amount - principal_paid

class SyndicateParticipant(Base):
    """Financial institutions that participate in syndicated loans."""
    __tablename__ = 'syndicate_participants'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    institution_type = Column(String(50))  # Bank, Insurance, Investment Fund, etc.
    contact_email = Column(String(100))
    
    portions = relationship("SyndicatePortion", back_populates="participant")
    
    def __repr__(self):
        return f"<SyndicateParticipant(id={self.id}, name='{self.name}')>"

class SyndicatePortion(Base):
    """
    Represents a portion of a syndicated loan assigned to a participant.
    Links loans to syndicate participants.
    """
    __tablename__ = 'syndicate_portions'
    
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id'))
    participant_id = Column(Integer, ForeignKey('syndicate_participants.id'))
    amount = Column(Float, nullable=False)
    participation_date = Column(Date, nullable=False)
    
    loan = relationship("Loan", back_populates="syndicate_portions")
    participant = relationship("SyndicateParticipant", back_populates="portions")
    
    def __repr__(self):
        return f"<SyndicatePortion(loan_id={self.loan_id}, participant_id={self.participant_id}, amount={self.amount})>"

class Covenant(Base):
    """Loan covenants that borrowers must comply with."""
    __tablename__ = 'covenants'
    
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id'))
    description = Column(Text, nullable=False)
    covenant_type = Column(String(50))  # Financial, Operational, etc.
    threshold_value = Column(Float)
    is_active = Column(Boolean, default=True)
    
    loan = relationship("Loan", back_populates="covenants")
    
    def __repr__(self):
        return f"<Covenant(id={self.id}, loan_id={self.loan_id}, type='{self.covenant_type}')>"

class Payment(Base):
    """
    Loan payment records, both scheduled and actual.
    Includes principal, interest, and fee components.
    """
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loans.id'))
    payment_date = Column(Date, nullable=False)
    principal_amount = Column(Float, default=0.0)
    interest_amount = Column(Float, default=0.0)
    fees_amount = Column(Float, default=0.0)
    is_scheduled = Column(Boolean, default=True)  # True if scheduled, False if actual payment
    
    loan = relationship("Loan", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, loan_id={self.loan_id}, date='{self.payment_date}', amount={self.principal_amount + self.interest_amount + self.fees_amount})>"

# Database initialization function
def init_db(db_path='sqlite:///loan_portfolio.db'):
    """Initialize the database and create tables."""
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    return engine