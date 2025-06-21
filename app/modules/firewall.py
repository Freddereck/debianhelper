import os
import questionary
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from app.translations import t

console = Console()

def run_command_for_output(command):
    """A local utility to run a command and capture its output, for simplicity."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def is_ufw_active():
    """Checks if UFW is active."""
    status_output = run_command_for_output("sudo ufw status")
    return status_output and "Status: active" in status_output

def show_firewall_status():
    """Displays the firewall status (UFW or iptables)."""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    if is_ufw_active():
        console.print(Panel(t('firewall_ufw_active_panel'), border_style="green", expand=False))
        # UFW's output is already quite readable
        ufw_output = run_command_for_output("sudo ufw status verbose")
        console.print(ufw_output or t('firewall_ufw_error'))
    else:
        console.print(Panel(t('firewall_iptables_active_panel'), border_style="yellow", expand=False))
        iptables_output = run_command_for_output("sudo iptables -L -v -n")
        
        if iptables_output:
            syntax = Syntax(iptables_output, "bash", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            console.print(t('firewall_iptables_error'))

    questionary.press_any_key_to_continue().ask()

def show_firewall_manager():
    """Main menu for the firewall manager."""
    # For now, this just shows the status. Can be expanded later.
    show_firewall_status() 