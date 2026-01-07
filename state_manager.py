"""State management to track notified issues."""
import json
import os
from typing import Set, Dict
from pathlib import Path


class StateManager:
    """Manages state to prevent duplicate notifications per repository."""
    
    def __init__(self, state_file: str = "state.json"):
        """Initialize state manager with state file path."""
        self.state_file = Path(state_file)
        # Track notified issues per repo: {repo: {issue_number, ...}}
        self.notified_issues: Dict[str, Set[int]] = {}
        self.load_state()
    
    def load_state(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    # Support both old format (flat list) and new format (per-repo)
                    if "repos" in data:
                        # New format: per-repo tracking
                        self.notified_issues = {
                            repo: set(issues) 
                            for repo, issues in data.get("repos", {}).items()
                        }
                    else:
                        # Old format: migrate to new format
                        old_issues = set(data.get("notified_issues", []))
                        if old_issues:
                            # Migrate old state to a default repo key
                            self.notified_issues = {"_legacy": old_issues}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load state file: {e}")
                self.notified_issues = {}
        else:
            self.notified_issues = {}
    
    def save_state(self) -> None:
        """Save state to file."""
        try:
            data = {
                "repos": {
                    repo: list(issues) 
                    for repo, issues in self.notified_issues.items()
                }
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save state file: {e}")
    
    def is_notified(self, repo: str, issue_number: int) -> bool:
        """Check if an issue has already been notified for a specific repo."""
        if repo not in self.notified_issues:
            return False
        return issue_number in self.notified_issues[repo]
    
    def mark_notified(self, repo: str, issue_number: int) -> None:
        """Mark an issue as notified for a specific repo."""
        if repo not in self.notified_issues:
            self.notified_issues[repo] = set()
        self.notified_issues[repo].add(issue_number)
        self.save_state()
    
    def get_new_issues(self, repo: str, issues: list) -> list:
        """Filter out issues that have already been notified for a specific repo."""
        return [
            issue for issue in issues
            if not self.is_notified(repo, issue.get("number"))
        ]

