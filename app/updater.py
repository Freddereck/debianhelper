import re
import os
import questionary
import base64
import json
import subprocess
from packaging import version
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from app.translations import t

# GitHub repository details
GITHUB_REPO = "Freddereck/debianhelper"

console = Console()

def get_remote_file_content_with_curl(path):
    """Fetches and decodes file content from GitHub API using curl."""
    try:
        command = [
            'curl',
            '-sL', # Silent, follow redirects
            '-H', 'Accept: application/vnd.github.v3+json', # Specify API version
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
        data = json.loads(result.stdout)
        content_b64 = data.get('content', '')
        if not content_b64:
            return None
        return base64.b64decode(content_b64).decode('utf-8')
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

def get_remote_version():
    """Fetches the version from the remote server_panel.py file via API using curl."""
    content = get_remote_file_content_with_curl("server_panel.py")
    if content:
        match = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", content)
        if match:
            return match.group(1)
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

def get_latest_changelog_notes(full_changelog, new_version):
    """Parses the full changelog to extract notes for the latest version."""
    if not full_changelog:
        return None
    
    # Regex to find version headers like "## [1.2.3]" or "## 2.3.4"
    version_headers = list(re.finditer(r"^##\s*\[?(\d+\.\d+\.\d+(\.\d+)*)\]?", full_changelog, re.MULTILINE))
    
    if not version_headers:
        # If no standard version headers are found, return the whole log as a fallback.
        return full_changelog

    # Find the start of the notes for the *new* version
    latest_version_start_index = -1
    for match in version_headers:
        if match.group(1) == new_version:
            latest_version_start_index = match.start()
            break
            
    if latest_version_start_index == -1:
        # If the new version isn't in the changelog yet, maybe just show the top.
        # This is a safe fallback.
        first_header = version_headers[0]
        second_header_start = version_headers[1].start() if len(version_headers) > 1 else len(full_changelog)
        return full_changelog[first_header.start():second_header_start].strip()

    # Find where the next section (previous version) begins
    next_section_start_index = len(full_changelog) # Default to end of file
    for match in version_headers:
        if match.start() > latest_version_start_index:
            next_section_start_index = match.start()
            break
            
    return full_changelog[latest_version_start_index:next_section_start_index].strip()

def get_changelog():
    """Fetches the CHANGELOG.md file from GitHub via API using curl."""
    return get_remote_file_content_with_curl("CHANGELOG.md")

def check_for_updates(on_startup=False):
    """Checks for updates and prompts the user if a new version is available."""
    if not on_startup:
        console.print(f"[cyan]{t('updater_checking')}[/cyan]")
        console.print(Panel(t('updater_insecure_warning'), border_style="bold yellow"))

    remote_v = get_remote_version()
    
    # Handle case where remote version check fails
    if not remote_v:
        if not on_startup:
            console.print(Panel(f"[bold red]{t('updater_remote_error')}[/bold red]", title="[bold red]Error[/bold red]"))
            questionary.press_any_key_to_continue().ask()
        return  # Silently fail on startup, show error on manual check

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

    if remote_v > local_v:
        if not on_startup:
            # Show a full panel if manually checked
            console.print(Panel(t('updater_new_version_found', new_version=remote_v), style="bold green"))
        else:
            # Show a more subtle message on startup
            console.print(f"[bold green]>>[/bold green] {t('updater_new_version_found', new_version=remote_v)}")
            
        if questionary.confirm(t('updater_prompt_update')).ask():
            console.print(f"[cyan]{t('updater_updating')}...[/cyan]")
            return_code = os.system("git fetch --all && git reset --hard origin/main")
            if return_code == 0:
                console.print(f"[green]{t('updater_pull_success')}[/green]")
                console.print(f"[bold cyan]{t('updater_restart_required')}[/bold cyan]")
                questionary.press_any_key_to_continue().ask()
                exit()  # Exit to force user to restart with the new code
            else:
                console.print(f"[red]{t('updater_pull_failed')}[/red]")
                questionary.press_any_key_to_continue().ask()
    else:
        # This part is reached only when not on startup and no update is available
        console.print(f"[green]{t('updater_up_to_date')}[/green]")
        questionary.press_any_key_to_continue().ask() 