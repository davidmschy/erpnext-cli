# ERPNext CLI - Package Summary

## Overview

Production-quality Python CLI and SDK for ERPNext/Frappe with OAuth2 PKCE authentication.

**Created**: 2024-02-24  
**Version**: 0.1.0  
**Location**: `/home/user/files/code/erpnext-cli/`

## Package Structure

```
code/erpnext-cli/
├── pyproject.toml          # Modern Python package configuration
├── setup.py                # Backward compatibility setup
├── README.md               # Comprehensive documentation (15KB)
├── LICENSE.txt             # MIT License
├── MANIFEST.in             # Package manifest
├── gitignore.txt           # Git ignore file (rename to .gitignore)
└── erpnext_cli/            # Main package directory
    ├── __init__.py         # Public API exports
    ├── config.py           # Site/profile configuration (5.3KB)
    ├── auth.py             # OAuth2 PKCE + token management (14.5KB)
    ├── client.py           # ERPNextClient SDK class (12.8KB)
    └── cli.py              # Click CLI commands (15.1KB)
```

**Total Package Size**: ~65KB of production code + documentation

## Key Features Implemented

### 1. OAuth2 PKCE Authentication Flow
- Full PKCE (Proof Key for Code Exchange) implementation
- Browser-based authorization with local callback server
- Automatic token refresh when expired
- Secure token storage with Fernet encryption

### 2. API Key/Secret Authentication
- Headless authentication for AI agents
- No browser required
- Stored encrypted alongside OAuth tokens

### 3. Multi-Site Management
- Configure multiple ERPNext instances
- Switch between sites easily
- Default site support
- Isolated token storage per site

### 4. CLI Commands
- `erpnext login` - OAuth2 or API key auth
- `erpnext logout` - Clear tokens
- `erpnext whoami` - Check authenticated user
- `erpnext sites` - List configured sites
- `erpnext add-site` - Register new site
- `erpnext remove-site` - Remove site config
- `erpnext get` - Fetch single document
- `erpnext list` - List documents with filters
- `erpnext call` - Call API methods
- `erpnext config` - Configuration management

### 5. Python SDK
- `ERPNextClient` class for programmatic access
- Full CRUD operations (get_doc, list_docs, create_doc, update_doc, delete_doc)
- Low-level HTTP methods (get, post, put, delete)
- Method calling via `call()`
- Automatic authentication header management
- Rich error handling with `ERPNextError`

### 6. Security Features
- Encrypted token storage using Fernet (symmetric encryption)
- Machine-specific encryption key in `~/.config/erpnext-cli/.key`
- File permissions set to 0600 for sensitive files
- No keyring dependency (works in headless environments)
- Token auto-refresh prevents expired token exposure

## Installation Methods

### Option 1: Direct from GitHub (Recommended)
```bash
pip install git+https://github.com/davidmschy/erpnext-cli.git
```

### Option 2: Local Development Install
```bash
cd /home/user/files/code/erpnext-cli
pip install -e .
```

### Option 3: Build and Install Wheel
```bash
cd /home/user/files/code/erpnext-cli
pip install build
python -m build
pip install dist/erpnext_cli-0.1.0-py3-none-any.whl
```

## Usage Examples

### CLI - Human Interactive
```bash
# Setup
erpnext add-site geniinow --url https://geniinow.v.frappe.cloud --client-id abc123
erpnext login --site geniinow

# Use
erpnext whoami
erpnext list Lead --filters '{"status": "Open"}' --limit 10
erpnext get Lead LEAD-2024-00001
```

### CLI - AI Agent (Headless)
```bash
# One-step setup and auth
erpnext login --site geniinow \
  --url https://geniinow.v.frappe.cloud \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET

# Use immediately
erpnext list Project --filters '{"status": "Open"}'
```

### Python SDK
```python
from erpnext_cli import ERPNextClient

# Initialize (uses stored credentials)
client = ERPNextClient(site_name='geniinow')

# Query documents
leads = client.list_docs('Lead', 
    filters={'status': 'Open'},
    fields=['name', 'lead_name', 'status'],
    limit_page_length=10
)

# CRUD operations
lead = client.get_doc('Lead', 'LEAD-2024-00001')
new_lead = client.create_doc('Lead', {'lead_name': 'John Doe', ...})
client.update_doc('Lead', 'LEAD-2024-00001', {'status': 'Qualified'})
client.delete_doc('Lead', 'LEAD-2024-00001')

# Call methods
user = client.get_logged_user()
result = client.call('custom_app.api.method', param1='value')
```

## Configuration Files

### Location
- Config dir: `~/.config/erpnext-cli/`
- Config: `config.json` (site definitions)
- Tokens: `tokens.json` (encrypted credentials)
- Key: `.key` (encryption key, 0600 permissions)

### Config Schema
```json
{
  "default_site": "geniinow",
  "sites": {
    "geniinow": {
      "base_url": "https://geniinow.v.frappe.cloud",
      "client_id": "abc123xyz",
      "scope": "openid all"
    }
  }
}
```

### Token Schema (encrypted)
```json
{
  "geniinow": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": 1740423600,
    "token_type": "Bearer"
  }
}
```

## ERPNext Admin Setup Required

Before team members can use this tool, an ERPNext Administrator must:

1. Go to **Setup → Integrations → Connected App**
2. Create new Connected App:
   - **App Name**: ERPNext CLI
   - **Redirect URIs**: `http://localhost:8585/callback`
   - **Scopes**: `openid all` (or specific scopes)
   - **Grant Type**: Authorization Code
3. Save and distribute the **Client ID** to team members

## Dependencies

- **requests** (>=2.28): HTTP client
- **click** (>=8.0): CLI framework
- **cryptography** (>=41.0): Token encryption (Fernet)
- **rich** (>=13.0): Rich CLI formatting

All dependencies are automatically installed via pip.

## Architecture Highlights

### OAuth2 PKCE Flow (auth.py)
1. Generate code_verifier (43-128 chars, URL-safe random)
2. Generate code_challenge (SHA256 hash of verifier, base64url encoded)
3. Build authorization URL with challenge
4. Start local HTTP server on port 8585
5. Open browser to authorization URL
6. Capture callback with authorization code
7. Exchange code + verifier for tokens
8. Store encrypted tokens

### Token Management
- Tokens checked for expiry before each request
- Auto-refresh if expires within 5 minutes
- Refresh token persisted across refreshes
- Encryption key unique per machine
- Supports both OAuth2 and API key formats

### SDK Architecture (client.py)
- `ERPNextClient` wraps `requests.Session`
- Authentication header injected via `_get_auth_header()`
- Error responses parsed and raised as `ERPNextError`
- High-level DocType methods wrap REST endpoints
- Low-level HTTP methods for custom endpoints

### CLI Architecture (cli.py)
- Built with Click framework
- Rich library for formatted output
- JSON syntax highlighting with Pygments theme
- Table rendering for list results
- Panel rendering for special outputs
- Comprehensive error handling

## Next Steps for Deployment

### 1. Push to GitHub
```bash
cd /home/user/files/code/erpnext-cli
git init
mv gitignore.txt .gitignore
git add .
git commit -m "Initial commit: ERPNext CLI v0.1.0 with OAuth2 PKCE"
git remote add origin https://github.com/davidmschy/erpnext-cli.git
git push -u origin main
```

### 2. Team Rollout
- Create Connected Apps in each ERPNext instance (geniinow, fbx, etc.)
- Document the Client IDs in team wiki
- Share installation instructions: `pip install git+https://github.com/davidmschy/erpnext-cli.git`
- Team members run: `erpnext add-site` and `erpnext login`

### 3. AI Agent Integration
- Generate API keys for each agent's assigned ERPNext user
- Store in agent environment/config: `erpnext login --site X --api-key K --api-secret S`
- Import in agent code: `from erpnext_cli import ERPNextClient`
- Use in workflows: `client = ERPNextClient(site_name='geniinow'); leads = client.get_list('Lead')`

### 4. CI/CD Integration
```yaml
# Example GitHub Actions
- name: Install ERPNext CLI
  run: pip install git+https://github.com/davidmschy/erpnext-cli.git

- name: Authenticate
  run: erpnext login --site test --api-key ${{ secrets.ERPNEXT_KEY }} --api-secret ${{ secrets.ERPNEXT_SECRET }}

- name: Run sync
  run: python scripts/sync_erpnext.py
```

## Testing Checklist

Before production use, test:

- [ ] OAuth2 login flow (browser-based)
- [ ] API key login (headless)
- [ ] Token refresh (wait for expiry or mock)
- [ ] Multi-site switching
- [ ] Document CRUD operations
- [ ] Method calling
- [ ] Error handling (invalid credentials, network errors)
- [ ] Config management (add/remove sites)
- [ ] Python SDK import and usage
- [ ] CLI help commands

## Known Limitations

1. **PKCE only**: Does not support client_secret-based flows (by design for security)
2. **Local callback**: OAuth requires localhost redirect (cloud-hosted agents must use API keys)
3. **Single-user tokens**: Each CLI installation has separate tokens (no shared token store)
4. **No token revocation UI**: Must revoke in ERPNext web UI
5. **Basic error messages**: Some Frappe errors are verbose/technical

## Future Enhancements (Optional)

- [ ] Support for custom CA certificates
- [ ] Bulk operations (batch create/update)
- [ ] Export to CSV/Excel
- [ ] Interactive mode (REPL)
- [ ] Shell completion (bash/zsh)
- [ ] Detailed logging mode
- [ ] Token expiry warnings
- [ ] Site health check command
- [ ] Migration from python-frappe-client

## Support Resources

- **ERPNext API Docs**: https://frappeframework.com/docs/user/en/api
- **OAuth2 PKCE Spec**: RFC 7636
- **Frappe REST API**: `{base_url}/api/resource/{doctype}`
- **Method calls**: `{base_url}/api/method/{method_name}`

## License

MIT License - Free for commercial and personal use.

---

**Built by**: Code Agent (Nebula AI)  
**For**: David Schy / GeniNow Team  
**Purpose**: Production OAuth2 integration for ERPNext multi-company operations
