"""Single check script for scheduled runs (e.g., GitHub Actions)."""
import sys
from config import Config
from github_client import GitHubClient, GitHubError
from telegram_client import TelegramClient
from state_manager import StateManager

def main():
    """Run a single check for all repositories."""
    # Validate configuration
    is_valid, errors = Config.validate()
    if not is_valid:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your environment variables.")
        sys.exit(1)
    
    # Initialize clients
    github = GitHubClient(Config.GITHUB_TOKEN)
    telegram = TelegramClient(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID)
    state = StateManager()
    
    repos = Config.REPO_NAMES
    total_new = 0
    
    print(f"Checking {len(repos)} repository/repositories...")
    if Config.AUTHOR_NAME:
        print(f"Author filter: {Config.AUTHOR_NAME}")
    print("-" * 50)
    
    # Check each repository
    for repo in repos:
        try:
            issues = github.get_open_issues(
                repo=repo,
                author=Config.AUTHOR_NAME
            )
            
            # Check if this is the first run for this repo (no state exists)
            is_first_run = not state.is_repo_initialized(repo)
            
            # Check if state appears stale (most tracked issues don't exist anymore)
            is_stale = state.is_state_stale(repo, issues) if not is_first_run else False
            
            if is_first_run or is_stale:
                # First run or stale state: mark all existing issues as notified without sending alerts
                if is_stale:
                    print(f"[{repo}] Stale state detected - re-syncing with {len(issues)} current issue(s) (no alerts sent)")
                else:
                    print(f"[{repo}] First run detected - marking {len(issues)} existing issue(s) as notified (no alerts sent)")
                
                state.sync_state_with_current_issues(repo, issues)
                print(f"[{repo}] Initialized. Future runs will only alert on new issues.")
            else:
                # Subsequent runs: only alert on new issues
                new_issues = state.get_new_issues(repo, issues)
                
                if new_issues:
                    # Safety check: if too many "new" issues, state might be stale
                    if len(new_issues) > len(issues) * 0.8:  # More than 80% are "new"
                        print(f"[{repo}] Warning: {len(new_issues)} out of {len(issues)} issues appear new. Re-syncing state to prevent spam.")
                        state.sync_state_with_current_issues(repo, issues)
                        print(f"[{repo}] State re-synced. No alerts sent this run.")
                    else:
                        print(f"[{repo}] Found {len(new_issues)} new issue(s)!")
                        total_new += len(new_issues)
                        
                        # Send alerts for new issues
                        for issue in new_issues:
                            issue_number = issue.get("number")
                            print(f"  Sending alert for issue #{issue_number}...")
                            
                            message = telegram.format_issue_alert(issue, repo)
                            success = telegram.send_message(message)
                            
                            if success:
                                state.mark_notified(repo, issue_number)
                                print(f"  ✓ Alert sent for issue #{issue_number}")
                            else:
                                print(f"  ✗ Failed to send alert for issue #{issue_number}")
                else:
                    print(f"[{repo}] No new issues (checked {len(issues)} total)")
                
        except GitHubError as e:
            print(f"⚠️  [{repo}] Error: {e}")
        except Exception as e:
            print(f"⚠️  [{repo}] Unexpected error: {e}")
    
    print("-" * 50)
    if total_new > 0:
        print(f"✅ Check complete: {total_new} new issue(s) found and alerted")
    else:
        print(f"✅ Check complete: No new issues")
    
    return 0 if total_new >= 0 else 1

if __name__ == "__main__":
    sys.exit(main())

