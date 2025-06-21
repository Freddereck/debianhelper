import os
import questionary
from rich.console import Console
from rich.panel import Panel

# Local imports
from app.translations import set_language, t
from app.updater import check_for_updates
from app.modules.health import show_health_check
from app.modules.services import show_service_manager
from app.modules.docker import show_docker_manager
from app.modules.monitor import show_htop_monitor
from app.modules.security import show_security_menu
from app.modules.dev_tools import show_dev_tools_menu
from app.modules.cron import show_cron_manager
from app.modules.logs import show_log_viewer
from app.modules.packages import show_package_manager
from app.modules.firewall import show_firewall_manager
from app.modules.users import show_user_manager
from app.modules.network import show_network_info
from app.modules.pm2 import show_pm2_manager

# Version of the application
__version__ = "2.1.0"

console = Console()

def main_menu():
    """Displays the main menu and handles user input."""
    # check_for_updates() # Check for updates on start

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold cyan]Server Panel v{__version__}[/bold cyan]", 
                            title=t('main_menu_title'), 
                            subtitle=t('main_menu_subtitle')))
        
        choices = {
            t('menu_health_check'): show_health_check,
            t('menu_service_manager'): show_service_manager,
            t('menu_docker_manager'): show_docker_manager,
            t('menu_monitor'): show_htop_monitor,
            t('menu_security_audit'): show_security_menu,
            t('menu_dev_tools'): show_dev_tools_menu,
            t('menu_cron_manager'): show_cron_manager,
            t('menu_log_viewer'): show_log_viewer,
            t('menu_package_manager'): show_package_manager,
            t('menu_firewall_manager'): show_firewall_manager,
            t('menu_user_manager'): show_user_manager,
            t('menu_network_info'): show_network_info,
            t('menu_pm2_manager'): show_pm2_manager,
            t('menu_exit'): "exit"
        }

        action = questionary.select(
            t('main_menu_prompt'),
            choices=list(choices.keys()),
            pointer="👉"
        ).ask()

        if action is None or choices[action] == "exit":
            break
        
        # Call the selected function
        selected_function = choices.get(action)
        if selected_function:
            selected_function()

if __name__ == "__main__":
    set_language()
    main_menu()