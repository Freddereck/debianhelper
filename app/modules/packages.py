import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.translations import t
from app.utils import run_command_for_output

console = Console()

def update_package_lists():
    """Runs apt update."""
    console.print(f"[yellow]{t('packages_update_running')}[/yellow]")
    # Using a direct command as this is a specific, safe operation
    return_code = os.system("sudo apt-get update")
    if return_code == 0:
        console.print(f"[green]{t('packages_update_success')}[/green]")
    else:
        console.print(f"[red]{t('packages_update_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def upgrade_packages():
    """Runs apt upgrade."""
    if questionary.confirm(t('packages_upgrade_confirm')).ask():
        console.print(f"[yellow]{t('packages_upgrade_running')}[/yellow]")
        return_code = os.system("sudo apt-get upgrade -y")
        if return_code == 0:
            console.print(f"[green]{t('packages_upgrade_success')}[/green]")
        else:
            console.print(f"[red]{t('packages_upgrade_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def autoremove_packages():
    """Runs apt autoremove."""
    if questionary.confirm(t('packages_autoremove_confirm')).ask():
        console.print(f"[yellow]{t('packages_autoremove_running')}[/yellow]")
        return_code = os.system("sudo apt-get autoremove -y")
        if return_code == 0:
            console.print(f"[green]{t('packages_autoremove_success')}[/green]")
        else:
            console.print(f"[red]{t('packages_autoremove_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def list_all_packages():
    """Lists all installed packages with their versions."""
    os.system('cls' if os.name == 'nt' else 'clear')
    with console.status(t('packages_listing_status')):
        package_data = run_command_for_output("dpkg-query -W -f='${Package}\t${Version}\n'")
    
    table = Table(title=t('packages_list_title'))
    table.add_column(t('packages_col_name'), style="cyan")
    table.add_column(t('packages_col_version'), style="magenta")

    if package_data:
        for line in package_data.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) == 2:
                table.add_row(parts[0], parts[1])

    console.print(table)
    questionary.press_any_key_to_continue().ask()

def show_package_manager():
    """Main function for the package manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(t('packages_title'), style="bold blue"))
        
        choices = [
            t('packages_menu_list'),
            t('packages_menu_update'),
            t('packages_menu_upgrade'),
            t('packages_menu_autoremove'),
            t('services_menu_back')
        ]
        
        choice = questionary.select(
            t('packages_action_prompt'),
            choices=choices
        ).ask()

        if choice == t('packages_menu_list'):
            list_all_packages()
        elif choice == t('packages_menu_update'):
            update_package_lists()
        elif choice == t('packages_menu_upgrade'):
            upgrade_packages()
        elif choice == t('packages_menu_autoremove'):
            autoremove_packages()
        elif choice == t('services_menu_back') or choice is None:
            break 