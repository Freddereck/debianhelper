import os
import shutil
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

from localization import get_string

console = Console()
LOG_DIR = Path("/var/log")

IMPORTANT_LOGS = {
    "journalctl": {
        "name_key": "log_journald_name",
        "desc_key": "log_journald_desc",
    },
    "auth.log": {
        "name_key": "log_auth_name",
        "desc_key": "log_auth_desc",
    },
    "dpkg.log": {
        "name_key": "log_dpkg_name",
        "desc_key": "log_dpkg_desc",
    },
    "syslog": {
        "name_key": "log_syslog_name",
        "desc_key": "log_syslog_desc",
    },
    "kern.log": {
        "name_key": "log_kern_name",
        "desc_key": "log_kern_desc",
    },
}

def clear_console():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def _view_log_file(file_path: Path):
    """Displays the last 100 lines of a selected log file."""
    clear_console()
    console.print(Panel(get_string("reading_log_file", path=str(file_path)), title=get_string("log_viewer_title")))
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore').strip()
        if not content:
            console.print(get_string("empty_log_file"))
            return
        lines = content.splitlines()
        log_content = "\n".join(lines[-100:])
        syntax = Syntax(log_content, "log", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=get_string("last_100_lines"), border_style="green"))
    except PermissionError:
        console.print(get_string("permission_denied"))
    except FileNotFoundError:
        console.print(get_string("log_file_not_found"))
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")

def _clear_log_file(file_path: Path):
    """Clears the content of a given log file after confirmation."""
    if os.geteuid() != 0:
        console.print(get_string("permission_denied"))
        return
    
    wants_to_clear = inquirer.confirm(
        message=get_string("clear_confirm_prompt"),
        default=False
    ).execute()

    if wants_to_clear:
        try:
            with open(file_path, 'w') as f:
                pass # Opening in 'w' mode and closing truncates the file
            console.print(get_string("clear_success", filename=file_path.name))
        except Exception as e:
            console.print(get_string("clear_fail", filename=file_path.name))
            console.print(f"[red]{e}[/red]")

def _view_journalctl():
    """Displays the last 100 lines from journalctl."""
    clear_console()
    console.print(Panel(get_string("reading_log_file", path="journalctl"), title=get_string("log_viewer_title")))
    try:
        result = subprocess.run(['journalctl', '--no-pager', '-n', '100'], capture_output=True, text=True, check=True)
        log_content = result.stdout.strip()
        if not log_content:
            console.print(get_string("empty_log_file"))
            return
        syntax = Syntax(log_content, "log", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=get_string("last_100_lines"), border_style="green"))
    except FileNotFoundError:
        console.print("[red]'journalctl' command not found. Is systemd running?[/red]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running journalctl: {e.stderr}[/red]")
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")

def run_log_viewer():
    """Scans /var/log, presents a structured menu, and views or clears selected logs."""
    if os.geteuid() != 0:
        console.print(f"[yellow]Warning:[/yellow] You are not running as root. You may not have permission to read or clear all log files.")
    
    while True:
        try:
            important_log_keys = set(IMPORTANT_LOGS.keys())
            
            # --- Build Choices ---
            choices = [Separator(get_string("important_logs_title"))]
            
            for log_key, data in IMPORTANT_LOGS.items():
                is_journal = log_key == "journalctl"
                path = LOG_DIR / log_key if not is_journal else None
                exists = (is_journal and shutil.which("journalctl")) or (path and path.exists())
                if exists:
                    name = f"{get_string(data['name_key'])}\n  {get_string(data['desc_key'])}"
                    choices.append(Choice(value={"type": "important", "path": path or log_key}, name=name))
            
            choices.append(Separator(get_string("other_logs_title")))
            other_files = sorted([f for f in LOG_DIR.glob('*') if f.is_file() and f.name not in important_log_keys], key=os.path.getmtime, reverse=True)
            for file in other_files[:15]:
                 choices.append(Choice(value={"type": "other", "path": file}, name=file.name))

            choices.append(Separator())
            choices.append(Choice(value=None, name=get_string("back_to_main_menu")))
            
            # --- Main Menu ---
            clear_console()
            console.print(Panel(get_string("log_viewer_title"), style="bold green", subtitle=f"Found in {LOG_DIR}"))
            
            selected = inquirer.select(
                message=get_string("log_viewer_prompt"), choices=choices, vi_mode=True, pointer="» ", height=None,
            ).execute()

            if selected is None: break

            # --- Handle Selection ---
            selection_type = selected["type"]
            selection_path = selected["path"]

            if selection_type == "important":
                if selection_path == "journalctl": _view_journalctl()
                else: _view_log_file(selection_path)
                inquirer.text(message="\n" + get_string("press_enter_to_continue"), vi_mode=True).execute()

            elif selection_type == "other":
                action = inquirer.select(
                    message=get_string("log_actions_prompt", filename=selection_path.name),
                    choices=[
                        Choice("view", get_string("action_view")),
                        Choice("clear", get_string("action_clear")),
                        Separator(),
                        Choice(None, get_string("action_back")),
                    ],
                    pointer="» ",
                ).execute()
                
                if action == "view":
                    _view_log_file(selection_path)
                    inquirer.text(message="\n" + get_string("press_enter_to_continue"), vi_mode=True).execute()
                elif action == "clear":
                    _clear_log_file(selection_path)
                    inquirer.text(message="\n" + get_string("press_enter_to_continue"), vi_mode=True).execute()

        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break
        except Exception as e:
            console.print(f"[red]An error occurred in the log viewer: {e}[/red]")
            break 