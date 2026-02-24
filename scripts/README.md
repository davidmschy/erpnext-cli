# ERPNext Admin Scripts

Administrative scripts for setting up ERPNext CLI and managing team access.

## Scripts

### setup_connected_app.py

**Purpose**: One-time setup to register the erpnext-cli OAuth2 client in your ERPNext instance.

**When to use**: Run this ONCE as an admin when first setting up erpnext-cli for your organization.

**Requirements**:
- Admin user API key and secret
- ERPNext v13+ instance
- `requests` library (`pip install requests`)

**Usage**:
```bash
python ../setup_connected_app.py \
    --url https://geniinow.v.frappe.cloud \
    --api-key YOUR_ADMIN_API_KEY \
    --api-secret YOUR_ADMIN_API_SECRET
```

**Output**:
- Client ID for OAuth2 authentication
- CLI commands to share with team members
- Instructions for setting up erpnext-cli

### create_team_user.py

**Purpose**: Create a new ERPNext user account with API credentials for CLI access.

**When to use**: Whenever you need to onboard a new team member who needs programmatic/CLI access to ERPNext.

**Requirements**:
- Admin user API key and secret
- ERPNext v13+ instance
- `requests` library (`pip install requests`)

**Usage**:
```bash
python create_team_user.py \
    --url https://geniinow.v.frappe.cloud \
    --api-key YOUR_ADMIN_API_KEY \
    --api-secret YOUR_ADMIN_API_SECRET \
    --email john.porter@example.com \
    --first-name John \
    --last-name Porter \
    --role "Sales User"
```

**Common Roles**:
- `Sales User` - CRM access, lead/opportunity management
- `Sales Manager` - Full sales + reporting access
- `Projects User` - Project and task management
- `System Manager` - Full admin access (use carefully)

**Output**:
- Generated API key and secret for the user
- CLI login commands to share with the team member
- Setup instructions

## Workflow

### Initial Setup (Run Once)

1. **Admin creates Connected App** (OAuth2 client registration):
   ```bash
   python ../setup_connected_app.py \
       --url https://your-site.frappe.cloud \
       --api-key ADMIN_KEY \
       --api-secret ADMIN_SECRET
   ```

2. **Share the client_id** with your team via the printed commands

### Team Member Onboarding (For Each User)

**Option A: OAuth2 Flow (Recommended)**
- Team members use the `erpnext add-site` command from setup_connected_app.py output
- They authenticate via browser (no API keys needed)
- Most secure for user-level access

**Option B: API Key Authentication (For Service Accounts/Automation)**
- Admin runs `create_team_user.py` to generate API credentials
- Share credentials securely with the user or service
- Useful for CI/CD, automation scripts, or service accounts

## Security Best Practices

1. **Admin Credentials**: Never commit admin API keys to git
2. **User Credentials**: Share API keys through secure channels (1Password, encrypted email)
3. **Key Rotation**: Regenerate compromised keys immediately via ERPNext UI
4. **Principle of Least Privilege**: Assign minimal required role (e.g., "Sales User" not "System Manager")
5. **Service Accounts**: Use dedicated users for automation (e.g., `ci-bot@example.com`)

## Troubleshooting

### "Connected App already exists"
- View existing apps at: `https://your-site.frappe.cloud/app/connected-app`
- Either delete and recreate, or retrieve the client_id from the existing app

### "User already exists"
- The email is already registered
- To regenerate API keys for existing user, go to: `https://your-site.frappe.cloud/app/user/{email}`

### "Authentication failed"
- Check your admin API key and secret are correct
- Verify the URL is correct (include `https://`)
- Ensure your admin user has "System Manager" role

### "Permission denied"
- Your admin user may lack "System Manager" role
- Some endpoints require elevated permissions

## Dependencies

Both scripts require:
```bash
pip install requests
```

Or install from erpnext-cli requirements:
```bash
pip install -r ../requirements.txt
```
