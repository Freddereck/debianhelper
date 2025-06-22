import os
import shutil
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import subprocess
from app.translations import t
from app.utils import run_command_for_output, run_command

console = Console()

def is_tool_installed(name):
    """Check whether a given tool is installed."""
    return shutil.which(name) is not None

def run_firewall_helper():
    """Interactive helper to create common firewall rules."""
    console.print(Panel(t('firewall_helper_title'), style="bold yellow"))
    
    choice = questionary.select(
        t('firewall_helper_prompt'),
        choices=[
            t('firewall_helper_allow_service'),
            t('firewall_helper_allow_port'),
            t('firewall_helper_deny_ip'),
            t('firewall_helper_allow_ssh_from_ip'),
            t('back_to_main_menu')
        ]
    ).ask()

    rule = None
    if choice == t('firewall_helper_allow_service'):
        service = questionary.text(t('firewall_helper_ask_service')).ask()
        if service: rule = f"allow {service}"
    
    elif choice == t('firewall_helper_allow_port'):
        port = questionary.text(t('firewall_helper_ask_port')).ask()
        protocol = questionary.select(t('firewall_helper_ask_protocol'), choices=['tcp', 'udp', 'any']).ask()
        if port and protocol != 'any':
            rule = f"allow {port}/{protocol}"
        elif port:
            rule = f"allow {port}"

    elif choice == t('firewall_helper_deny_ip'):
        ip_address = questionary.text(t('firewall_helper_ask_ip_deny')).ask()
        if ip_address: rule = f"deny from {ip_address}"

    elif choice == t('firewall_helper_allow_ssh_from_ip'):
        ip_address = questionary.text(t('firewall_helper_ask_ip_allow_ssh')).ask()
        if ip_address: rule = f"allow from {ip_address} to any port 22"

    elif choice == t('back_to_main_menu') or choice is None:
        return

    if rule:
        confirm_message = t('firewall_helper_confirm_rule', rule=f"sudo ufw {rule}")
        if questionary.confirm(confirm_message).ask():
            console.print(t('executing_command'))
            run_command(f"sudo ufw {rule}", show_output=True)
            console.print(f"[green]{t('firewall_rule_applied')}[/green]")
        else:
            console.print(f"[red]{t('operation_cancelled')}[/red]")
    
    questionary.press_any_key_to_continue().ask()

def manage_ufw():
    """Logic for managing UFW."""
    active_check = run_command_for_output('sudo ufw status')
    if "inactive" in active_check:
        console.print(Panel(t('firewall_ufw_not_active'), border_style="bold red"))
        if questionary.confirm(t('firewall_menu_enable_prompt')).ask():
            os.system('sudo ufw enable')
        questionary.press_any_key_to_continue().ask()
        return

    # UFW is active, proceed with management
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('firewall_ufw_title')}[/bold blue]"))
        
        status_output = run_command_for_output('sudo ufw status verbose')
        console.print(Panel(status_output, title=t('firewall_current_status')))

        choice = questionary.select(
            t('firewall_action_prompt'),
            choices=[
                t('firewall_menu_helper'),
                t('firewall_menu_add'),
                t('firewall_menu_delete'),
                t('firewall_menu_disable'),
                t('services_menu_back')
            ]
        ).ask()

        if choice == t('services_menu_back') or choice is None:
            break
        elif choice == t('firewall_menu_disable'):
            os.system('sudo ufw disable')
            console.print(t('firewall_ufw_disabled'))
            questionary.press_any_key_to_continue().ask()
            break
        elif choice == t('firewall_menu_helper'):
            run_firewall_helper()
        elif choice == t('firewall_menu_add'):
            rule = questionary.text(t('firewall_add_prompt')).ask()
            if rule: os.system(f'sudo ufw {rule}')
        elif choice == t('firewall_menu_delete'):
            rule = questionary.text(t('firewall_delete_prompt')).ask()
            if rule: os.system(f'sudo ufw delete {rule}')

def show_iptables_rules():
    """Displays iptables rules in a read-only format."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('firewall_iptables_title'), style="bold yellow"))
    
    iptables_output = run_command_for_output("sudo iptables -L -v -n")
    if iptables_output:
        syntax = Syntax(iptables_output, "bash", theme="monokai", line_numbers=True)
        console.print(syntax)
        console.print(Panel(t('firewall_iptables_readonly'), border_style="dim"))
    else:
        console.print(t('firewall_iptables_error'))
    
    questionary.press_any_key_to_continue().ask()

def show_firewall_manager():
    """Main menu for the firewall manager, allows choosing between UFW and iptables."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold blue]{t('firewall_title')}[/bold blue]"))
    
    ufw_installed = is_tool_installed('ufw')
    iptables_installed = is_tool_installed('iptables')

    choices = []
    if ufw_installed: choices.append("UFW (Recommended)")
    if iptables_installed: choices.append("iptables (View Only)")
    choices.append(t('services_menu_back'))

    if not ufw_installed and not iptables_installed:
        console.print(t('firewall_no_firewall_found'))
        questionary.press_any_key_to_continue().ask()
        return

    console.print(t('firewall_select_prompt'))
    choice = questionary.select(
        t('firewall_select_prompt_long'),
        choices=choices
    ).ask()

    if choice == "UFW (Recommended)":
        manage_ufw()
    elif choice == "iptables (View Only)":
        show_iptables_rules()
    else:
        return 