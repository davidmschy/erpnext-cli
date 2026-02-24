#!/usr/bin/env python3
"""
ERPNext Connected App Setup Script
===================================

This script registers an OAuth2 Connected App in your Frappe/ERPNext instance
to enable the erpnext-cli tool to authenticate users via OAuth2 + PKCE flow.

PREREQUISITES:
- ERPNext/Frappe v13+ instance
- Admin user API key and secret (generate via: User > API Access > Generate Keys)
- Network access to your ERPNext instance

USAGE:
    python setup_connected_app.py \\
        --url https://your-site.frappe.cloud \\
        --api-key <your_admin_api_key> \\
        --api-secret <your_admin_api_secret>

WHAT IT DOES:
1. Connects to your ERPNext instance using admin API credentials
2. Creates a "Connected App" document for OAuth2 authentication
3. Returns the client_id needed for erpnext-cli configuration
4. Provides the exact command for team members to connect

AFTER RUNNING:
- Share the printed "erpnext add-site" command with your team
- Team members can then authenticate via OAuth2 flow (no API keys needed)
- The Connected App uses PKCE for secure public client authentication

NOTE:
- This script only needs to be run ONCE per ERPNext instance
- If the Connected App already exists, you can retrieve the client_id from:
  ERPNext > Connected App > [your-app-name] > Client ID
"""

import argparse
import json
import sys
import urllib.parse
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found.")
    print("Install it with: pip install requests")
    sys.exit(1)


class ERPNextConnectedAppSetup:
    """Handle Connected App creation in ERPNext via REST API."""
    
    def __init__(self, url: str, api_key: str, api_secret: str):
        """
        Initialize the setup client.
        
        Args:
            url: Base URL of ERPNext instance (e.g., https://example.frappe.cloud)
            api_key: Admin user API key
            api_secret: Admin user API secret
        """
        self.base_url = url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_connection(self) -> bool:
        """
        Test API connectivity and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/method/frappe.auth.get_logged_user',
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                user = data.get('message', 'unknown')
                print(f"✓ Connected to {self.base_url} as {user}")
                return True
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def create_connected_app(
        self,
        app_name: str,
        redirect_uri: str,
        scope: str
    ) -> Dict[str, Any]:
        """
        Create a Connected App document in ERPNext.
        
        Args:
            app_name: Name for the Connected App
            redirect_uri: OAuth2 redirect URI
            scope: OAuth2 scopes (space-separated)
        
        Returns:
            Dictionary with client_id, client_secret, and app details
        
        Raises:
            Exception if creation fails
        """
        payload = {
            "app_name": app_name,
            "redirect_uris": redirect_uri,
            "scopes": scope,
            "response_type": "Code"
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/api/resource/Connected App',
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                app_data = data.get('data', {})
                
                # Extract client credentials
                client_id = app_data.get('client_id')
                client_secret = app_data.get('client_secret')
                
                if not client_id:
                    raise Exception("Response missing client_id")
                
                print(f"✓ Connected App '{app_name}' created successfully!")
                return {
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'app_name': app_name,
                    'redirect_uri': redirect_uri,
                    'scope': scope
                }
            
            elif response.status_code == 409 or 'already exists' in response.text.lower():
                print(f"⚠ Connected App '{app_name}' already exists")
                print(f"  To retrieve client_id, go to: {self.base_url}/app/connected-app")
                print(f"  Or delete the existing app and re-run this script")
                sys.exit(1)
            
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get('exception') or error_data.get('message') or error_msg
                except:
                    pass
                
                raise Exception(f"HTTP {response.status_code}: {error_msg}")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
    
    def print_setup_instructions(self, app_data: Dict[str, Any]):
        """
        Print setup instructions and CLI commands.
        
        Args:
            app_data: Dictionary containing client credentials and app config
        """
        client_id = app_data['client_id']
        client_secret = app_data['client_secret']
        app_name = app_data['app_name']
        
        # Extract site name from URL
        site_name = self.base_url.replace('https://', '').replace('http://', '').split('/')[0]
        site_slug = site_name.split('.')[0]  # e.g., geniinow from geniinow.v.frappe.cloud
        
        print("\n" + "="*70)
        print("CONNECTED APP CREDENTIALS")
        print("="*70)
        print(f"App Name:      {app_name}")
        print(f"Client ID:     {client_id}")
        print(f"Client Secret: {client_secret}")
        print(f"Redirect URI:  {app_data['redirect_uri']}")
        print(f"Scopes:        {app_data['scope']}")
        
        print("\n" + "="*70)
        print("ADMIN SETUP COMMAND (Run this once as admin)")
        print("="*70)
        print(f"erpnext add-site {site_slug} --url {self.base_url} --client-id {client_id}")
        
        print("\n" + "="*70)
        print("SHARE WITH TEAM MEMBERS")
        print("="*70)
        print("\n1. Install erpnext-cli:")
        print("   pip install erpnext-cli")
        
        print("\n2. Add the site:")
        print(f"   erpnext add-site {site_slug} --url {self.base_url} --client-id {client_id}")
        
        print("\n3. Login (opens browser for OAuth):")
        print(f"   erpnext login --site {site_slug}")
        
        print("\n4. Test connection:")
        print(f"   erpnext whoami --site {site_slug}")
        
        print("\n" + "="*70)
        print("NOTES")
        print("="*70)
        print("• The client_secret is stored in Frappe and NOT needed for PKCE flow")
        print("• Team members authenticate via browser (OAuth2 + PKCE)")
        print("• No need to share API keys with team members")
        print(f"• Connected App can be managed at: {self.base_url}/app/connected-app/{app_name}")
        print("="*70 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Setup OAuth2 Connected App for erpnext-cli',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic setup with defaults
  python setup_connected_app.py \\
      --url https://geniinow.v.frappe.cloud \\
      --api-key abc123... \\
      --api-secret xyz789...
  
  # Custom app name and redirect
  python setup_connected_app.py \\
      --url https://example.frappe.cloud \\
      --api-key abc123... \\
      --api-secret xyz789... \\
      --app-name "My CLI Tool" \\
      --redirect-uri http://localhost:9999/callback
        """
    )
    
    parser.add_argument(
        '--url',
        required=True,
        help='ERPNext base URL (e.g., https://geniinow.v.frappe.cloud)'
    )
    parser.add_argument(
        '--api-key',
        required=True,
        help='Admin user API key'
    )
    parser.add_argument(
        '--api-secret',
        required=True,
        help='Admin user API secret'
    )
    parser.add_argument(
        '--app-name',
        default='erpnext-cli',
        help='Name for the Connected App (default: erpnext-cli)'
    )
    parser.add_argument(
        '--redirect-uri',
        default='http://localhost:8585/callback',
        help='OAuth2 redirect URI (default: http://localhost:8585/callback)'
    )
    parser.add_argument(
        '--scope',
        default='openid all',
        help='OAuth2 scopes (default: "openid all")'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("ERPNext Connected App Setup")
    print("="*70 + "\n")
    
    # Initialize setup client
    setup = ERPNextConnectedAppSetup(
        url=args.url,
        api_key=args.api_key,
        api_secret=args.api_secret
    )
    
    # Test connection
    if not setup.test_connection():
        print("\n✗ Setup failed: Could not connect to ERPNext")
        print("  Check your URL and API credentials")
        sys.exit(1)
    
    print()
    
    # Create Connected App
    try:
        app_data = setup.create_connected_app(
            app_name=args.app_name,
            redirect_uri=args.redirect_uri,
            scope=args.scope
        )
        
        # Print instructions
        setup.print_setup_instructions(app_data)
        
    except Exception as e:
        print(f"\n✗ Failed to create Connected App: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
