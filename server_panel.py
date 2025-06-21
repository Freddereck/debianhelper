import os
import questionary
from rich.console import Console
from rich.panel import Panel

# Local imports
from app.translations import load_language, t
from app.updater import check_for_updates
from app.modules.health import run_system_health_check
from app.modules.services import show_service_manager
from app.modules.docker import show_docker_manager
from app.modules.monitor import show_htop_monitor
from app.modules.security import run_security_audit
from app.modules.dev_tools import show_dev_manager
from app.modules.cron import show_cron_manager
from app.modules.logs import show_log_viewer
from app.modules.packages import show_package_manager
from app.modules.firewall import show_firewall_manager
from app.modules.users import show_user_manager
from app.modules.network import show_network_toolkit
from app.modules.pm2 import show_pm2_manager
from app.modules.software_manager import show_software_manager
from app.utils import is_tool_installed

# Version of the application
__version__ = "2.2.2"

console = Console()

def main_menu():
    """Displays the main menu and handles user input."""
    # check_for_updates(on_startup=True) is called at startup now

    menu_options = {
        t('menu_health_check'): run_system_health_check,
        t('menu_service_manager'): show_service_manager,
        t('menu_docker_manager'): show_docker_manager,
        t('menu_software_manager'): show_software_manager,
        t('menu_monitor'): show_htop_monitor,
        t('menu_security_audit'): run_security_audit,
        t('menu_dev_tools'): show_dev_manager,
        t('menu_cron_manager'): show_cron_manager,
        t('menu_log_viewer'): show_log_viewer,
        t('menu_package_manager'): show_package_manager,
        t('menu_firewall_manager'): show_firewall_manager,
        t('menu_user_manager'): show_user_manager,
        t('menu_network_info'): show_network_toolkit,
    }

    # Conditionally add PM2 manager if installed
    if is_tool_installed('pm2'):
        menu_options[t('menu_pm2_manager')] = show_pm2_manager

    # Add remaining options
    menu_options[t('menu_check_updates')] = lambda: check_for_updates(on_startup=False)
    menu_options[t('menu_exit')] = "exit"
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        header = Panel(f"[bold bright_cyan]Server Panel v{__version__}[/bold bright_cyan]", 
                       title=f"[bold blue]🔥 {t('main_menu_title')} 🔥[/bold blue]", 
                       subtitle=f"[italic cyan]mderick.su[/italic cyan]",
                       border_style="bold magenta")
        console.print(header)

        action = questionary.select(
            t('main_menu_prompt'),
            choices=list(menu_options.keys()),
            pointer="👉",
            use_indicator=True,
            style=questionary.Style([
                ('pointer', 'bold fg:yellow'),
                ('highlighted', 'bold fg:yellow'),
                ('selected', 'fg:white bg:blue'),
            ])
        ).ask()

        if action is None or menu_options.get(action) == "exit":
            break
        
        selected_function = menu_options.get(action)
        if selected_function:
            console.clear()
            selected_function()

if __name__ == "__main__":
    # Language Selection
    lang_code = load_language()

    # Check for updates on start
    check_for_updates(on_startup=True)

    try:
        # Warn if not running as root, as many functions require sudo
        if os.name != 'nt' and os.geteuid() != 0:
            console.print(f"[bold yellow]{t('root_warning')}[/bold yellow]")
            questionary.press_any_key_to_continue().ask()
        main_menu()
    except Exception as e:
        console.print(f"\n[bold red]{t('critical_error', error=e)}[/bold red]")
        # In case of a crash, ensure the cursor is visible
        console.show_cursor(True)