import re
import os
import questionary
import base64
import json
import subprocess
from packaging.version import parse as parse_version
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

def get_relevant_changelog_entries(local_version_str):
    """
    Parses the local CHANGELOG.md and returns all entries for versions
    newer than the given local_version_str.
    """
    try:
        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            full_changelog = f.read()
    except FileNotFoundError:
        return t('updater_changelog_not_found')

    local_version = parse_version(local_version_str)
    relevant_notes = []

    # Regex to find version headers like "## [1.2.3]" or "## 2.3.4"
    # and capture the content until the next header
    pattern = re.compile(r"##\s*\[?(\d+\.\d+\.\d+.*)\]?.*?\n(.*?)(?=\n##\s*\[?|\Z)", re.DOTALL)
    
    for match in pattern.finditer(full_changelog):
        version_str = match.group(1).strip()
        notes = match.group(2).strip()
        try:
            changelog_version = parse_version(version_str)
            if changelog_version > local_version:
                # Prepend the version header to its notes
                relevant_notes.append(f"## {version_str}\n{notes}")
        except Exception:
            # Ignore parsing errors for version strings in changelog
            continue

    if not relevant_notes:
        return t('updater_no_new_changes')

    return "\n\n".join(relevant_notes)

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
    """Fetches the CHANGELOG.md file from GitHub via API using curl."""
    return get_remote_file_content_with_curl("CHANGELOG.md")

def check_for_updates(on_startup=False):
    """Checks for updates and prompts the user if a new version is available."""
    if not on_startup:
        console.print(f"[cyan]{t('updater_checking')}[/cyan]")
        console.print(Panel(t('updater_insecure_warning'), border_style="bold yellow"))

    remote_v_str = get_remote_version()
    local_v_str = get_local_version()

    if not remote_v_str or not local_v_str:
        if not on_startup:
            console.print(f"[bold red]{t('updater_version_error')}[/bold red]")
        return

    remote_version = parse_version(remote_v_str)
    local_version = parse_version(local_v_str)

    if remote_version > local_version:
        console.print(Panel(
            t('updater_new_version_found', new_version=remote_v_str),
            border_style="bold green",
            title=t('updater_title')
        ))

        # --- Display relevant changelog entries ---
        changelog_notes = get_relevant_changelog_entries(local_v_str)
        if changelog_notes:
            console.print(Panel(
                Markdown(changelog_notes), 
                title=t('updater_changelog_title'), 
                border_style="cyan"
            ))
        # -----------------------------------------

        if questionary.confirm(t('updater_prompt_update')).ask():
            console.print(f"[cyan]{t('updater_updating')}...[/cyan]")
            # Use git pull for updating
            process = subprocess.run(["git", "pull"], capture_output=True, text=True)
            if process.returncode == 0:
                console.print(f"[green]{t('updater_pull_success')}[/green]")
                console.print(f"[bold cyan]{t('updater_restart_required')}[/bold cyan]")
                questionary.press_any_key_to_continue().ask()
                exit()
            else:
                console.print(Panel(t('updater_pull_failed', error=process.stderr), title="[bold red]Error[/bold red]"))
                questionary.press_any_key_to_continue().ask()
    elif not on_startup:
        console.print(f"[green]{t('updater_up_to_date')}[/green]")
        questionary.press_any_key_to_continue().ask() 