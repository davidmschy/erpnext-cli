"""
ERPNext CLI - OAuth2 PKCE authentication and Python SDK for ERPNext/Frappe.

This package provides both a command-line interface and a Python SDK for
interacting with ERPNext/Frappe instances using OAuth2 PKCE authentication.

CLI Usage:
    $ erpnext add-site mysite --url https://mysite.erpnext.com --client-id abc123
    $ erpnext login --site mysite
    $ erpnext whoami
    $ erpnext list Lead --filters '{"status": "Open"}' --limit 5

SDK Usage:
    from erpnext_cli import ERPNextClient
    
    client = ERPNextClient(site_name='mysite')
    leads = client.list_docs('Lead', filters={'status': 'Open'})
    
    for lead in leads:
        print(f"{lead['name']}: {lead['lead_name']}")

For more information, see: https://github.com/davidmschy/erpnext-cli
"""

from .client import ERPNextClient, ERPNextError
from .config import (
    add_site,
    remove_site,
    get_site,
    list_sites,
    set_default,
    get_default_site,
)
from .auth import (
    perform_oauth_flow,
    store_api_key,
    get_valid_token,
    delete_token,
)

__version__ = "0.1.0"
__author__ = "GeniNow"
__email__ = "david@geniinow.com"

__all__ = [
    # Client
    "ERPNextClient",
    "ERPNextError",
    # Config
    "add_site",
    "remove_site",
    "get_site",
    "list_sites",
    "set_default",
    "get_default_site",
    # Auth
    "perform_oauth_flow",
    "store_api_key",
    "get_valid_token",
    "delete_token",
]
