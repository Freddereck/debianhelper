import os
import re
import subprocess
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.utils import run_command

console = Console()

# --- JournalCTL Based Logger (Primary) ---

JOURNAL_SERVICES = {
    "System Journal": "-n {lines}",
    "Kernel Log": "-k -n {lines}",
    "SSH Daemon": "-u sshd -n {lines}",
    "Nginx": "-u nginx -n {lines}",
    "UFW": "-u ufw -n {lines}",
}

def show_journalctl_viewer():
    """Shows logs using journalctl for modern systems."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold cyan]Log Viewer (JournalCTL Mode)[/bold cyan]"))
    
    choices = list(JOURNAL_SERVICES.keys()) + ["Custom Service", "Custom Log File", "Back"]
    choice = questionary.select("Which logs to view?", choices=choices).ask()

    if choice is None or choice == "Back":
        return

    if choice == "Custom Log File":
        view_raw_log_file() # Fallback to raw file viewer
        return

    n_lines = questionary.text("How many lines to show?", default="50", validate=lambda t: t.isdigit()).ask()
    
    cmd_template = ""
    if choice == "Custom Service":
        service_name = questionary.text("Enter service name (e.g., postgresql):").ask()
        if not service_name: return
        cmd_template = f"-u {service_name} -n {n_lines}"
    else:
        cmd_template = JOURNAL_SERVICES[choice].format(lines=n_lines)

    os.system('cls' if os.name == 'nt' else 'clear')
    command = f"sudo journalctl {cmd_template} --no-pager -o cat"
    console.print(f"[dim]Running: {command}[/dim]")
    
    log_output = run_command(command)
    console.print(Panel(log_output if log_output else "[dim]-- No entries --[/dim]", 
                      title=f"Logs for {choice}", expand=False))
    
    questionary.press_any_key_to_continue().ask()

# --- File Based Logger (Fallback) ---

def view_raw_log_file():
    """Allows viewing and tailing any raw log file."""
    log_file = questionary.path("Enter the path to the log file:").ask()
    if not log_file or not os.path.exists(log_file):
        console.print("[red]File not found.[/red]"); time.sleep(1); return
    
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"Viewing: {log_file}"))
    n_lines = questionary.text("How many lines to show?", default="50").ask()
    console.print(Panel(run_command(f"sudo tail -n {n_lines} {log_file}"), title=f"Raw Log: {log_file}"))
    questionary.press_any_key_to_continue().ask()


# --- Main Entry Point ---

def show_log_viewer():
    """
    Main entry point for the log viewer.
    Detects if journalctl is available and shows the appropriate menu.
    """
    if os.name != 'nt' and run_command("which journalctl"):
        show_journalctl_viewer()
    else:
        # Fallback for Windows or systems without journalctl
        console.print("[yellow]journalctl not found. Falling back to raw file viewer.[/yellow]")
        time.sleep(1)
        view_raw_log_file() 