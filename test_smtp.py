#!/usr/bin/env python3
"""
SMTP Configuration and Diagnostic Script
Run this to test if email sending is properly configured
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ai_orchestration.services.mail_service import diagnose_smtp_config, _send_sync
from ai_orchestration.core.config import SMTP_USER, SMTP_HOST, SMTP_PORT
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("\n" + "="*70)
    print("SIGNLY EMAIL SMTP DIAGNOSTIC TOOL")
    print("="*70 + "\n")
    
    # Run diagnostic
    config_ok = diagnose_smtp_config()
    
    if not config_ok:
        print("\n⚠️  SMTP configuration check failed!")
        print("\nPlease verify your .env file or environment variables:")
        print(f"  - SMTP_HOST should be 'smtp.gmail.com'")
        print(f"  - SMTP_PORT should be 465 (SSL)")
        print(f"  - SMTP_USER should be your Gmail address")
        print(f"  - SMTP_PASS should be a 16-char App Password from Google")
        sys.exit(1)
    
    # Try sending a test email
    print("\n→ Would you like to send a test email? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        test_email = input("Enter test email address: ").strip()
        if not test_email or '@' not in test_email:
            print("✗ Invalid email address")
            sys.exit(1)
        
        print(f"\n→ Sending test email to {test_email}...")
        
        test_html = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>SMTP Configuration Test</h2>
            <p>If you received this email, your SMTP configuration is working correctly!</p>
            <p style="color: green;">✓ Email system is operational</p>
        </body>
        </html>
        """
        
        success = _send_sync(
            test_email, 
            "Signly SMTP Test",
            test_html,
            code=None
        )
        
        if success:
            print(f"\n✓ Test email sent successfully to {test_email}")
            print("  Check the email to confirm delivery.")
        else:
            print(f"\n✗ Failed to send test email")
            print("  Check the error messages above for details.")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("Diagnostic complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
