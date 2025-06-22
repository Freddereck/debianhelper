import os
import re
import shutil
import questionary
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from app.translations import t
from app.utils import run_command_for_output

console = Console()

# --- Generic Service Management ---

# List of common services to check. This could be expanded or made dynamic.
COMMON_SERVICES = [
    "ssh", "sshd", "cron", "crond",
    "nginx", "apache2", "httpd",
    "mysql", "mariadb", "postgresql",
    "docker", "containerd",
    "fail2ban",
    "systemd-journald", "rsyslog",
    "network-manager", "systemd-networkd",
    "wg-quick@wg0" # Example for a common WireGuard service name
]

def get_service_status(service_name):
    """Gets the status of a single service using systemctl."""
    # We use systemctl list-units to get more info and avoid return codes for non-existent services
    output = run_command_for_output(f"systemctl list-units --type=service --all | grep '{service_name}.service'")
    if not output:
        return "not found"
    
    parts = output.strip().split()
    if len(parts) >= 4:
        # LOAD, ACTIVE, SUB
        status = f"{parts[1]} / {parts[2]} / {parts[3]}"
        if parts[2] == "active":
            return f"[green]{status}[/green]"
        elif parts[2] in ["inactive", "failed"]:
            return f"[red]{status}[/red]"
        else:
            return f"[yellow]{status}[/yellow]"
    return "not found"

def show_all_services():
    """Displays the status of all common services in a table."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold blue]{t('services_title')}[/bold blue]"))

    table = Table(title=t('services_table_title'))
    table.add_column(t('services_col_service'), style="cyan", no_wrap=True)
    table.add_column(t('services_col_status'), style="magenta")

    # Use a set to avoid checking the same service twice (e.g. ssh/sshd)
    checked_services = set()

    with console.status(t('services_checking_status')):
        # Let's try to get a list of actual running services first
        try:
            # Get all active services
            active_services_raw = run_command_for_output("systemctl list-units --type=service --state=active --no-pager --plain | awk '{print $1}'")
            active_services = [s.replace('.service', '') for s in active_services_raw.split('\n') if s.endswith('.service')]
            
            # Combine with our common list to ensure we don't miss important but inactive ones
            services_to_check = sorted(list(set(active_services + COMMON_SERVICES)))
        except Exception:
            # Fallback to the static list if the command fails
            services_to_check = sorted(list(set(COMMON_SERVICES)))


        for service in services_to_check:
            if service in checked_services:
                continue

            status = get_service_status(service)
            
            if status != "not found":
                table.add_row(service, status)
                checked_services.add(service)
    
    console.print(table)
    console.print(f"\n[italic]{t('services_status_note')}[/italic]")
    questionary.press_any_key_to_continue(t('press_any_key')).ask()

def show_service_manager():
    """Main menu for the service manager, now directly shows the list."""
    show_all_services() 