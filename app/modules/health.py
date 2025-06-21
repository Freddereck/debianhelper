import os
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.utils import run_command, run_command_live
from app.translations import t

console = Console()

def check_updates():
    """Checks for available package updates and offers to install them."""
    console.print(f"[yellow]{t('health_checking_updates')}[/yellow]")
    
    # Update package list first quietly
    run_command("sudo apt-get update -qq")
    
    # Get list of upgradable packages
    upgradable_raw = run_command("apt list --upgradable 2>/dev/null | tail -n +2")
    
    if not upgradable_raw:
        console.print(f"[green]{t('health_no_updates')}[/green]")
        return
        
    upgradable_packages = upgradable_raw.strip().split('\n')
    package_count = len(upgradable_packages)

    console.print(f"[bold cyan]{t('health_updates_found', count=package_count)}[/bold cyan]")
    
    table = Table(title=t('health_updates_list'))
    table.add_column("Package", style="cyan")
    table.add_column("Current Version", style="magenta")
    table.add_column("New Version", style="green")

    for pkg in upgradable_packages:
        parts = pkg.split()
        table.add_row(parts[0], parts[3], parts[1])
        
    console.print(table)
    
    if questionary.confirm(t('health_prompt_upgrade')).ask():
        console.print(f"\n[yellow]{t('health_starting_upgrade')}[/yellow]")
        run_command_live("sudo apt-get upgrade -y", "apt_upgrade.log")
        console.print(f"[bold green]{t('health_upgrade_complete')}[/bold green]")

def perform_cleanup():
    """Performs system cleanup by running autoremove and clean."""
    if not questionary.confirm(t('health_cleanup_prompt')).ask():
        return

    console.print(f"\n[yellow]{t('health_running_autoremove')}[/yellow]")
    run_command_live("sudo apt-get autoremove -y", "apt_autoremove.log")
    
    console.print(f"\n[yellow]{t('health_running_clean')}[/yellow]")
    run_command_live("sudo apt-get clean", "apt_clean.log")
    
    console.print(f"\n[bold green]{t('health_cleanup_finished')}[/bold green]")

def run_system_health_check():
    """Main menu for the system health check module."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold green]{t('health_title')}[/bold green]"))
        
        choice = questionary.select(
            t('main_prompt'),
            choices=[
                t('health_menu_check_updates'),
                t('health_menu_cleanup'),
                t('health_menu_back')
            ]
        ).ask()

        if choice == t('health_menu_check_updates'):
            check_updates()
            console.print(f"\n[cyan]{t('health_press_enter')}[/cyan]")
            input()
        elif choice == t('health_menu_cleanup'):
            perform_cleanup()
            console.print(f"\n[cyan]{t('health_press_enter')}[/cyan]")
            input()
        elif choice == t('health_menu_back') or choice is None:
            break 