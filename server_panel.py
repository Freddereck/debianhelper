import os
import sys
import time

import psutil
import questionary
from rich.console import Console
from rich.panel import Panel

# Modular imports
from app.modules.monitor import show_live_monitor, show_advanced_monitor
from app.modules.health import run_system_health_check
from app.modules.security import run_security_audit
from app.modules.logs import show_log_viewer
from app.modules.cron import show_cron_manager
from app.modules.firewall import show_firewall_manager
from app.modules.services import show_service_manager
from app.modules.packages import show_package_manager
from app.modules.docker import show_docker_manager
from app.modules.pm2 import show_pm2_manager
from app.modules.users import show_user_manager
from app.modules.network import show_network_toolkit
from app.utils import get_uptime

console = Console()

def main():
    """The main interactive loop for the server panel."""
    menu_actions = {
        "Live System Dashboard": show_live_monitor,
        "Advanced System Monitor": show_advanced_monitor,
        "System Health Check": run_system_health_check,
        "Security & Network Audit": run_security_audit,
        "Advanced Log Viewer": show_log_viewer,
        "Network Toolkit": show_network_toolkit,
        "Cron Job Manager": show_cron_manager,
        "Firewall Manager": show_firewall_manager,
        "System Service Manager": show_service_manager,
        "Package Manager (APT)": show_package_manager,
        "Docker Container Manager": show_docker_manager,
        "PM2 Process Manager": show_pm2_manager,
        "User Manager": show_user_manager,
    }

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Main menu title panel
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        uptime_text = get_uptime()
        title_panel = Panel(
            f"[bold green]CPU:[/][green] {cpu_percent:05.1f}%[/]  "
            f"[bold magenta]RAM:[/][magenta] {mem.percent:05.1f}%[/]  "
            f"[bold cyan]Uptime:[/][cyan] {uptime_text}[/]",
            title="Server Control Panel",
            subtitle="v3.0 - Modular"
        )
        console.print(title_panel)
        
        # Main menu selection
        choices = list(menu_actions.keys()) + ["Exit"]
        choice = questionary.select(
            "What would you like to do?",
            choices=choices,
            pointer="👉"
        ).ask()

        if choice is None or choice == "Exit":
            console.print("[bold cyan]Goodbye![/bold cyan]")
            break
        
        # Call the selected function
        action = menu_actions.get(choice)
        if action:
            action()

if __name__ == "__main__":
    try:
        # Check for root/sudo if not on Windows
        if os.name != 'nt' and os.geteuid() != 0:
            console.print("[bold yellow]Warning: Some functions require root privileges (sudo).[/bold yellow]")
            console.print("Running in 3 seconds...")
            time.sleep(3)
        main()
    except Exception as e:
        console.print(f"\n[bold red]A critical error occurred: {e}[/bold red]")
        # Optional: Add full traceback for debugging
        # import traceback
        # traceback.print_exc()
        sys.exit(1) 