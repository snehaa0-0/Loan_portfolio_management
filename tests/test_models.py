import unittest
from datetime import datetime, timedelta

from app.db.models import Loan, Payment, SyndicatePortion, Covenant


class TestLoanModel(unittest.TestCase):
    """Test cases for Loan model"""

    def setUp(self):
        """Set up test environment before each test"""
        self.today = datetime.now().date()
        self.one_year_later = self.today + timedelta(days=365)
        
        # Create a sample loan for testing
        self.loan = Loan(
            loan_number='L12345',
            borrower_id=1,
            amount=100000.00,
            origination_date=self.today,
            maturity_date=self.one_year_later,
            interest_rate=5.0,
            purpose='Working Capital',
            risk_rating=3,
            status='ACTIVE'
        )

    def test_loan_creation(self):
        """Test that a loan is created with the correct attributes"""
        self.assertEqual(self.loan.loan_number, 'L12345')
        self.assertEqual(self.loan.borrower_id, 1)
        self.assertEqual(self.loan.amount, 100000.00)
        self.assertEqual(self.loan.origination_date, self.today)
        self.assertEqual(self.loan.maturity_date, self.one_year_later)
        self.assertEqual(self.loan.interest_rate, 5.0)
        self.assertEqual(self.loan.purpose, 'Working Capital')
        self.assertEqual(self.loan.risk_rating, 3)
        self.assertEqual(self.loan.status, 'ACTIVE')

    def test_risk_rating_string(self):
        """Test that risk_rating_string returns the correct value"""
        # Test various risk ratings
        self.loan.risk_rating = 1
        self.assertEqual(self.loan.risk_rating_string, 'AAA')
        
        self.loan.risk_rating = 2
        self.assertEqual(self.loan.risk_rating_string, 'AA')
        
        self.loan.risk_rating = 3
        self.assertEqual(self.loan.risk_rating_string, 'A')
        
        self.loan.risk_rating = 4
        self.assertEqual(self.loan.risk_rating_string, 'BBB')
        
        self.loan.risk_rating = 5
        self.assertEqual(self.loan.risk_rating_string, 'BB')
        
        self.loan.risk_rating = 6
        self.assertEqual(self.loan.risk_rating_string, 'B')
        
        self.loan.risk_rating = 7
        self.assertEqual(self.loan.risk_rating_string, 'CCC')
        
        # Test invalid risk rating
        self.loan.risk_rating = 10
        self.assertEqual(self.loan.risk_rating_string, 'Unknown')

    def test_days_to_maturity(self):
        """Test that days_to_maturity returns the correct value"""
        # Set maturity date to exactly one year from today
        self.loan.maturity_date = self.one_year_later
        
        # Days to maturity should be close to 365
        self.assertAlmostEqual(self.loan.days_to_maturity, 365, delta=1)
        
        # Test past maturity
        self.loan.maturity_date = self.today - timedelta(days=10)
        self.assertEqual(self.loan.days_to_maturity, 0)

    def test_is_past_due(self):
        """Test that is_past_due returns the correct value"""
        # Not past due (future maturity date)
        self.loan.maturity_date = self.one_year_later
        self.loan.status = 'ACTIVE'
        self.assertFalse(self.loan.is_past_due)
        
        # Past due (past maturity date and still active)
        self.loan.maturity_date = self.today - timedelta(days=10)
        self.loan.status = 'ACTIVE'
        self.assertTrue(self.loan.is_past_due)
        
        # Not past due (past maturity date but not active)
        self.loan.status = 'PAID_OFF'
        self.assertFalse(self.loan.is_past_due)

    def test_remaining_principal(self):
        """Test that remaining_principal returns the correct value"""
        # Initially, remaining principal should be the full amount
        self.assertEqual(self.loan.remaining_principal, 100000.00)
        
        # Add some payments
        payment1 = Payment(
            loan_id=self.loan.id,
            payment_date=self.today,
            principal=10000.00,
            interest=500.00,
            fees=50.00,
            is_scheduled=False
        )
        
        payment2 = Payment(
            loan_id=self.loan.id,
            payment_date=self.today,
            principal=5000.00,
            interest=450.00,
            fees=25.00,
            is_scheduled=False
        )
        
        # Add payments to loan
        self.loan.payments = [payment1, payment2]
        
        # Remaining principal should be reduced by the sum of principal payments
        expected_remaining = 100000.00 - (10000.00 + 5000.00)
        self.assertEqual(self.loan.remaining_principal, expected_remaining)


class TestPaymentModel(unittest.TestCase):
    """Test cases for Payment model"""

    def setUp(self):
        """Set up test environment before each test"""
        self.today = datetime.now().date()
        
        # Create a sample payment for testing
        self.payment = Payment(
            loan_id=1,
            payment_date=self.today,
            principal=10000.00,
            interest=500.00,
            fees=50.00,
            is_scheduled=False
        )

    def test_payment_creation(self):
        """Test that a payment is created with the correct attributes"""
        self.assertEqual(self.payment.loan_id, 1)
        self.assertEqual(self.payment.payment_date, self.today)
        self.assertEqual(self.payment.principal, 10000.00)
        self.assertEqual(self.payment.interest, 500.00)
        self.assertEqual(self.payment.fees, 50.00)
        self.assertFalse(self.payment.is_scheduled)

    def test_total_amount(self):
        """Test that total_amount returns the correct value"""
        # Total should be sum of principal, interest, and fees
        expected_total = 10000.00 + 500.00 + 50.00
        self.assertEqual(self.payment.total_amount, expected_total)


class TestSyndicatePortionModel(unittest.TestCase):
    """Test cases for SyndicatePortion model"""

    def setUp(self):
        """Set up test environment before each test"""
        self.today = datetime.now().date()
        
        # Create a sample syndicate portion for testing
        self.portion = SyndicatePortion(
            loan_id=1,
            participant_id=2,
            amount=50000.00,
            participation_date=self.today
        )

    def test_syndicate_portion_creation(self):
        """Test that a syndicate portion is created with the correct attributes"""
        self.assertEqual(self.portion.loan_id, 1)
        self.assertEqual(self.portion.participant_id, 2)
        self.assertEqual(self.portion.amount, 50000.00)
        self.assertEqual(self.portion.participation_date, self.today)


class TestCovenantModel(unittest.TestCase):
    """Test cases for Covenant model"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create a sample covenant for testing
        self.covenant = Covenant(
            loan_id=1,
            description="Debt-to-EBITDA ratio must stay below threshold",
            covenant_type="FINANCIAL",
            threshold_value=3.5
        )

    def test_covenant_creation(self):
        """Test that a covenant is created with the correct attributes"""
        self.assertEqual(self.covenant.loan_id, 1)
        self.assertEqual(self.covenant.description, "Debt-to-EBITDA ratio must stay below threshold")
        self.assertEqual(self.covenant.covenant_type, "FINANCIAL")
        self.assertEqual(self.covenant.threshold_value, 3.5)
        self.assertFalse(self.covenant.is_breached)

    def test_mark_breached(self):
        """Test that mark_breached sets the breach flag and date"""
        # Initially not breached
        self.assertFalse(self.covenant.is_breached)
        self.assertIsNone(self.covenant.breach_date)
        
        # Mark as breached
        today = datetime.now().date()
        self.covenant.mark_breached(today)
        
        # Now should be breached
        self.assertTrue(self.covenant.is_breached)
        self.assertEqual(self.covenant.breach_date, today)

    def test_clear_breach(self):
        """Test that clear_breach clears the breach flag and date"""
        # First mark as breached
        today = datetime.now().date()
        self.covenant.mark_breached(today)
        self.assertTrue(self.covenant.is_breached)
        
        # Then clear the breach
        self.covenant.clear_breach()
        
        # Should no longer be breached
        self.assertFalse(self.covenant.is_breached)
        self.assertIsNone(self.covenant.breach_date)


if __name__ == '__main__':
    unittest.main()