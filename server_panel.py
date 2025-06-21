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
from app.modules.dev_tools import show_dev_manager
from app.utils import get_uptime
from app.translations import load_language, t
from app.updater import check_for_updates

# --- App Version ---
__version__ = "1.0.0"

console = Console()

def main():
    """The main interactive loop for the server panel."""
    menu_actions = {
        t("menu_live_dashboard"): show_live_monitor,
        t("menu_advanced_monitor"): show_advanced_monitor,
        t("menu_health_check"): run_system_health_check,
        t("menu_security_audit"): run_security_audit,
        t("menu_log_viewer"): show_log_viewer,
        t("menu_network_toolkit"): show_network_toolkit,
        t("menu_dev_tools"): show_dev_manager,
        t("menu_cron_manager"): show_cron_manager,
        t("menu_firewall_manager"): show_firewall_manager,
        t("menu_service_manager"): show_service_manager,
        t("menu_package_manager"): show_package_manager,
        t("menu_docker_manager"): show_docker_manager,
        t("menu_pm2_manager"): show_pm2_manager,
        t("menu_user_manager"): show_user_manager,
    }

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        uptime_text = get_uptime()
        
        title_panel = Panel(
            f"[bold green]CPU:[/][green] {cpu_percent:05.1f}%[/]  "
            f"[bold magenta]RAM:[/][magenta] {mem.percent:05.1f}%[/]  "
            f"[bold cyan]Uptime:[/][cyan] {uptime_text}[/]",
            title=t("app_title"),
            subtitle=t("app_subtitle", version=__version__)
        )
        console.print(title_panel)
        
        choices = list(menu_actions.keys()) + [t("menu_exit")]
        choice = questionary.select(
            t("main_prompt"),
            choices=choices,
            pointer="👉"
        ).ask()

        if choice is None or choice == t("menu_exit"):
            console.print(f"[bold cyan]{t('goodbye')}[/bold cyan]")
            break
        
        action = menu_actions.get(choice)
        if action:
            # This is a bit of a hack to get the original key back,
            # might need a better structure if menu grows more complex.
            action()

if __name__ == "__main__":
    # Language Selection
    lang_choice = questionary.select(
        "Please select a language / Пожалуйста, выберите язык:",
        choices=[
            {"name": "English", "value": "en"},
            {"name": "Русский", "value": "ru"}
        ],
        pointer="👉"
    ).ask()

    if lang_choice is None:
        lang_choice = 'en' # Default to english if user cancels
    load_language(lang_choice)

    # Check for updates
    check_for_updates(__version__)

    try:
        if os.name != 'nt' and os.geteuid() != 0:
            console.print(f"[bold yellow]{t('root_warning')}[/bold yellow]")
            time.sleep(2)
        main()
    except Exception as e:
        console.print(f"\n[bold red]{t('critical_error', error=e)}[/bold red]")
        sys.exit(1) 