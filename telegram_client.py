"""Telegram bot client for sending alerts."""
import requests
from typing import Optional
from config import Config


class TelegramClient:
    """Client for sending messages via Telegram bot."""
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram client with bot token and chat ID."""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.url = f"{self.BASE_URL}{bot_token}"
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to the configured chat.
        
        Args:
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def format_issue_alert(self, issue: dict, repo: str) -> str:
        """
        Format a GitHub issue as a Telegram message with clickable link.
        
        Args:
            issue: Issue dictionary from GitHub API
            repo: Repository name
        
        Returns:
            Formatted message string with HTML formatting
        """
        title = issue.get("title", "Untitled")
        number = issue.get("number", "?")
        url = issue.get("html_url", "")
        author = issue.get("user", {}).get("login", "Unknown")
        body = issue.get("body", "")
        labels = issue.get("labels", [])
        
        # Truncate body if too long
        if body and len(body) > 300:
            body = body[:300] + "..."
        
        # Format labels if present
        label_text = ""
        if labels:
            label_names = [label.get("name", "") for label in labels[:5]]  # Max 5 labels
            label_text = " ".join([f"#{label}" for label in label_names if label])
        
        message = f"🔔 <b>New Issue Opened</b>\n\n"
        message += f"<b>Repository:</b> <code>{repo}</code>\n"
        message += f"<b>Author:</b> {author}\n"
        message += f"<b>Issue #{number}:</b> {title}\n"
        
        if label_text:
            message += f"<b>Labels:</b> {label_text}\n"
        
        message += "\n"
        
        if body:
            # Escape HTML in body to prevent formatting issues
            body_escaped = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            message += f"<b>Description:</b>\n{body_escaped}\n\n"
        
        # Make the link prominent and clickable
        message += f"🔗 <a href='{url}'><b>View Issue on GitHub →</b></a>\n"
        message += f"<code>{url}</code>"
        
        return message

