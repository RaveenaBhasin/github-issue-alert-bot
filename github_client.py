"""GitHub API client for fetching issues."""
import requests
from typing import Optional, List, Dict
from config import Config


class GitHubError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with optional API token."""
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    def get_open_issues(
        self,
        repo: str,
        author: Optional[str] = None,
        state: str = "open"
    ) -> List[Dict]:
        """
        Fetch open issues from a repository, optionally filtered by author.
        
        Args:
            repo: Repository name in format 'owner/repo'
            author: Optional GitHub username to filter by
            state: Issue state (default: 'open')
        
        Returns:
            List of issue dictionaries
        """
        url = f"{self.BASE_URL}/repos/{repo}/issues"
        params = {
            "state": state,
            "per_page": 100,
            "sort": "created",
            "direction": "desc"
        }
        
        all_issues = []
        page = 1
        
        try:
            while True:
                params["page"] = page
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                # Handle different HTTP status codes gracefully
                if response.status_code == 404:
                    raise GitHubError(
                        f"Repository '{repo}' not found. "
                        f"Please check that the repository exists and is accessible. "
                        f"Format should be 'owner/repo' (e.g., 'paradigmxyz/reth')"
                    )
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    message = error_data.get("message", "Access forbidden")
                    if "rate limit" in message.lower():
                        raise GitHubError(
                            f"GitHub API rate limit exceeded. "
                            f"Please wait before trying again or use a GitHub token for higher limits."
                        )
                    else:
                        raise GitHubError(
                            f"Access forbidden to repository '{repo}'. "
                            f"This may be a private repository. "
                            f"If it's your repository, ensure your token has the 'repo' scope. "
                            f"Run 'python check_token.py' to verify your token permissions."
                        )
                elif response.status_code == 401:
                    raise GitHubError(
                        f"Authentication failed. "
                        f"Please check your GitHub token is valid and has the correct permissions."
                    )
                elif not response.ok:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("message", response.text)
                    raise GitHubError(
                        f"GitHub API error ({response.status_code}): {error_msg}"
                    )
                
                issues = response.json()
                if not issues:
                    break
                
                # Filter by author if specified
                if author:
                    issues = [issue for issue in issues if issue.get("user", {}).get("login") == author]
                
                all_issues.extend(issues)
                
                # Check if there are more pages
                if len(issues) < 100:
                    break
                
                page += 1
            
            return all_issues
            
        except requests.exceptions.Timeout:
            raise GitHubError(f"Request timeout while fetching issues from '{repo}'. Please try again later.")
        except requests.exceptions.RequestException as e:
            raise GitHubError(f"Network error while fetching issues: {str(e)}")
    
    def get_issue(self, repo: str, issue_number: int) -> Dict:
        """Get a specific issue by number."""
        url = f"{self.BASE_URL}/repos/{repo}/issues/{issue_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

