#!/usr/bin/env python3
"""
ERPNext Team User Creation Script
==================================

This script creates a new ERPNext user account for a team member, assigns them
a role, and generates their API credentials for use with erpnext-cli.

PREREQUISITES:
- ERPNext/Frappe v13+ instance
- Admin user API key and secret
- Network access to your ERPNext instance

USAGE:
    python create_team_user.py \\
        --url https://your-site.frappe.cloud \\
        --api-key <admin_api_key> \\
        --api-secret <admin_api_secret> \\
        --email john.doe@example.com \\
        --first-name John \\
        --last-name Doe \\
        --role "Sales User"

WHAT IT DOES:
1. Creates a new User document in ERPNext
2. Assigns the specified role (default: Sales User)
3. Generates API key and secret for the user
4. Prints the credentials and CLI login command

AFTER RUNNING:
- Share the printed credentials securely with the team member
- Team member can authenticate with: erpnext login --site <site> --api-key ... --api-secret ...
- API credentials can be regenerated anytime from ERPNext UI

COMMON ROLES:
- Sales User: CRM access, lead/opportunity management
- Sales Manager: Full sales + reporting access
- Projects User: Project and task management
- System Manager: Full admin access (use carefully)
- Custom roles: Any role defined in your ERPNext instance
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found.")
    print("Install it with: pip install requests")
    sys.exit(1)


class ERPNextUserManager:
    """Handle user creation and API key generation in ERPNext."""
    
    def __init__(self, url: str, api_key: str, api_secret: str):
        """
        Initialize the user manager.
        
        Args:
            url: Base URL of ERPNext instance
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
        """Test API connectivity and authentication."""
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
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def user_exists(self, email: str) -> bool:
        """
        Check if a user already exists.
        
        Args:
            email: User email address
        
        Returns:
            True if user exists, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.base_url}/api/resource/User/{email}',
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        send_welcome_email: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new user in ERPNext.
        
        Args:
            email: User email address (also used as username)
            first_name: User's first name
            last_name: User's last name
            send_welcome_email: Whether to send welcome email
        
        Returns:
            User document data
        
        Raises:
            Exception if creation fails
        """
        # Check if user already exists
        if self.user_exists(email):
            raise Exception(f"User {email} already exists")
        
        payload = {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "send_welcome_email": 1 if send_welcome_email else 0,
            "enabled": 1,
            "user_type": "System User"
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/api/resource/User',
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ User '{email}' created successfully")
                return data.get('data', {})
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
    
    def assign_role(self, email: str, role: str) -> bool:
        """
        Assign a role to a user.
        
        Args:
            email: User email address
            role: Role name to assign
        
        Returns:
            True if successful
        
        Raises:
            Exception if assignment fails
        """
        payload = {
            "doctype": "Has Role",
            "parent": email,
            "parenttype": "User",
            "parentfield": "roles",
            "role": role
        }
        
        try:
            response = self.session.post(
                f'{self.base_url}/api/resource/Has Role',
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                print(f"✓ Role '{role}' assigned to {email}")
                return True
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
    
    def generate_api_keys(self, email: str) -> Dict[str, str]:
        """
        Generate API key and secret for a user.
        
        Args:
            email: User email address
        
        Returns:
            Dictionary with api_key and api_secret
        
        Raises:
            Exception if generation fails
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/method/frappe.core.doctype.user.user.generate_keys',
                json={"user": email},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', {})
                
                api_key = message.get('api_key')
                api_secret = message.get('api_secret')
                
                if not api_key or not api_secret:
                    raise Exception("Response missing API credentials")
                
                print(f"✓ API keys generated for {email}")
                return {
                    'api_key': api_key,
                    'api_secret': api_secret
                }
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
    
    def print_credentials(self, email: str, credentials: Dict[str, str], role: str):
        """
        Print user credentials and setup instructions.
        
        Args:
            email: User email address
            credentials: Dictionary with api_key and api_secret
            role: Assigned role
        """
        # Extract site name
        site_name = self.base_url.replace('https://', '').replace('http://', '').split('/')[0]
        site_slug = site_name.split('.')[0]
        
        api_key = credentials['api_key']
        api_secret = credentials['api_secret']
        
        print("\n" + "="*70)
        print("USER ACCOUNT CREATED")
        print("="*70)
        print(f"Email:     {email}")
        print(f"Role:      {role}")
        print(f"Site:      {site_name}")
        print(f"Portal:    {self.base_url}")
        
        print("\n" + "="*70)
        print("API CREDENTIALS (SHARE SECURELY)")
        print("="*70)
        print(f"API Key:    {api_key}")
        print(f"API Secret: {api_secret}")
        
        print("\n" + "="*70)
        print("SETUP INSTRUCTIONS FOR TEAM MEMBER")
        print("="*70)
        print("\n1. Install erpnext-cli:")
        print("   pip install erpnext-cli")
        
        print("\n2. Add the site:")
        print(f"   erpnext add-site {site_slug} --url {self.base_url}")
        
        print("\n3. Login with API credentials:")
        print(f"   erpnext login --site {site_slug} --api-key {api_key} --api-secret {api_secret}")
        
        print("\n4. Test connection:")
        print(f"   erpnext whoami --site {site_slug}")
        print(f"   # Should return: {email}")
        
        print("\n5. Example queries:")
        print(f"   erpnext list Lead --site {site_slug} --limit 5")
        print(f"   erpnext get Lead LEAD-00001 --site {site_slug}")
        
        print("\n" + "="*70)
        print("SECURITY NOTES")
        print("="*70)
        print("• API credentials grant full access with assigned role permissions")
        print("• Store credentials securely (do not commit to git)")
        print("• Regenerate keys if compromised via ERPNext UI:")
        print(f"  {self.base_url}/app/user/{email}")
        print("• Keys can also be regenerated by re-running this script")
        print("="*70 + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Create ERPNext team member user account with API access',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create sales user
  python create_team_user.py \\
      --url https://geniinow.v.frappe.cloud \\
      --api-key abc123... \\
      --api-secret xyz789... \\
      --email john@example.com \\
      --first-name John \\
      --last-name Porter \\
      --role "Sales User"
  
  # Create system manager
  python create_team_user.py \\
      --url https://example.frappe.cloud \\
      --api-key abc123... \\
      --api-secret xyz789... \\
      --email admin@example.com \\
      --first-name Jane \\
      --last-name Admin \\
      --role "System Manager"
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
        '--email',
        required=True,
        help='New user email address'
    )
    parser.add_argument(
        '--first-name',
        required=True,
        help='User first name'
    )
    parser.add_argument(
        '--last-name',
        required=True,
        help='User last name'
    )
    parser.add_argument(
        '--role',
        default='Sales User',
        help='Role to assign (default: Sales User)'
    )
    parser.add_argument(
        '--send-welcome-email',
        action='store_true',
        help='Send welcome email to user'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("ERPNext Team User Creation")
    print("="*70 + "\n")
    
    # Initialize manager
    manager = ERPNextUserManager(
        url=args.url,
        api_key=args.api_key,
        api_secret=args.api_secret
    )
    
    # Test connection
    if not manager.test_connection():
        print("\n✗ Setup failed: Could not connect to ERPNext")
        sys.exit(1)
    
    print()
    
    # Create user
    try:
        user_data = manager.create_user(
            email=args.email,
            first_name=args.first_name,
            last_name=args.last_name,
            send_welcome_email=args.send_welcome_email
        )
        
        # Assign role
        manager.assign_role(args.email, args.role)
        
        # Generate API keys
        credentials = manager.generate_api_keys(args.email)
        
        # Print instructions
        manager.print_credentials(args.email, credentials, args.role)
        
    except Exception as e:
        print(f"\n✗ Failed to create user: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
