"""
Command-line interface for ERPNext CLI.
Provides commands for authentication, configuration, and API operations.
"""
import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from . import auth, config, client

console = Console()


def handle_error(error: Exception, exit_code: int = 1) -> None:
    """Display error message and exit."""
    console.print(f"[bold red]Error:[/bold red] {error}", file=sys.stderr)
    sys.exit(exit_code)


def format_json(data: dict) -> str:
    """Format JSON data with pretty printing."""
    return json.dumps(data, indent=2, default=str)


@click.group()
@click.version_option(version="0.1.0", prog_name="erpnext-cli")
def main():
    """
    ERPNext CLI - OAuth2 PKCE authentication and API access for ERPNext/Frappe.
    
    Manage multiple ERPNext sites, authenticate securely, and interact with the API.
    """
    pass


@main.command()
@click.option('--site', default=None, help='Site name')
@click.option('--url', default=None, help='ERPNext instance URL')
@click.option('--client-id', default=None, help='OAuth2 client ID')
@click.option('--scope', default='openid all', help='OAuth2 scope')
@click.option('--port', default=8585, help='Local callback server port')
@click.option('--api-key', default=None, help='API key (alternative to OAuth2)')
@click.option('--api-secret', default=None, help='API secret (with --api-key)')
def login(site, url, client_id, scope, port, api_key, api_secret):
    """
    Authenticate to an ERPNext site.
    
    Supports two authentication methods:
    
    1. OAuth2 PKCE (interactive, browser-based):
       erpnext login --site geniinow
    
    2. API Key/Secret (headless, for agents):
       erpnext login --site geniinow --api-key KEY --api-secret SECRET
    
    First-time setup (new site):
       erpnext login --site mysite --url https://mysite.erpnext.com --client-id abc123
    """
    try:
        # Determine site name
        if not site:
            if url:
                # Extract site name from URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                site = parsed.hostname.split('.')[0] if parsed.hostname else 'default'
            else:
                site = config.get_default_site()
                if not site:
                    raise click.ClickException(
                        "No site specified and no default site configured. "
                        "Use --site or configure a site first."
                    )
        
        # API key authentication
        if api_key and api_secret:
            # Register site if URL provided
            if url:
                if not client_id:
                    client_id = 'api-key-auth'  # Placeholder
                config.add_site(site, url, client_id, scope, set_as_default=True)
            
            # Store API credentials
            auth.store_api_key(site, api_key, api_secret)
            console.print(f"[green]✓[/green] API key authentication configured for site '{site}'")
            return
        
        # OAuth2 flow
        if url and client_id:
            # Register new site
            config.add_site(site, url, client_id, scope, set_as_default=True)
            console.print(f"[green]✓[/green] Site '{site}' configured")
        
        # Get site config
        try:
            site_config = config.get_site(site)
        except ValueError as e:
            raise click.ClickException(str(e))
        
        # Perform OAuth flow
        console.print(f"[cyan]Authenticating to {site_config['base_url']}...[/cyan]")
        token_data = auth.perform_oauth_flow(
            site_name=site,
            base_url=site_config['base_url'],
            client_id=site_config['client_id'],
            scope=site_config.get('scope', 'openid all'),
            port=port
        )
        
        # Get logged-in user
        try:
            api_client = client.ERPNextClient(site_name=site)
            user = api_client.get_logged_user()
            console.print(f"[green]✓[/green] Logged in to {site} as [bold]{user}[/bold]")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Authentication successful, but couldn't verify user: {e}")
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.option('--site', default=None, help='Site name (default: all sites)')
def logout(site):
    """
    Log out from an ERPNext site (clear stored tokens).
    
    Examples:
        erpnext logout --site geniinow
        erpnext logout  # clears all tokens
    """
    try:
        if site:
            auth.delete_token(site)
            console.print(f"[green]✓[/green] Logged out from site '{site}'")
        else:
            # Clear all tokens
            tokens = auth.load_tokens()
            if not tokens:
                console.print("[yellow]No active sessions found[/yellow]")
                return
            
            for site_name in list(tokens.keys()):
                auth.delete_token(site_name)
            
            console.print(f"[green]✓[/green] Logged out from all sites ({len(tokens)} sessions cleared)")
    
    except Exception as e:
        handle_error(e)


@main.command()
def sites():
    """
    List all configured sites.
    
    Shows site name, URL, and default status.
    """
    try:
        sites_config = config.list_sites()
        default_site = config.get_default_site()
        
        if not sites_config:
            console.print("[yellow]No sites configured[/yellow]")
            console.print("\nAdd a site with: [cyan]erpnext add-site[/cyan]")
            return
        
        table = Table(title="Configured Sites", show_header=True)
        table.add_column("Site Name", style="cyan")
        table.add_column("Base URL", style="blue")
        table.add_column("Client ID", style="dim")
        table.add_column("Default", style="green")
        
        for site_name, site_config in sites_config.items():
            is_default = "✓" if site_name == default_site else ""
            table.add_row(
                site_name,
                site_config.get('base_url', 'N/A'),
                site_config.get('client_id', 'N/A')[:20] + '...' if len(site_config.get('client_id', '')) > 20 else site_config.get('client_id', 'N/A'),
                is_default
            )
        
        console.print(table)
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.argument('name')
@click.option('--url', required=True, help='ERPNext instance base URL')
@click.option('--client-id', required=True, help='OAuth2 client ID')
@click.option('--scope', default='openid all', help='OAuth2 scope')
@click.option('--set-default', is_flag=True, help='Set as default site')
def add_site(name, url, client_id, scope, set_default):
    """
    Add a new ERPNext site configuration.
    
    This registers the site but doesn't authenticate yet.
    Use 'erpnext login' to authenticate after adding.
    
    Example:
        erpnext add-site geniinow \\
            --url https://geniinow.v.frappe.cloud \\
            --client-id abc123xyz
    """
    try:
        config.add_site(name, url, client_id, scope, set_as_default=set_default)
        console.print(f"[green]✓[/green] Site '{name}' added successfully")
        
        if set_default or not config.get_default_site():
            console.print(f"[green]✓[/green] Set as default site")
        
        console.print(f"\nNext step: [cyan]erpnext login --site {name}[/cyan]")
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.argument('name')
def remove_site(name):
    """
    Remove a site configuration.
    
    This removes the site config and clears stored tokens.
    
    Example:
        erpnext remove-site oldsite
    """
    try:
        if not click.confirm(f"Remove site '{name}' and clear its tokens?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
        
        config.remove_site(name)
        auth.delete_token(name)
        console.print(f"[green]✓[/green] Site '{name}' removed")
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.option('--site', default=None, help='Site name')
def whoami(site):
    """
    Show the currently authenticated user.
    
    Example:
        erpnext whoami
        erpnext whoami --site geniinow
    """
    try:
        api_client = client.ERPNextClient(site_name=site)
        user = api_client.get_logged_user()
        
        site_name = api_client.site_name
        console.print(Panel(
            f"[green]{user}[/green]",
            title=f"Logged in to {site_name}",
            border_style="cyan"
        ))
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.argument('doctype')
@click.argument('name')
@click.option('--site', default=None, help='Site name')
@click.option('--fields', default=None, help='Comma-separated field names')
def get(doctype, name, site, fields):
    """
    Get a document by doctype and name.
    
    Examples:
        erpnext get Lead LEAD-2024-00001
        erpnext get "Sales Order" SAL-ORD-2024-00001 --fields name,customer,status
    """
    try:
        api_client = client.ERPNextClient(site_name=site)
        doc = api_client.get_doc(doctype, name)
        
        # Filter fields if specified
        if fields:
            field_list = [f.strip() for f in fields.split(',')]
            doc = {k: v for k, v in doc.items() if k in field_list}
        
        # Display formatted JSON
        syntax = Syntax(format_json(doc), "json", theme="monokai", line_numbers=False)
        console.print(syntax)
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.argument('doctype')
@click.option('--site', default=None, help='Site name')
@click.option('--fields', default=None, help='Comma-separated field names')
@click.option('--filters', default=None, help='JSON filters')
@click.option('--limit', default=20, help='Number of records')
@click.option('--offset', default=0, help='Offset for pagination')
@click.option('--order-by', default=None, help='Sort order (e.g., "modified desc")')
def list(doctype, site, fields, filters, limit, offset, order_by):
    """
    List documents of a doctype.
    
    Examples:
        erpnext list Lead --limit 5
        erpnext list Lead --filters '{"status": "Open"}' --fields name,lead_name,status
        erpnext list Project --order-by "creation desc"
    """
    try:
        api_client = client.ERPNextClient(site_name=site)
        
        # Parse fields
        field_list = None
        if fields:
            field_list = [f.strip() for f in fields.split(',')]
        
        # Parse filters
        filter_dict = None
        if filters:
            filter_dict = json.loads(filters)
        
        # Fetch documents
        docs = api_client.list_docs(
            doctype=doctype,
            fields=field_list,
            filters=filter_dict,
            limit_start=offset,
            limit_page_length=limit,
            order_by=order_by
        )
        
        if not docs:
            console.print(f"[yellow]No {doctype} documents found[/yellow]")
            return
        
        # Display as table if reasonable number of fields, else JSON
        if field_list and len(field_list) <= 6 and len(docs) > 1:
            table = Table(title=f"{doctype} ({len(docs)} records)")
            for field in field_list:
                table.add_column(field, style="cyan")
            
            for doc in docs:
                table.add_row(*[str(doc.get(field, '')) for field in field_list])
            
            console.print(table)
        else:
            # JSON output
            syntax = Syntax(format_json(docs), "json", theme="monokai", line_numbers=False)
            console.print(syntax)
    
    except Exception as e:
        handle_error(e)


@main.command()
@click.argument('method')
@click.option('--site', default=None, help='Site name')
@click.option('--data', default=None, help='JSON data to pass to method')
@click.option('--param', multiple=True, help='Method parameters (key=value)')
def call(method, site, data, param):
    """
    Call an ERPNext server-side method.
    
    Examples:
        erpnext call frappe.auth.get_logged_user
        erpnext call custom_app.api.get_report --param report_name=Sales
        erpnext call myapp.tasks.process --data '{"id": 123, "action": "approve"}'
    """
    try:
        api_client = client.ERPNextClient(site_name=site)
        
        # Parse parameters
        kwargs = {}
        if data:
            kwargs = json.loads(data)
        
        # Add individual params
        for p in param:
            if '=' not in p:
                raise click.ClickException(f"Invalid parameter format: {p}. Use key=value")
            key, value = p.split('=', 1)
            # Try to parse as JSON, fallback to string
            try:
                kwargs[key] = json.loads(value)
            except:
                kwargs[key] = value
        
        # Call method
        result = api_client.call(method, **kwargs)
        
        # Display result
        if isinstance(result, (dict, list)):
            syntax = Syntax(format_json(result), "json", theme="monokai", line_numbers=False)
            console.print(syntax)
        else:
            console.print(result)
    
    except Exception as e:
        handle_error(e)


@main.group()
def config_cmd():
    """Manage configuration."""
    pass


@config_cmd.command('show')
def config_show():
    """
    Show current configuration.
    
    Displays all configured sites (with masked secrets).
    """
    try:
        full_config = config.load_config()
        
        # Mask client IDs
        display_config = full_config.copy()
        for site_name, site_config in display_config.get('sites', {}).items():
            if 'client_id' in site_config and len(site_config['client_id']) > 20:
                site_config['client_id'] = site_config['client_id'][:8] + '...' + site_config['client_id'][-8:]
        
        syntax = Syntax(format_json(display_config), "json", theme="monokai", line_numbers=False)
        console.print(syntax)
        
        console.print(f"\n[dim]Config file: {config.get_config_path()}[/dim]")
        console.print(f"[dim]Tokens file: {auth.get_tokens_path()}[/dim]")
    
    except Exception as e:
        handle_error(e)


@config_cmd.command('set-default')
@click.argument('site')
def config_set_default(site):
    """
    Set the default site.
    
    Example:
        erpnext config set-default geniinow
    """
    try:
        config.set_default(site)
        console.print(f"[green]✓[/green] Default site set to '{site}'")
    
    except Exception as e:
        handle_error(e)


# Alias 'config' command group to main
main.add_command(config_cmd, name='config')


if __name__ == '__main__':
    main()
