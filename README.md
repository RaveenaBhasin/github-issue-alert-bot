# GitHub Issue Alert Monitor

A Python application that monitors GitHub repositories for new issues and sends Telegram alerts when they're opened. You can monitor multiple repositories and optionally filter by issue author.

## Features

- Monitor multiple GitHub repositories simultaneously
- Optional filtering by issue author
- Telegram notifications with issue details and links
- Per-repository state tracking to avoid duplicate alerts
- Graceful error handling - continues monitoring even if one repo fails
- Configurable polling interval

## Quick Start

### Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token (optional for public repos, required for private)
- Telegram Bot Token and Chat ID
