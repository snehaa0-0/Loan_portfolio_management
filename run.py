#!/usr/bin/env python
"""
Main entry point for the Syndicated Loan Manager application.
"""
import sys
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Syndicated Loan Manager')
    
    # Primary commands
    parser.add_argument('command', choices=['run', 'init-db', 'sample-data', 'report'],
                        help='Command to execute')
    
    # UI options
    parser.add_argument('--loan', type=int, help='Loan ID to display details for')
    
    # Reporting options
    parser.add_argument('--report-type', choices=[
        'portfolio', 'loan-performance', 'syndication', 'maturity', 'covenant'
    ], help='Type of report to generate')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--loan-id', type=int, help='Loan ID for loan-specific reports')
    parser.add_argument('--export', choices=['csv', 'excel'], 
                       help='Export portfolio data in specified format')
    
    return parser.parse_args()

def init_required_modules():
    """Import required modules with error handling."""
    try:
        global init_app, get_session, LoanManager, LoanReporter
        global display_dashboard, loan_details
        global db_init, sample_data
        
        from app import init_app, get_session
        from app.loan_manager import LoanManager
        from app.reporting import LoanReporter
        from ui.dashboard import display_dashboard
        from ui.loan_view import loan_details
        import scripts.initialize_db as db_init
        import scripts.sample_data as sample_data
        
        return True
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        print(f"Error: Missing required module - {e}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        if args.command == 'init-db':
            print("Initializing database...")
            # Import only the modules needed for this command
            try:
                import scripts.initialize_db as db_init
                db_init.main()
                print("Database initialized successfully.")
            except ImportError as e:
                logger.error(f"Failed to import database initialization module: {e}")
                print(f"Error: Cannot initialize database - {e}")
                return 1
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                print(f"Error: Database initialization failed - {e}")
                return 1
            
        elif args.command == 'sample-data':
            print("Loading sample data...")
            try:
                import scripts.sample_data as sample_data
                sample_data.main()
                print("Sample data loaded successfully.")
            except ImportError as e:
                logger.error(f"Failed to import sample data module: {e}")
                print(f"Error: Cannot load sample data - {e}")
                return 1
            except Exception as e:
                logger.error(f"Sample data loading failed: {e}")
                print(f"Error: Sample data loading failed - {e}")
                return 1
            
        elif args.command == 'report':
            print("Generating report...")
            
            # Check if required modules are available
            if not init_required_modules():
                return 1
            
            # Initialize application
            try:
                init_app()
                session = get_session()
            except Exception as e:
                logger.error(f"Failed to initialize application: {e}")
                print(f"Error: Application initialization failed - {e}")
                return 1
            
            try:
                reporter = LoanReporter(session)
                
                if args.export:
                    file_path = reporter.export_portfolio_data(format=args.export)
                    print(f"Portfolio data exported to: {file_path}")
                    
                elif args.report_type == 'portfolio':
                    data = reporter.generate_portfolio_summary(args.output)
                    print(f"Portfolio summary:")
                    print(f"  Total portfolio size: ${data['total_portfolio_size']:,.2f}")
                    print(f"  Active loans: {data['active_loans_count']}")
                    print(f"  Syndication percentage: {data['syndication_percentage']:.2f}%")
                    
                elif args.report_type == 'loan-performance':
                    if not args.loan_id:
                        print("Error: --loan-id is required for loan-performance report")
                        return 1
                        
                    data = reporter.generate_loan_performance_report(args.loan_id, args.output)
                    metrics = data.get('loan_metrics', {})
                    print(f"Loan performance report for loan ID {args.loan_id}:")
                    print(f"  Loan number: {metrics.get('loan_number', 'N/A')}")
                    print(f"  Borrower: {metrics.get('borrower_name', 'N/A')}")
                    print(f"  Original amount: ${metrics.get('original_amount', 0):,.2f}")
                    print(f"  Remaining principal: ${metrics.get('remaining_principal', 0):,.2f}")
                    print(f"  Days to maturity: {metrics.get('days_to_maturity', 'N/A')}")
                    
                elif args.report_type == 'syndication':
                    data = reporter.generate_syndication_report(args.output)
                    loans_count = len(data.get('loans', []))
                    print(f"Syndication report generated for {loans_count} loans")
                    if args.output:
                        print(f"Report saved to {args.output}")
                        
                elif args.report_type == 'maturity':
                    data = reporter.generate_maturity_profile(args.output)
                    print("Maturity profile by quarter:")
                    for period, amount in data.items():
                        print(f"  {period}: ${amount:,.2f}")
                        
                elif args.report_type == 'covenant':
                    data = reporter.generate_covenant_compliance_report()
                    print(f"Covenant report generated for {len(data)} loans")
                    for loan_number, loan_data in data.items():
                        print(f"\nLoan {loan_number} - {loan_data.get('borrower', 'Unknown')}:")
                        for i, covenant in enumerate(loan_data.get('covenants', []), 1):
                            print(f"  {i}. {covenant.get('type', 'Unknown')}: {covenant.get('description', 'N/A')}")
                            if covenant.get('threshold') is not None:
                                print(f"     Threshold: {covenant.get('threshold')}")
                else:
                    print(f"Error: Unknown report type '{args.report_type}'")
                    return 1
            
            except Exception as e:
                logger.error(f"Report generation failed: {e}")
                print(f"Error: Report generation failed - {e}")
                return 1
            finally:
                try:
                    session.close()
                except Exception:
                    pass
            
        elif args.command == 'run':
            # Check if web UI is requested (default) or CLI
            try:
                import webbrowser
                import threading
                import time
                from flask import Flask, redirect, url_for
                from app import create_app
                
                # Create Flask app
                app = create_app()
                
                # Register UI blueprints
                from ui.dashboard import dashboard_bp
                from ui.loan_view import loan_view_bp
                
                app.register_blueprint(dashboard_bp)
                app.register_blueprint(loan_view_bp)
                
                # Add root route redirect
                @app.route('/')
                def index():
                    return redirect(url_for('dashboard.index'))
                
                def open_browser():
                    """Open browser after a short delay to ensure server is running."""
                    time.sleep(1.5)
                    webbrowser.open('http://127.0.0.1:5000')
                
                print("Starting web server at http://127.0.0.1:5000")
                print("Opening browser automatically...")
                print("Press Ctrl+C to stop")
                
                # Start browser opening in separate thread
                threading.Thread(target=open_browser, daemon=True).start()
                
                app.run(host='127.0.0.1', port=5000, debug=True)
                
            except ImportError:
                # Fall back to CLI if Flask not available
                if not init_required_modules():
                    return 1
                
                init_app()
                session = get_session()
                
                try:
                    if args.loan:
                        loan_details(session, args.loan)
                    else:
                        display_dashboard(session)
                finally:
                    session.close()
        else:
            print(f"Error: Unknown command '{args.command}'")
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: An unexpected error occurred - {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())