"""GitHub token validation and scope checking."""
import requests
from typing import Optional, Dict, List
from github_client import GitHubError


def validate_token(token: str) -> tuple[bool, Dict]:
    """
    Validate GitHub token and check its scopes.
    
    Returns:
        (is_valid, info_dict) where info_dict contains:
        - scopes: List of token scopes
        - has_repo_scope: Boolean indicating if repo scope is present
        - user: GitHub username
        - rate_limit: Current rate limit info
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # Check token validity and get user info
    try:
        response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
        
        if response.status_code == 401:
            return False, {"error": "Token is invalid or expired"}
        
        if not response.ok:
            return False, {"error": f"API error: {response.status_code}"}
        
        user_data = response.json()
        
        # Get token scopes from response headers
        scopes_header = response.headers.get("X-OAuth-Scopes", "")
        scopes = [s.strip() for s in scopes_header.split(",")] if scopes_header else []
        
        # Check rate limit
        rate_limit_response = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=10)
        rate_limit_data = rate_limit_response.json() if rate_limit_response.ok else {}
        
        has_repo_scope = "repo" in scopes
        has_public_repo_scope = "public_repo" in scopes
        
        return True, {
            "scopes": scopes,
            "has_repo_scope": has_repo_scope,
            "has_public_repo_scope": has_public_repo_scope,
            "user": user_data.get("login", "Unknown"),
            "rate_limit": rate_limit_data.get("resources", {}).get("core", {}),
        }
    except requests.exceptions.RequestException as e:
        return False, {"error": f"Network error: {str(e)}"}


def check_private_repo_access(token: str, repo: str) -> tuple[bool, str]:
    """
    Check if token can access a specific private repository.
    
    Returns:
        (can_access, message)
    """
    is_valid, info = validate_token(token)
    
    if not is_valid:
        return False, f"Token validation failed: {info.get('error', 'Unknown error')}"
    
    if not info.get("has_repo_scope"):
        return False, (
            f"Token does not have 'repo' scope required for private repositories. "
            f"Current scopes: {', '.join(info.get('scopes', [])) or 'none'}. "
            f"Please regenerate your token with 'repo' scope."
        )
    
    # Try to access the repo
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=10)
        
        if response.status_code == 404:
            return False, f"Repository '{repo}' not found or you don't have access"
        elif response.status_code == 403:
            return False, f"Access forbidden to '{repo}'. Check repository permissions."
        elif response.ok:
            repo_data = response.json()
            is_private = repo_data.get("private", False)
            return True, f"Access granted. Repository is {'private' if is_private else 'public'}."
        else:
            return False, f"Unexpected error: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Network error: {str(e)}"

