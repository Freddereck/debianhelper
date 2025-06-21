import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.translations import t
from app.utils import run_command_for_output # Reusing this handy function

console = Console()

def get_installed_packages():
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