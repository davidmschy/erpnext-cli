# ERPNext CLI

OAuth2 PKCE authentication and Python SDK for ERPNext/Frappe instances.

A production-quality tool that lets team members (and their AI agents) authenticate to ERPNext/Frappe via OAuth2 PKCE and make API calls through both a CLI and Python SDK.

## Features

- **OAuth2 PKCE Authentication**: Secure browser-based authentication with automatic token refresh
- **API Key Support**: Headless authentication for AI agents and automated scripts
- **Multi-Site Management**: Configure and switch between multiple ERPNext instances
- **CLI Interface**: Full-featured command-line tool with rich formatting
- **Python SDK**: Importable client for programmatic access
- **Encrypted Token Storage**: Tokens encrypted at rest using Fernet (cryptography)
- **Auto Token Refresh**: Seamless token renewal when expired

## Installation

### From GitHub (Recommended)

```bash
pip install git+https://github.com/davidmschy/erpnext-cli.git
```

### From Local Clone

```bash
git clone https://github.com/davidmschy/erpnext-cli.git
cd erpnext-cli
pip install -e .
```

### Verify Installation

```bash
erpnext --version
```

## Quick Start (Humans)

### 1. Register OAuth2 App in ERPNext

Before using the CLI, you need to register a Connected App in your ERPNext instance:

1. Log into your ERPNext instance as Administrator
2. Go to **Setup → Integrations → Connected App**
3. Create a new Connected App with:
   - **App Name**: ERPNext CLI (or your preferred name)
   - **Redirect URIs**: `http://localhost:8585/callback`
   - **Scopes**: `openid all` (or specific scopes as needed)
   - **Grant Type**: Authorization Code
4. Save and copy the **Client ID**

### 2. Configure Your Site

```bash
erpnext add-site geniinow \
  --url https://geniinow.v.frappe.cloud \
  --client-id YOUR_CLIENT_ID_HERE
```

### 3. Authenticate

```bash
erpnext login --site geniinow
```

This will:
- Open your browser to the ERPNext authorization page
- Prompt you to log in and approve access
- Capture the authorization code
- Exchange it for an access token
- Store the token securely

### 4. Verify Authentication

```bash
erpnext whoami
```

### 5. Start Using the API

```bash
# List open leads
erpnext list Lead --filters '{"status": "Open"}' --limit 5

# Get a specific document
erpnext get Lead LEAD-2024-00001

# Call a custom method
erpnext call frappe.auth.get_logged_user
```

## Quick Start (AI Agents)

AI agents and automated scripts should use API key authentication to avoid browser-based flows.

### 1. Generate API Key/Secret in ERPNext

1. Log into ERPNext
2. Go to your user profile (top-right menu)
3. Click **API Access** → **Generate Keys**
4. Copy the API Key and API Secret (you'll only see the secret once!)

### 2. Configure and Authenticate

```bash
# One-step configuration and authentication
erpnext login --site geniinow \
  --url https://geniinow.v.frappe.cloud \
  --api-key YOUR_API_KEY \
  --api-secret YOUR_API_SECRET
```

### 3. Use in Python Scripts

```python
from erpnext_cli import ERPNextClient

# Client automatically loads stored credentials
client = ERPNextClient(site_name='geniinow')

# Query the API
leads = client.list_docs('Lead', filters={'status': 'Open'}, limit_page_length=10)
for lead in leads:
    print(f"{lead['name']}: {lead['lead_name']} - {lead['status']}")
```

## CLI Commands Reference

### Authentication

```bash
# Login with OAuth2 (interactive)
erpnext login --site geniinow

# Login with API key (headless)
erpnext login --site geniinow --api-key KEY --api-secret SECRET

# Logout from a site
erpnext logout --site geniinow

# Logout from all sites
erpnext logout

# Check who you're logged in as
erpnext whoami
erpnext whoami --site geniinow
```

### Site Management

```bash
# List all configured sites
erpnext sites

# Add a new site
erpnext add-site mysite \
  --url https://mysite.erpnext.com \
  --client-id abc123 \
  --set-default

# Remove a site
erpnext remove-site mysite

# Set default site
erpnext config set-default geniinow

# Show configuration
erpnext config show
```

### Document Operations

```bash
# Get a single document
erpnext get Lead LEAD-2024-00001
erpnext get "Sales Order" SAL-ORD-2024-00001

# Get specific fields only
erpnext get Lead LEAD-2024-00001 --fields name,lead_name,status,email_id

# List documents
erpnext list Lead
erpnext list Lead --limit 10
erpnext list Lead --offset 20 --limit 10  # Pagination

# List with filters
erpnext list Lead --filters '{"status": "Open"}'
erpnext list Lead --filters '{"status": "Open", "lead_owner": "john@example.com"}'

# List with specific fields
erpnext list Lead --fields name,lead_name,status --limit 5

# List with sorting
erpnext list Lead --order-by "modified desc" --limit 10
erpnext list Project --order-by "creation asc"

# Use different site
erpnext list Lead --site geniinow --filters '{"status": "Open"}'
```

### Method Calling

```bash
# Call a Frappe/ERPNext method
erpnext call frappe.auth.get_logged_user

# Call with parameters (key=value format)
erpnext call custom_app.api.get_report --param report_name=Sales --param year=2024

# Call with JSON data
erpnext call myapp.tasks.process_order --data '{"order_id": "SAL-ORD-2024-00001", "action": "approve"}'

# Mix both approaches
erpnext call myapp.api.search --param doctype=Lead --data '{"filters": {"status": "Open"}}'
```

## Python SDK Usage

### Basic Client Usage

```python
from erpnext_cli import ERPNextClient, ERPNextError

# Initialize client (uses default site)
client = ERPNextClient()

# Or specify a site
client = ERPNextClient(site_name='geniinow')

# Or provide custom base URL and token
client = ERPNextClient(
    base_url='https://custom.erpnext.com',
    auth_token='token api_key:api_secret'
)
```

### Document Operations

```python
# Get a document
lead = client.get_doc('Lead', 'LEAD-2024-00001')
print(f"Lead: {lead['lead_name']} - {lead['status']}")

# List documents
leads = client.list_docs(
    doctype='Lead',
    fields=['name', 'lead_name', 'status', 'email_id'],
    filters={'status': 'Open', 'company': 'GeniNow'},
    limit_page_length=10,
    order_by='modified desc'
)

for lead in leads:
    print(f"{lead['name']}: {lead['lead_name']}")

# Alternative: use get_list (alias)
leads = client.get_list('Lead', filters={'status': 'Open'}, limit_page_length=5)

# Create a document
new_lead = client.create_doc('Lead', {
    'lead_name': 'Jane Doe',
    'email_id': 'jane@example.com',
    'company_name': 'Example Corp',
    'status': 'Open'
})
print(f"Created lead: {new_lead['name']}")

# Update a document
updated = client.update_doc('Lead', 'LEAD-2024-00001', {
    'status': 'Qualified',
    'notes': 'Follow up completed, ready for conversion'
})

# Delete a document
client.delete_doc('Lead', 'LEAD-2024-00001')
```

### Method Calling

```python
# Get current user
user = client.get_logged_user()
print(f"Logged in as: {user}")

# Call custom method
result = client.call('custom_app.api.get_dashboard_data', 
                     company='GeniNow', 
                     date='2024-02-24')

# Call method with complex parameters
report_data = client.call('frappe.desk.query_report.run',
    report_name='Sales Analytics',
    filters={'company': 'GeniNow', 'from_date': '2024-01-01'}
)
```

### Error Handling

```python
from erpnext_cli import ERPNextClient, ERPNextError

client = ERPNextClient(site_name='geniinow')

try:
    lead = client.get_doc('Lead', 'INVALID-ID')
except ERPNextError as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    if e.response:
        print(f"Response: {e.response}")
```

### Low-Level HTTP Methods

```python
# Direct HTTP access for custom endpoints
response = client.get('/api/resource/Lead', params={'limit_page_length': 5})

response = client.post('/api/method/custom_app.api.process', data={
    'action': 'approve',
    'document_id': 'DOC-001'
})

response = client.put('/api/resource/Lead/LEAD-001', data={'status': 'Closed'})

response = client.delete('/api/resource/Lead/LEAD-001')
```

## Multi-Company Usage

The CLI supports managing multiple ERPNext instances (different companies or environments).

```bash
# Add multiple sites
erpnext add-site geniinow --url https://geniinow.v.frappe.cloud --client-id abc123
erpnext add-site fbx --url https://fbx.erpnext.com --client-id xyz789
erpnext add-site staging --url https://staging.mycompany.com --client-id test456

# Login to each
erpnext login --site geniinow
erpnext login --site fbx --api-key KEY --api-secret SECRET
erpnext login --site staging

# Set default site (optional)
erpnext config set-default geniinow

# Use without --site flag (uses default)
erpnext list Lead

# Or explicitly specify site
erpnext list Lead --site fbx
erpnext list Project --site staging
```

### In Python

```python
from erpnext_cli import ERPNextClient

# Different clients for different sites
geniinow_client = ERPNextClient(site_name='geniinow')
fbx_client = ERPNextClient(site_name='fbx')

geniinow_leads = geniinow_client.get_list('Lead', filters={'status': 'Open'})
fbx_projects = fbx_client.get_list('Project', filters={'status': 'Open'})
```

## Configuration Files

### Config Location

- **Config**: `~/.config/erpnext-cli/config.json`
- **Tokens**: `~/.config/erpnext-cli/tokens.json` (encrypted)
- **Encryption Key**: `~/.config/erpnext-cli/.key`

### Config Structure

```json
{
  "default_site": "geniinow",
  "sites": {
    "geniinow": {
      "base_url": "https://geniinow.v.frappe.cloud",
      "client_id": "abc123xyz",
      "scope": "openid all"
    },
    "fbx": {
      "base_url": "https://fbx.erpnext.com",
      "client_id": "xyz789abc",
      "scope": "openid all"
    }
  }
}
```

### Token Storage

Tokens are encrypted at rest using Fernet (cryptography library) with a machine-specific key. Each site's tokens are stored separately with:
- `access_token`: Current OAuth2 access token
- `refresh_token`: OAuth2 refresh token (if provided)
- `expires_at`: Unix timestamp for token expiry
- Auto-refresh: Tokens are automatically refreshed when expired

## Channel Isolation & Security

**Important for Multi-Company Teams:**

When using this tool in organizations with multiple ERPNext instances:

1. **Use dedicated API keys per company**: Each team member's agent should only have credentials for their assigned company
2. **Channel isolation**: Configure separate AI agents for each company/division to prevent data leakage
3. **Least privilege**: Request only the scopes/permissions needed for your role
4. **Secure storage**: The CLI encrypts tokens at rest, but protect your `~/.config/erpnext-cli/` directory with proper file permissions

## Advanced Usage

### Pagination

```python
# Fetch all records in batches
def fetch_all_docs(client, doctype, filters=None, batch_size=100):
    offset = 0
    all_docs = []
    
    while True:
        batch = client.list_docs(
            doctype=doctype,
            filters=filters,
            limit_start=offset,
            limit_page_length=batch_size
        )
        
        if not batch:
            break
        
        all_docs.extend(batch)
        offset += batch_size
        
        if len(batch) < batch_size:
            break
    
    return all_docs

# Usage
client = ERPNextClient(site_name='geniinow')
all_leads = fetch_all_docs(client, 'Lead', filters={'status': 'Open'})
print(f"Total open leads: {len(all_leads)}")
```

### Custom Headers and Session Configuration

```python
from erpnext_cli import ERPNextClient

client = ERPNextClient(site_name='geniinow')

# Add custom headers to all requests
client.session.headers.update({
    'X-Custom-Header': 'value',
    'User-Agent': 'MyApp/1.0'
})

# Configure timeouts
client.session.timeout = 60  # 60 seconds

# Configure retries
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
client.session.mount("https://", adapter)
client.session.mount("http://", adapter)
```

### Environment Variables

You can use environment variables to configure sites without the CLI:

```bash
export ERPNEXT_SITE=geniinow
export ERPNEXT_BASE_URL=https://geniinow.v.frappe.cloud
export ERPNEXT_API_KEY=your_api_key
export ERPNEXT_API_SECRET=your_api_secret
```

Then in Python:

```python
import os
from erpnext_cli import ERPNextClient

# Override with environment variables
client = ERPNextClient(
    base_url=os.getenv('ERPNEXT_BASE_URL'),
    auth_token=f"token {os.getenv('ERPNEXT_API_KEY')}:{os.getenv('ERPNEXT_API_SECRET')}"
)
```

## Troubleshooting

### OAuth2 Callback Not Received

If the browser opens but the callback fails:

1. **Check redirect URI**: Must be exactly `http://localhost:8585/callback` in ERPNext Connected App
2. **Port conflict**: Try a different port: `erpnext login --site mysite --port 8586`
3. **Firewall**: Ensure localhost connections are allowed

### Token Refresh Fails

If token refresh fails repeatedly:

1. **Re-login**: `erpnext logout --site mysite && erpnext login --site mysite`
2. **Check Connected App**: Ensure it's still active in ERPNext
3. **Check scope**: Refresh tokens require appropriate scopes

### API Key Authentication Not Working

1. **Verify keys**: Check that API key and secret are correct (no extra spaces)
2. **User permissions**: Ensure the user has necessary permissions in ERPNext
3. **API access enabled**: Check that API Access is enabled for the user

### Permission Denied on Config Files

```bash
# Fix file permissions
chmod 600 ~/.config/erpnext-cli/tokens.json
chmod 600 ~/.config/erpnext-cli/.key
chmod 644 ~/.config/erpnext-cli/config.json
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=erpnext_cli
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/davidmschy/erpnext-cli.git
cd erpnext-cli

# Install in editable mode
pip install -e .

# Make changes and test
erpnext --version
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: https://github.com/davidmschy/erpnext-cli/issues
- **Documentation**: https://github.com/davidmschy/erpnext-cli
- **ERPNext Docs**: https://frappeframework.com/docs

## Related Projects

- [Frappe Framework](https://github.com/frappe/frappe)
- [ERPNext](https://github.com/frappe/erpnext)
- [Frappe Python Client](https://github.com/frappe/python-frappe-client) (REST API key only, no OAuth2)

## Changelog

### v0.1.0 (2024-02-24)

- Initial release
- OAuth2 PKCE authentication flow
- API key/secret authentication
- Multi-site management
- Full CLI with rich formatting
- Python SDK for programmatic access
- Encrypted token storage with auto-refresh
- Document CRUD operations
- Method calling support
