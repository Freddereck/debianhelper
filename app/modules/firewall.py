import os
import shutil
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import subprocess
from app.translations import t

console = Console()

def is_ufw_active():
    """Check if UFW is installed and active."""
    if not shutil.which('ufw'):
        return False, "not_installed"
    
    try:
        status_output = subprocess.check_output(['ufw', 'status'], text=True)
        return "Status: active" in status_output, "ok"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "error"

def show_firewall_manager():
    """Main function for the firewall manager."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold blue]{t('firewall_title')}[/bold blue]"))

    active, reason = is_ufw_active()

    if not active:
        if reason == "not_installed":
            console.print(Panel(t('firewall_ufw_not_installed'), border_style="bold red"))
        else: # error or inactive
            console.print(Panel(t('firewall_ufw_not_active'), border_style="bold red"))
        questionary.press_any_key_to_continue().ask()
        return

    # UFW is active, proceed with management
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('firewall_title')}[/bold blue]"))
        
        try:
            status_output = subprocess.check_output(['ufw', 'status', 'verbose'], text=True)
            console.print(Panel(status_output, title=t('firewall_current_status')))
        except Exception as e:
            console.print(f"[red]{t('firewall_status_error', error=e)}[/red]")
            questionary.press_any_key_to_continue().ask()
            break

        choice = questionary.select(
            t('firewall_action_prompt'),
            choices=[
                t('firewall_menu_enable'),
                t('firewall_menu_disable'),
                t('firewall_menu_add'),
                t('firewall_menu_delete'),
                t('services_menu_back')
            ]
        ).ask()

        if choice == t('services_menu_back') or choice is None:
            break
        elif choice == t('firewall_menu_enable'):
            os.system('sudo ufw enable')
        elif choice == t('firewall_menu_disable'):
            os.system('sudo ufw disable')
        elif choice == t('firewall_menu_add'):
            rule = questionary.text(t('firewall_add_prompt')).ask()
            if rule:
                os.system(f'sudo ufw {rule}')
        elif choice == t('firewall_menu_delete'):
            rule = questionary.text(t('firewall_delete_prompt')).ask()
            if rule:
                os.system(f'sudo ufw delete {rule}') 