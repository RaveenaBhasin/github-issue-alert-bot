"""Configuration management for GitHub issue monitor."""
import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # GitHub settings
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN") or None
    REPO_NAMES: List[str] = []
    AUTHOR_NAME: Optional[str] = os.getenv("AUTHOR_NAME") or None
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Monitoring settings
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "900"))  # Default 15 minutes
    
    @classmethod
    def _parse_repos(cls) -> List[str]:
        """Parse repository names from environment variable."""
        repo_str = os.getenv("REPO_NAMES", "") or os.getenv("REPO_NAME", "")
        if not repo_str:
            return []
        
        # Support comma-separated or newline-separated repos
        repos = []
        for repo in repo_str.replace("\n", ",").split(","):
            repo = repo.strip()
            if repo:
                repos.append(repo)
        return repos
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate configuration and return (is_valid, errors)."""
        errors = []
        
        # GITHUB_TOKEN is optional (for public repos), but recommended for higher rate limits
        
        # Parse repos
        cls.REPO_NAMES = cls._parse_repos()
        
        if not cls.REPO_NAMES:
            errors.append("REPO_NAMES or REPO_NAME is required (format: owner/repo or comma-separated: owner1/repo1,owner2/repo2)")
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not cls.TELEGRAM_CHAT_ID:
            errors.append("TELEGRAM_CHAT_ID is required")
        
        return len(errors) == 0, errors

