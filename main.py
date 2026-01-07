"""Main monitoring script for GitHub issues."""
import time
import sys
from config import Config
from github_client import GitHubClient, GitHubError
from telegram_client import TelegramClient
from state_manager import StateManager
from token_validator import validate_token, check_private_repo_access


def main():
    """Main monitoring loop."""
    # Validate configuration
    is_valid, errors = Config.validate()
    if not is_valid:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file or environment variables.")
        sys.exit(1)
    
    # Initialize clients
    github = GitHubClient(Config.GITHUB_TOKEN)
    telegram = TelegramClient(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID)
    state = StateManager()
    
    repos = Config.REPO_NAMES
    poll_interval_minutes = Config.POLL_INTERVAL // 60
    
    print(f"Starting GitHub issue monitor...")
    print(f"Repositories ({len(repos)}): {', '.join(repos)}")
    if Config.AUTHOR_NAME:
        print(f"Author filter: {Config.AUTHOR_NAME}")
    print(f"Poll interval: {poll_interval_minutes} minutes ({Config.POLL_INTERVAL} seconds)")
    print(f"Telegram chat ID: {Config.TELEGRAM_CHAT_ID}")
    
    # Validate token if provided
    if Config.GITHUB_TOKEN:
        print(f"GitHub authentication: Enabled")
        is_valid, token_info = validate_token(Config.GITHUB_TOKEN)
        if is_valid:
            scopes = token_info.get("scopes", [])
            has_repo_scope = token_info.get("has_repo_scope", False)
            user = token_info.get("user", "Unknown")
            print(f"  Token user: {user}")
            print(f"  Token scopes: {', '.join(scopes) if scopes else 'none'}")
            if has_repo_scope:
                print(f"  ✓ Token has 'repo' scope - can access private repositories")
            else:
                print(f"  ⚠️  Token missing 'repo' scope - cannot access private repositories")
                print(f"     Current scopes: {', '.join(scopes) if scopes else 'none'}")
                print(f"     To access private repos, regenerate token with 'repo' scope")
            rate_limit = token_info.get("rate_limit", {})
            if rate_limit:
                remaining = rate_limit.get("remaining", 0)
                limit = rate_limit.get("limit", 0)
                print(f"  Rate limit: {remaining}/{limit} requests remaining")
        else:
            print(f"  ⚠️  Token validation failed: {token_info.get('error', 'Unknown error')}")
    else:
        print(f"GitHub authentication: Disabled (60 requests/hour limit)")
        print(f"  ⚠️  Warning: Unauthenticated requests have lower rate limits")
        print(f"  ⚠️  Cannot access private repositories without a token")
    
    print("-" * 50)
    
    # Check access to each repository
    if Config.GITHUB_TOKEN:
        print("Checking repository access...")
        for repo in repos:
            can_access, message = check_private_repo_access(Config.GITHUB_TOKEN, repo)
            if can_access:
                print(f"  ✓ {repo}: {message}")
            else:
                print(f"  ⚠️  {repo}: {message}")
        print()
    
    # Initial check for all repos
    print("Performing initial check for all repositories...")
    for repo in repos:
        try:
            issues = github.get_open_issues(
                repo=repo,
                author=Config.AUTHOR_NAME
            )
            print(f"  ✓ {repo}: Found {len(issues)} open issue(s)")
            
            # Mark existing issues as notified (don't alert on startup)
            for issue in issues:
                state.mark_notified(repo, issue.get("number"))
        except GitHubError as e:
            print(f"  ⚠️  {repo}: {e}")
        except Exception as e:
            print(f"  ⚠️  {repo}: Unexpected error - {e}")
    
    print("\nInitial state loaded. Monitoring for new issues...\n")
    
    # Main monitoring loop
    repo_error_counts = {repo: 0 for repo in repos}
    max_consecutive_errors = 10
    
    while True:
        try:
            total_new_issues = 0
            successful_repos = 0
            
            # Check each repository
            for repo in repos:
                try:
                    # Fetch current issues
                    issues = github.get_open_issues(
                        repo=repo,
                        author=Config.AUTHOR_NAME
                    )
                    
                    # Reset error counter for this repo on success
                    repo_error_counts[repo] = 0
                    successful_repos += 1
                    
                    # Filter to only new issues
                    new_issues = state.get_new_issues(repo, issues)
                    
                    if new_issues:
                        total_new_issues += len(new_issues)
                        print(f"[{repo}] Found {len(new_issues)} new issue(s)!")
                        
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
                    repo_error_counts[repo] += 1
                    print(f"⚠️  [{repo}] GitHub API error: {e}")
                    if repo_error_counts[repo] < max_consecutive_errors:
                        print(f"   Will retry on next poll (error {repo_error_counts[repo]}/{max_consecutive_errors})")
                    else:
                        print(f"   ⚠️  Too many errors for {repo} - skipping in future checks")
                except Exception as e:
                    repo_error_counts[repo] += 1
                    print(f"⚠️  [{repo}] Unexpected error: {e}")
                    if repo_error_counts[repo] < max_consecutive_errors:
                        print(f"   Will retry on next poll (error {repo_error_counts[repo]}/{max_consecutive_errors})")
                    else:
                        print(f"   ⚠️  Too many errors for {repo} - skipping in future checks")
            
            # Summary
            if total_new_issues > 0:
                print(f"\n📊 Summary: {total_new_issues} new issue(s) found across {successful_repos}/{len(repos)} repositories")
            else:
                print(f"\n📊 Summary: No new issues across {successful_repos}/{len(repos)} repositories")
            
            # Check if all repos are failing
            if successful_repos == 0:
                print(f"\n❌ All repositories are failing. Waiting {poll_interval_minutes} minutes before retry...")
            
            # Wait before next check
            print(f"\n⏳ Next check in {poll_interval_minutes} minutes...\n")
            time.sleep(Config.POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            break


if __name__ == "__main__":
    main()

