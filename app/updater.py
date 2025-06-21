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
GITHUB_REPO = "debianhelper/server-panel"

console = Console()

def get_latest_release_info():
    """Fetches the latest release information from the GitHub API."""
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
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

def check_for_updates(on_startup=False):
    """Checks for updates and prompts the user if a new version is available."""
    if not on_startup:
        console.print(f"[cyan]{t('updater_checking')}[/cyan]")

    release_info = get_latest_release_info()

    # Handle case where remote version check fails
    if not release_info:
        if not on_startup:
            console.print(Panel(f"[bold red]{t('updater_remote_error')}[/bold red]", title="[bold red]Error[/bold red]"))
            questionary.press_any_key_to_continue().ask()
        return  # Silently fail on startup, show error on manual check

    remote_v_tag = release_info.get("tag_name", "0.0.0")
    remote_v = remote_v_tag.lstrip('v') # Remove 'v' prefix if it exists
    changelog = release_info.get("body", t('updater_changelog_error'))

    local_v = get_local_version()

    # Handle case where local version can't be read (less likely)
    if not local_v:
        console.print(Panel(f"[bold red]{t('updater_local_error')}[/bold red]", title="[bold red]Error[/bold red]"))
        questionary.press_any_key_to_continue().ask()
        return

    is_update_available = version.parse(local_v) < version.parse(remote_v)

    if not is_update_available and on_startup:
        return  # Silently return on startup if no update is available

    console.print(Panel(t('updater_version_comparison', local=local_v, remote=remote_v), style="bold yellow"))

    if is_update_available:
        console.print(Panel(t('updater_new_version_found', version=remote_v), style="bold green"))
        
        console.print(Panel(Markdown(changelog), title=t('updater_changelog_title'), border_style="cyan"))

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