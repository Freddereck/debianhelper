import os
import shutil
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from app.translations import t
from app.modules.firewall import run_command_for_output # Import from firewall

console = Console()

# List of common services to check
COMMON_SERVICES = ["ssh", "cron", "nginx", "apache2", "mysql", "postgresql", "docker", "fail2ban", "ufw"]

def is_wireguard_installed():
    """Check if 'wg' command is available."""
    return shutil.which("wg") is not None

def get_service_status(service_name):
    """Gets the status of a single service using systemctl."""
    output = run_command_for_output(f"systemctl is-active {service_name}")
    return output.strip() if output else "not found"

def show_all_services():
    """Displays the status of all common services in a table."""
    os.system('cls' if os.name == 'nt' else 'clear')
    table = Table(title=t('services_table_title'))
    table.add_column(t('services_col_service'), style="cyan")
    table.add_column(t('services_col_status'), style="magenta")

    with console.status(t('services_checking_status')):
        for service in COMMON_SERVICES:
            status = get_service_status(service)
            if status == "active":
                status_text = f"[green]{status}[/green]"
            elif status == "inactive" or status == "failed":
                status_text = f"[red]{status}[/red]"
            else:
                status_text = f"[yellow]{status}[/yellow]"
            
            # Only show services that are installed (not 'not found')
            if status != "not found":
                table.add_row(service, status_text)
    
    console.print(table)
    questionary.press_any_key_to_continue().ask()

def show_wireguard_status():
    """Displays the output of 'wg show'."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('services_wireguard_status'), border_style="blue", expand=False))
    
    wg_output = run_command_for_output("sudo wg show")
    if wg_output:
        # Using Syntax for better readability of the output
        syntax = Syntax(wg_output, "bash", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        # This could be due to no interfaces being up or an error
        console.print(t('services_wireguard_error'))
        
    questionary.press_any_key_to_continue().ask()

def show_service_manager():
    """Main menu for the service manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('services_title')}[/bold blue]"))

        choices = [
            t('services_menu_list_all'),
        ]
        
        # Conditionally add WireGuard option
        if is_wireguard_installed():
            choices.append(t('services_wireguard_status'))
            
        choices.append(t('services_menu_back'))

        choice = questionary.select(
            t('services_prompt_action'),
            choices=choices
        ).ask()

        if choice == t('services_menu_list_all'):
            show_all_services()
        elif choice == t('services_wireguard_status'):
            show_wireguard_status()
        elif choice == t('services_menu_back') or choice is None:
            break 