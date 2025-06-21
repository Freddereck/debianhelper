import os
import questionary
from rich.console import Console
from rich.panel import Panel
from app.translations import t
from app.utils import run_command, run_command_live
from app.modules.firewall import run_command_for_output # Reusing this handy function

console = Console()

def update_package_lists():
    """Runs apt update."""
    console.print(f"[yellow]{t('packages_update_running')}[/yellow]")
    return_code = run_command("sudo apt-get update", show_output=True, ignore_errors=True)
    if return_code == 0:
        console.print(f"[green]{t('packages_update_success')}[/green]")
    else:
        console.print(f"[red]{t('packages_update_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def upgrade_packages():
    """Runs apt upgrade."""
    if questionary.confirm(t('packages_upgrade_confirm')).ask():
        console.print(f"[yellow]{t('packages_upgrade_running')}[/yellow]")
        console.print(f"[dim]{t('packages_upgrade_log')}[/dim]")
        # Using run_command_live for better user experience
        return_code = run_command_live("sudo apt-get upgrade -y", "apt_upgrade.log")
        if return_code == 0:
            console.print(f"[green]{t('packages_upgrade_success')}[/green]")
        else:
            console.print(f"[red]{t('packages_upgrade_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def autoremove_packages():
    """Runs apt autoremove."""
    if questionary.confirm(t('packages_autoremove_confirm')).ask():
        console.print(f"[yellow]{t('packages_autoremove_running')}[/yellow]")
        return_code = run_command("sudo apt-get autoremove -y", show_output=True, ignore_errors=True)
        if return_code == 0:
            console.print(f"[green]{t('packages_autoremove_success')}[/green]")
        else:
            console.print(f"[red]{t('packages_autoremove_error')}[/red]")
    questionary.press_any_key_to_continue().ask()

def list_all_packages():
    """Lists all installed packages with their versions."""
    os.system('cls' if os.name == 'nt' else 'clear')
    with console.status(t('packages_list_running')):
        package_list = run_command_for_output("dpkg-query -W -f='${Package;-30}\t${Version}\\n'")
    
    if package_list:
        console.print(Panel(package_list, title=t('packages_list_title'), border_style="green", expand=False))
    else:
        console.print(f"[red]{t('packages_list_error')}[/red]")
    
    questionary.press_any_key_to_continue().ask()

def show_package_manager():
    """Main menu for the APT package manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('packages_title')}[/bold blue]"))

        choice = questionary.select(
            t('packages_prompt_action'),
            choices=[
                t('packages_menu_update'),
                t('packages_menu_upgrade'),
                t('packages_menu_list'),
                t('packages_menu_autoremove'),
                t('packages_menu_back'),
            ]
        ).ask()

        if choice == t('packages_menu_update'):
            update_package_lists()
        elif choice == t('packages_menu_upgrade'):
            upgrade_packages()
        elif choice == t('packages_menu_list'):
            list_all_packages()
        elif choice == t('packages_menu_autoremove'):
            autoremove_packages()
        elif choice == t('packages_menu_back') or choice is None:
            break 