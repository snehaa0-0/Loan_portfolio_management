"""
Data visualization and reporting module for the Syndicated Loan Manager.
"""
import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Borrower, Loan, LoanStatus, RiskRating, SyndicateParticipant, 
    SyndicatePortion, Covenant, Payment, FinancialStatement
)
from app.loan_manager import LoanManager
from config.config import REPORT_CONFIG

# Configure Matplotlib and Seaborn
plt.style.use(REPORT_CONFIG['chart_style'])
logger = logging.getLogger(__name__)

class LoanReporter:
    """
    Class for generating reports and visualizations from loan data.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the reporter with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.loan_manager = LoanManager(db_session)
        self.reports_folder = REPORT_CONFIG['reports_folder']
        
        # Ensure reports folder exists
        os.makedirs(self.reports_folder, exist_ok=True)
    
    def generate_portfolio_summary(self, output_file: Optional[str] = None) -> Dict:
        """
        Generate a portfolio summary report.
        
        Args:
            output_file: Optional file path to save the report visualization
            
        Returns:
            Dict with portfolio summary data
        """
        # Get portfolio overview from loan manager
        portfolio_data = self.loan_manager.get_portfolio_overview()
        
        # Create visualization
        if output_file:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=REPORT_CONFIG['default_chart_size'])
            
            # Risk rating distribution
            risk_data = portfolio_data['risk_breakdown']
            if risk_data:
                risk_df = pd.DataFrame({
                    'Risk Rating': list(risk_data.keys()),
                    'Exposure': list(risk_data.values())
                })
                risk_df = risk_df.sort_values('Risk Rating')
                sns.barplot(x='Risk Rating', y='Exposure', data=risk_df, ax=ax1)
                ax1.set_title('Exposure by Risk Rating')
                ax1.tick_params(axis='x', rotation=45)
            else:
                ax1.text(0.5, 0.5, 'No risk data available', 
                         horizontalalignment='center', verticalalignment='center')
            
            # Industry distribution
            industry_data = portfolio_data['industry_breakdown']
            if industry_data:
                industry_df = pd.DataFrame({
                    'Industry': list(industry_data.keys()),
                    'Exposure': list(industry_data.values())
                })
                industry_df = industry_df.sort_values('Exposure', ascending=False)
                sns.barplot(x='Exposure', y='Industry', data=industry_df, ax=ax2)
                ax2.set_title('Exposure by Industry')
            else:
                ax2.text(0.5, 0.5, 'No industry data available',
                        horizontalalignment='center', verticalalignment='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.reports_folder, output_file))
            plt.close()
            logger.info(f"Portfolio summary visualization saved to {output_file}")
        
        return portfolio_data
    
    def generate_loan_performance_report(self, loan_id: int, output_file: Optional[str] = None) -> Dict:
        """
        Generate a performance report for a specific loan.
        
        Args:
            loan_id: ID of the loan to report on
            output_file: Optional file path to save the report visualization
            
        Returns:
            Dict with loan performance data
        """
        # Get loan data
        loan = self.loan_manager.get_loan(loan_id)
        if not loan:
            raise ValueError(f"Loan with ID {loan_id} not found")
        
        # Get all payments for this loan
        actual_payments = [p for p in loan.payments if not p.is_scheduled]
        scheduled_payments = [p for p in loan.payments if p.is_scheduled]
        
        # Calculate payment history
        payment_history = []
        cumulative_principal = 0
        
        for payment in sorted(actual_payments, key=lambda p: p.payment_date):
            cumulative_principal += payment.principal_amount
            payment_history.append({
                'date': payment.payment_date,
                'principal': payment.principal_amount,
                'interest': payment.interest_amount,
                'fees': payment.fees_amount,
                'total': payment.principal_amount + payment.interest_amount + payment.fees_amount,
                'cumulative_principal': cumulative_principal,
                'remaining_principal': loan.amount - cumulative_principal
            })
        
        # Get loan metrics
        loan_metrics = self.loan_manager.calculate_loan_metrics(loan_id)
        
        # Create visualization
        if output_file and payment_history:
            # Convert payment history to DataFrame
            df = pd.DataFrame(payment_history)
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
            
            # Principal paydown chart
            ax1.plot(df['date'], df['remaining_principal'], marker='o', linewidth=2)
            ax1.set_title(f'Principal Paydown - Loan {loan.loan_number}')
            ax1.set_ylabel('Remaining Principal')
            ax1.grid(True)
            
            # Payment breakdown chart
            width = 0.25
            dates = df['date']
            x = np.arange(len(dates))
            
            ax2.bar(x - width, df['principal'], width, label='Principal')
            ax2.bar(x, df['interest'], width, label='Interest')
            ax2.bar(x + width, df['fees'], width, label='Fees')
            
            ax2.set_title('Payment Breakdown')
            ax2.set_ylabel('Amount')
            ax2.set_xticks(x)
            ax2.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates], rotation=45)
            ax2.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.reports_folder, output_file))
            plt.close()
            logger.info(f"Loan performance report saved to {output_file}")
        
        return {
            'loan_metrics': loan_metrics,
            'payment_history': payment_history,
            'future_payments': [
                {
                    'date': p.payment_date,
                    'principal': p.principal_amount,
                    'interest': p.interest_amount,
                    'fees': p.fees_amount,
                    'total': p.principal_amount + p.interest_amount + p.fees_amount
                } for p in sorted(scheduled_payments, key=lambda p: p.payment_date)
            ]
        }
    
    def generate_syndication_report(self, output_file: Optional[str] = None) -> List[Dict]:
        """
        Generate a report on syndication activity across the portfolio.
        
        Args:
            output_file: Optional file path to save the report visualization
            
        Returns:
            List of dicts with syndication data by loan
        """
        # Get all active loans
        loans = self.db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).all()
        
        syndication_data = []
        for loan in loans:
            syndication_info = self.loan_manager.get_loan_syndication_status(loan.id)
            syndication_data.append(syndication_info)
        
        # Get participant data
        participants = self.db.query(SyndicateParticipant).all()
        participant_exposure = {}
        
        for participant in participants:
            exposure = sum(portion.amount for portion in participant.portions 
                         if portion.loan.status == LoanStatus.ACTIVE)
            participant_exposure[participant.name] = exposure
        
        # Create visualization
        if output_file and participant_exposure:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
            
            # Syndication percentage by loan
            loan_data = pd.DataFrame({
                'Loan': [data['loan_number'] for data in syndication_data],
                'Syndication %': [data['syndication_percentage'] for data in syndication_data]
            })
            
            sns.barplot(x='Loan', y='Syndication %', data=loan_data, ax=ax1)
            ax1.set_title('Syndication Percentage by Loan')
            ax1.set_ylim([0, 100])
            ax1.tick_params(axis='x', rotation=45)
            
            # Participant exposure
            participant_df = pd.DataFrame({
                'Participant': list(participant_exposure.keys()),
                'Exposure': list(participant_exposure.values())
            })
            participant_df = participant_df.sort_values('Exposure', ascending=False)
            
            sns.barplot(x='Exposure', y='Participant', data=participant_df, ax=ax2)
            ax2.set_title('Exposure by Syndicate Participant')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.reports_folder, output_file))
            plt.close()
            logger.info(f"Syndication report saved to {output_file}")
        
        return {
            'loans': syndication_data,
            'participant_exposure': participant_exposure
        }
    
    def generate_maturity_profile(self, output_file: Optional[str] = None) -> Dict:
        """
        Generate a report showing the maturity profile of the loan portfolio.
        
        Args:
            output_file: Optional file path to save the report visualization
            
        Returns:
            Dict with maturity profile data
        """
        # Get all active loans
        loans = self.db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).all()
        
        # Group loans by maturity year and quarter
        maturity_profile = {}
        for loan in loans:
            year = loan.maturity_date.year
            quarter = (loan.maturity_date.month - 1) // 3 + 1
            period = f"{year} Q{quarter}"
            
            if period not in maturity_profile:
                maturity_profile[period] = 0
            
            maturity_profile[period] += loan.amount - loan.total_syndicated
        
        # Sort periods
        sorted_periods = sorted(maturity_profile.keys(), 
                               key=lambda p: (int(p.split()[0]), int(p.split()[1][1])))
        sorted_profile = {period: maturity_profile[period] for period in sorted_periods}
        
        # Create visualization
        if output_file and sorted_profile:
            plt.figure(figsize=REPORT_CONFIG['default_chart_size'])
            
            plt.bar(sorted_profile.keys(), sorted_profile.values())
            plt.title('Loan Maturity Profile')
            plt.xlabel('Period (Year/Quarter)')
            plt.ylabel('Amount Maturing')
            plt.xticks(rotation=45)
            plt.grid(True, axis='y')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.reports_folder, output_file))
            plt.close()
            logger.info(f"Maturity profile report saved to {output_file}")
        
        return sorted_profile
    
    def generate_covenant_compliance_report(self) -> Dict:
        """
        Generate a report on covenant compliance across the portfolio.
        
        Returns:
            Dict with covenant compliance data
        """
        # Get all active loans and their covenants
        loans = self.db.query(Loan).filter(Loan.status == LoanStatus.ACTIVE).all()
        
        covenant_data = {}
        for loan in loans:
            active_covenants = [c for c in loan.covenants if c.is_active]
            covenant_data[loan.loan_number] = {
                'loan_id': loan.id,
                'borrower': loan.borrower.name,
                'covenants': [
                    {
                        'id': c.id,
                        'type': c.covenant_type,
                        'description': c.description,
                        'threshold': c.threshold_value
                    } for c in active_covenants
                ]
            }
        
        return covenant_data
    
    def export_portfolio_data(self, format='csv') -> str:
        """
        Export portfolio data to a file.
        
        Args:
            format: Export format ('csv' or 'excel')
            
        Returns:
            Path to the exported file
        """
        # Get all loans
        loans = self.db.query(Loan).all()
        
        # Create dataframe with loan data
        loan_data = []
        for loan in loans:
            loan_data.append({
                'Loan Number': loan.loan_number,
                'Borrower': loan.borrower.name,
                'Industry': loan.borrower.industry,
                'Amount': loan.amount,
                'Remaining Principal': loan.remaining_principal,
                'Origination Date': loan.origination_date,
                'Maturity Date': loan.maturity_date,
                'Interest Rate': loan.interest_rate,
                'Status': loan.status.value,
                'Risk Rating': loan.risk_rating.value if loan.risk_rating else "Not rated",
                'Syndication %': (loan.total_syndicated / loan.amount * 100) if loan.amount > 0 else 0
            })
        
        # Create DataFrame
        df = pd.DataFrame(loan_data)
        
        # Export data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format.lower() == 'csv':
            filename = f'portfolio_export_{timestamp}.csv'
            file_path = os.path.join(self.reports_folder, filename)
            df.to_csv(file_path, index=False)
        elif format.lower() in ('excel', 'xlsx'):
            filename = f'portfolio_export_{timestamp}.xlsx'
            file_path = os.path.join(self.reports_folder, filename)
            df.to_excel(file_path, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Portfolio data exported to {file_path}")
        return file_path