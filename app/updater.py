import requests
import re
import os
import questionary
from packaging import version
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from app.translations import t

# GitHub repository details
GITHUB_REPO_URL = "https://github.com/debianhelper/server-panel" # Replace with your actual repo URL if different
RAW_CONTENT_URL = "https://raw.githubusercontent.com/debianhelper/server-panel/main" # Replace if different

console = Console()

def get_remote_version():
    """Fetches the version from the remote server_panel.py file."""
    try:
        url = f"{RAW_CONTENT_URL}/server_panel.py"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        match = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", response.text)
        if match:
            return match.group(1)
    except (requests.RequestException, re.error):
        return None
    return None

def get_local_version():
    """Reads the version from the local server_panel.py file."""
    try:
        with open("server_panel.py", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", content)
            if match:
                return match.group(1)
    except (IOError, re.error):
        return None
    return None

def get_changelog():
    """Fetches the CHANGELOG.md file from GitHub."""
    try:
        url = f"{RAW_CONTENT_URL}/CHANGELOG.md"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None

def check_for_updates(on_startup=False):
    """Checks for updates and prompts the user if a new version is available."""
    local_v = get_local_version()
    remote_v = get_remote_version()

    if not local_v or not remote_v:
        return # Cannot compare versions
    
    is_update_available = version.parse(local_v) < version.parse(remote_v)

    if not is_update_available and on_startup:
        return # Silently return on startup if no update is available

    console.print(Panel(t('updater_version_comparison', local=local_v, remote=remote_v), style="bold yellow"))

    if is_update_available:
        console.print(Panel(t('updater_new_version_found', version=remote_v), style="bold green"))
        
        changelog = get_changelog()
        if changelog:
            console.print(Panel(Markdown(changelog), title=t('updater_changelog_title'), border_style="cyan"))
        else:
            console.print(f"[yellow]{t('updater_changelog_error')}[/yellow]")

        if questionary.confirm(t('updater_prompt_update')).ask():
            console.print(f"[yellow]{t('updater_running_pull')}[/yellow]")
            return_code = os.system("git fetch --all && git reset --hard origin/main")
            if return_code == 0:
                console.print(f"[green]{t('updater_pull_success')}[/green]")
                console.print(f"[bold cyan]{t('updater_restart_required')}[/bold cyan]")
                questionary.press_any_key_to_continue().ask()
                exit() # Exit to force user to restart with the new code
            else:
                console.print(f"[red]{t('updater_pull_failed')}[/red]")
                questionary.press_any_key_to_continue().ask()
    else:
        # This part is reached only when not on startup and no update is available
        console.print(f"[green]{t('updater_up_to_date')}[/green]")
        questionary.press_any_key_to_continue().ask() 