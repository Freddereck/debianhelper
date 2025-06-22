import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.translations import t
from app.utils import run_command

console = Console()

def list_enabled_services():
    """Lists all enabled systemd services."""
    console.print(f"[yellow]{t('autostart_listing')}...[/yellow]")
    
    output = run_command("systemctl list-unit-files --state=enabled --no-pager")
    
    table = Table(title=t('autostart_enabled_title'))
    table.add_column(t('autostart_col_unit'), style="cyan")
    table.add_column(t('autostart_col_state'), style="green")
    
    lines = output.strip().split('\n')
    # First and last lines are header/footer, skip them
    for line in lines[1:-1]:
        parts = line.split()
        if len(parts) >= 2:
            table.add_row(parts[0], parts[1])
            
    if not table.rows:
        console.print(f"[green]{t('autostart_no_services')}[/green]")
    else:
        console.print(table)
    
    questionary.press_any_key_to_continue().ask()

def disable_service():
    """Disables a service from starting on boot."""
    service = questionary.text(t('autostart_prompt_disable')).ask()
    if not service:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    console.print(t('autostart_disabling', service=service))
    run_command(f"sudo systemctl disable {service}", show_output=True)
    questionary.press_any_key_to_continue().ask()

def enable_service():
    """Enables a service to start on boot."""
    service = questionary.text(t('autostart_prompt_enable')).ask()
    if not service:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return

    console.print(t('autostart_enabling', service=service))
    run_command(f"sudo systemctl enable {service}", show_output=True)
    questionary.press_any_key_to_continue().ask()

def show_autostart_manager():
    """Main menu for the autostart manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold green]{t('autostart_title')}[/bold green]"))
        
        choice = questionary.select(
            t('main_prompt'),
            choices=[
                t('autostart_menu_list'),
                t('autostart_menu_disable'),
                t('autostart_menu_enable'),
                t('back_to_main_menu')
            ]
        ).ask()

        if choice == t('autostart_menu_list'):
            list_enabled_services()
        elif choice == t('autostart_menu_disable'):
            disable_service()
        elif choice == t('autostart_menu_enable'):
            enable_service()
        elif choice == t('back_to_main_menu') or choice is None:
            break 