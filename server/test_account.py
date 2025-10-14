#!/usr/bin/env python3
"""
Quick script to check which Gmail account is authenticated
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Paths to secrets and token files
dir_path = os.path.dirname(os.path.realpath(__file__))
TOKEN_FILE = os.path.join(dir_path, 'secrets/token.json')
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def check_authenticated_account():
    """Check which Gmail account is currently authenticated"""
    
    if not os.path.exists(TOKEN_FILE):
        print(" No token.json file found. You need to authenticate first.")
        print(" Go to http://localhost:8080/authorize to authenticate.")
        return None
    
    try:
        # Load credentials
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not credentials.valid:
            print(" Refreshing expired credentials...")
            credentials.refresh(Request())
            with open(TOKEN_FILE, 'w') as token:
                token.write(credentials.to_json())
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Get user profile to find email address
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile['emailAddress']
        
        print(f" Authenticated Gmail account: {email_address}")
        print(f" To test the system, send emails TO: {email_address}")
        print(f"  Make sure to attach an image and include text in the email body")
        
        return email_address
        
    except Exception as e:
        print(f" Error checking account: {e}")
        return None

if __name__ == "__main__":
    print(" Checking authenticated Gmail account...")
    print("=" * 50)
    check_authenticated_account()
    print("=" * 50)
    print(" Web interface available at: http://localhost:8080")
    print(" Satellite frame (shows images from others): http://localhost:8080/satellite_frame")
    print(" Earth frame (shows images from of8179333@gmail.com): http://localhost:8080/earth_frame")