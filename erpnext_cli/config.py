"""
Configuration management for ERPNext CLI.
Handles site profiles stored in ~/.config/erpnext-cli/config.json
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_home = os.environ.get('XDG_CONFIG_HOME')
    if config_home:
        config_dir = Path(config_home) / 'erpnext-cli'
    else:
        config_dir = Path.home() / '.config' / 'erpnext-cli'
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / 'config.json'


def load_config() -> Dict[str, Any]:
    """
    Load configuration from disk.
    
    Returns:
        Configuration dictionary with structure:
        {
            "default_site": "site_name",
            "sites": {
                "site_name": {
                    "base_url": "https://...",
                    "client_id": "...",
                    "scope": "openid all"
                }
            }
        }
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        return {
            "default_site": None,
            "sites": {}
        }
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Ensure required keys exist
            if "sites" not in config:
                config["sites"] = {}
            if "default_site" not in config:
                config["default_site"] = None
            return config
    except (json.JSONDecodeError, IOError) as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}")


def save_config(config: Dict[str, Any]) -> None:
    """
    Save configuration to disk.
    
    Args:
        config: Configuration dictionary to save
    """
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        raise RuntimeError(f"Failed to save config to {config_path}: {e}")


def get_site(name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get site configuration by name.
    
    Args:
        name: Site name. If None, uses default_site.
        
    Returns:
        Site configuration dictionary
        
    Raises:
        ValueError: If site not found or no default site configured
    """
    config = load_config()
    
    if name is None:
        name = config.get("default_site")
        if not name:
            raise ValueError(
                "No default site configured. Use 'erpnext add-site' or specify --site"
            )
    
    if name not in config["sites"]:
        raise ValueError(
            f"Site '{name}' not found. Available sites: {', '.join(config['sites'].keys()) or 'none'}"
        )
    
    site_config = config["sites"][name].copy()
    site_config["name"] = name
    return site_config


def add_site(
    name: str,
    base_url: str,
    client_id: str,
    scope: str = "openid all",
    set_as_default: bool = False
) -> None:
    """
    Add or update a site configuration.
    
    Args:
        name: Unique identifier for this site
        base_url: Base URL of the ERPNext/Frappe instance
        client_id: OAuth2 client ID
        scope: OAuth2 scope (default: "openid all")
        set_as_default: Whether to set this as the default site
    """
    config = load_config()
    
    # Normalize base_url (remove trailing slash)
    base_url = base_url.rstrip('/')
    
    config["sites"][name] = {
        "base_url": base_url,
        "client_id": client_id,
        "scope": scope
    }
    
    # If this is the first site or set_as_default is True, make it default
    if set_as_default or not config["default_site"]:
        config["default_site"] = name
    
    save_config(config)


def remove_site(name: str) -> None:
    """
    Remove a site configuration.
    
    Args:
        name: Site name to remove
        
    Raises:
        ValueError: If site not found
    """
    config = load_config()
    
    if name not in config["sites"]:
        raise ValueError(f"Site '{name}' not found")
    
    del config["sites"][name]
    
    # Clear default if it was the removed site
    if config["default_site"] == name:
        # Set default to first remaining site, if any
        config["default_site"] = next(iter(config["sites"]), None)
    
    save_config(config)


def set_default(name: str) -> None:
    """
    Set the default site.
    
    Args:
        name: Site name to set as default
        
    Raises:
        ValueError: If site not found
    """
    config = load_config()
    
    if name not in config["sites"]:
        raise ValueError(f"Site '{name}' not found")
    
    config["default_site"] = name
    save_config(config)


def list_sites() -> Dict[str, Dict[str, Any]]:
    """
    List all configured sites.
    
    Returns:
        Dictionary mapping site names to their configurations
    """
    config = load_config()
    return config["sites"]


def get_default_site() -> Optional[str]:
    """
    Get the name of the default site.
    
    Returns:
        Default site name or None if not configured
    """
    config = load_config()
    return config.get("default_site")
