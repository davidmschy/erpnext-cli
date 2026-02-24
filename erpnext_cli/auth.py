"""
OAuth2 PKCE authentication and token management for ERPNext/Frappe.
Supports both OAuth2 PKCE flow and API key/secret authentication.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from cryptography.fernet import Fernet

from . import config


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth2 callback."""
    
    auth_code = None
    auth_error = None
    
    def do_GET(self):
        """Handle GET request from OAuth2 redirect."""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        if 'code' in query_params:
            CallbackHandler.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Authentication Successful</title></head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <script>window.close();</script>
                </body>
                </html>
            """)
        elif 'error' in query_params:
            CallbackHandler.auth_error = query_params.get('error_description', [query_params['error'][0]])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Error: {CallbackHandler.auth_error}</p>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Invalid callback')
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.
    
    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate code_verifier: 43-128 characters, URL-safe
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code_challenge: SHA256 hash of verifier, base64url encoded
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge


def get_authorization_url(
    base_url: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    scope: str = "openid all",
    state: Optional[str] = None
) -> str:
    """
    Build OAuth2 authorization URL with PKCE parameters.
    
    Args:
        base_url: ERPNext instance base URL
        client_id: OAuth2 client ID
        redirect_uri: Redirect URI (must match registered value)
        code_challenge: PKCE code challenge
        scope: OAuth2 scope
        state: Optional state parameter for CSRF protection
        
    Returns:
        Authorization URL
    """
    if state is None:
        state = secrets.token_urlsafe(16)
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'state': state
    }
    
    return f"{base_url}/api/method/frappe.integrations.oauth2.authorize?{urlencode(params)}"


def run_local_server(port: int = 8585, timeout: int = 120) -> str:
    """
    Start local HTTP server to capture OAuth2 callback.
    
    Args:
        port: Port to listen on (default: 8585)
        timeout: Timeout in seconds (default: 120)
        
    Returns:
        Authorization code
        
    Raises:
        TimeoutError: If callback not received within timeout
        RuntimeError: If OAuth error occurred
    """
    CallbackHandler.auth_code = None
    CallbackHandler.auth_error = None
    
    server = HTTPServer(('localhost', port), CallbackHandler)
    
    # Run server in background thread with timeout
    server_thread = Thread(target=server.handle_request, daemon=True)
    server_thread.start()
    
    start_time = time.time()
    while server_thread.is_alive():
        if time.time() - start_time > timeout:
            server.shutdown()
            raise TimeoutError(f"OAuth callback not received within {timeout} seconds")
        time.sleep(0.1)
    
    if CallbackHandler.auth_error:
        raise RuntimeError(f"OAuth authorization failed: {CallbackHandler.auth_error}")
    
    if not CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received")
    
    return CallbackHandler.auth_code


def exchange_code_for_token(
    base_url: str,
    client_id: str,
    code: str,
    code_verifier: str,
    redirect_uri: str
) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        base_url: ERPNext instance base URL
        client_id: OAuth2 client ID
        code: Authorization code from callback
        code_verifier: PKCE code verifier
        redirect_uri: Redirect URI (must match authorization request)
        
    Returns:
        Token dictionary with keys: access_token, refresh_token, expires_in, token_type
        
    Raises:
        RuntimeError: If token exchange fails
    """
    token_url = f"{base_url}/api/method/frappe.integrations.oauth2.get_token"
    
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'code_verifier': code_verifier
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        
        # Add expires_at timestamp for easier validation
        if 'expires_in' in token_data:
            token_data['expires_at'] = int(time.time()) + token_data['expires_in']
        
        return token_data
    except requests.RequestException as e:
        raise RuntimeError(f"Token exchange failed: {e}")


def refresh_access_token(
    base_url: str,
    client_id: str,
    refresh_token: str
) -> Dict[str, Any]:
    """
    Refresh access token using refresh token.
    
    Args:
        base_url: ERPNext instance base URL
        client_id: OAuth2 client ID
        refresh_token: Refresh token
        
    Returns:
        New token dictionary
        
    Raises:
        RuntimeError: If token refresh fails
    """
    token_url = f"{base_url}/api/method/frappe.integrations.oauth2.get_token"
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        
        if 'expires_in' in token_data:
            token_data['expires_at'] = int(time.time()) + token_data['expires_in']
        
        return token_data
    except requests.RequestException as e:
        raise RuntimeError(f"Token refresh failed: {e}")


def get_encryption_key() -> bytes:
    """
    Get or create encryption key for token storage.
    
    Returns:
        Fernet encryption key
    """
    key_path = config.get_config_dir() / '.key'
    
    if key_path.exists():
        with open(key_path, 'rb') as f:
            return f.read()
    else:
        # Generate new key
        key = Fernet.generate_key()
        # Secure key file: readable only by owner
        key_path.touch(mode=0o600)
        with open(key_path, 'wb') as f:
            f.write(key)
        return key


def get_tokens_path() -> Path:
    """Get the tokens file path."""
    return config.get_config_dir() / 'tokens.json'


def load_tokens() -> Dict[str, Dict[str, Any]]:
    """
    Load encrypted tokens from disk.
    
    Returns:
        Dictionary mapping site names to token data
    """
    tokens_path = get_tokens_path()
    
    if not tokens_path.exists():
        return {}
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        
        with open(tokens_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception as e:
        raise RuntimeError(f"Failed to load tokens: {e}")


def save_tokens(tokens: Dict[str, Dict[str, Any]]) -> None:
    """
    Save encrypted tokens to disk.
    
    Args:
        tokens: Dictionary mapping site names to token data
    """
    tokens_path = get_tokens_path()
    
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        
        json_data = json.dumps(tokens).encode('utf-8')
        encrypted_data = fernet.encrypt(json_data)
        
        # Secure tokens file: readable only by owner
        tokens_path.touch(mode=0o600, exist_ok=True)
        with open(tokens_path, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        raise RuntimeError(f"Failed to save tokens: {e}")


def store_token(site_name: str, token_data: Dict[str, Any]) -> None:
    """
    Store token data for a site.
    
    Args:
        site_name: Site identifier
        token_data: Token dictionary from OAuth2 response
    """
    tokens = load_tokens()
    tokens[site_name] = token_data
    save_tokens(tokens)


def get_token(site_name: str) -> Optional[Dict[str, Any]]:
    """
    Get token data for a site.
    
    Args:
        site_name: Site identifier
        
    Returns:
        Token dictionary or None if not found
    """
    tokens = load_tokens()
    return tokens.get(site_name)


def delete_token(site_name: str) -> None:
    """
    Delete token data for a site.
    
    Args:
        site_name: Site identifier
    """
    tokens = load_tokens()
    if site_name in tokens:
        del tokens[site_name]
        save_tokens(tokens)


def get_valid_token(site_name: str) -> str:
    """
    Get a valid access token for a site, refreshing if necessary.
    
    Args:
        site_name: Site identifier
        
    Returns:
        Valid access token
        
    Raises:
        ValueError: If no token found or refresh fails
    """
    token_data = get_token(site_name)
    if not token_data:
        raise ValueError(f"No authentication found for site '{site_name}'. Run 'erpnext login --site {site_name}'")
    
    # Check if token is API key/secret format
    if token_data.get('auth_type') == 'api_key':
        return f"token {token_data['api_key']}:{token_data['api_secret']}"
    
    # Check if OAuth token needs refresh
    expires_at = token_data.get('expires_at', 0)
    current_time = int(time.time())
    
    # Refresh if expired or expiring within 5 minutes
    if current_time >= (expires_at - 300):
        if 'refresh_token' not in token_data:
            raise ValueError(f"Token expired and no refresh token available for site '{site_name}'")
        
        # Get site config for refresh
        site_config = config.get_site(site_name)
        
        try:
            new_token_data = refresh_access_token(
                site_config['base_url'],
                site_config['client_id'],
                token_data['refresh_token']
            )
            
            # Preserve refresh_token if not included in response
            if 'refresh_token' not in new_token_data and 'refresh_token' in token_data:
                new_token_data['refresh_token'] = token_data['refresh_token']
            
            store_token(site_name, new_token_data)
            return new_token_data['access_token']
        except RuntimeError as e:
            raise ValueError(f"Failed to refresh token for site '{site_name}': {e}")
    
    return token_data['access_token']


def store_api_key(site_name: str, api_key: str, api_secret: str) -> None:
    """
    Store API key/secret authentication for a site.
    
    Args:
        site_name: Site identifier
        api_key: API key
        api_secret: API secret
    """
    token_data = {
        'auth_type': 'api_key',
        'api_key': api_key,
        'api_secret': api_secret
    }
    store_token(site_name, token_data)


def perform_oauth_flow(
    site_name: str,
    base_url: str,
    client_id: str,
    scope: str = "openid all",
    port: int = 8585
) -> Dict[str, Any]:
    """
    Perform complete OAuth2 PKCE flow.
    
    Args:
        site_name: Site identifier
        base_url: ERPNext instance base URL
        client_id: OAuth2 client ID
        scope: OAuth2 scope
        port: Local server port for callback
        
    Returns:
        Token data dictionary
        
    Raises:
        RuntimeError: If OAuth flow fails
    """
    redirect_uri = f"http://localhost:{port}/callback"
    
    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce_pair()
    
    # Build authorization URL
    auth_url = get_authorization_url(
        base_url=base_url,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        scope=scope
    )
    
    # Open browser
    print(f"Opening browser for authentication...")
    print(f"If the browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)
    
    # Wait for callback
    print(f"Waiting for callback on http://localhost:{port}/callback ...")
    auth_code = run_local_server(port=port)
    
    # Exchange code for token
    print("Exchanging authorization code for token...")
    token_data = exchange_code_for_token(
        base_url=base_url,
        client_id=client_id,
        code=auth_code,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri
    )
    
    # Store token
    store_token(site_name, token_data)
    
    return token_data
