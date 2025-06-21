import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.utils import run_command, run_command_live

console = Console()

def check_common_utilities():
    """Checks for the presence and version of common command-line tools."""
    console.print(Panel("[bold green]Checking for Common Utilities[/bold green]"))
    utilities = ["python3", "git", "node", "docker"]
    table = Table(title="Utility Status")
    table.add_column("Utility", style="cyan")
    table.add_column("Version / Status", style="magenta")

    for util in utilities:
        version = run_command(f"{util} --version")
        if version:
            table.add_row(util, version)
        else:
            table.add_row(util, "[red]Not Found[/red]")
    
    console.print(table)
    questionary.press_any_key_to_continue().ask()


def show_package_manager():
    """Provides a simple interface for APT package management."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold blue]Package Manager (APT)[/bold blue]"))

    # This check is for Windows compatibility, not for apt specifically
    if os.name == 'nt':
        console.print("[red]APT package manager is not available on Windows.[/red]")
        questionary.press_any_key_to_continue().ask()
        return

    action = questionary.select("Select an action:",
                                 choices=["Update package lists (update)",
                                          "Upgrade all packages (upgrade)",
                                          "Install a package",
                                          "Remove a package",
                                          "Check for common utilities",
                                          "Back"]).ask()

    if action is None or action == "Back":
        return

    if "update" in action:
        run_command_live("sudo apt-get update", "apt_update.log")
    elif "upgrade" in action:
        run_command_live("sudo apt-get upgrade -y", "apt_upgrade.log")
    elif "Install" in action:
        package = questionary.text("Enter name of package to install:").ask()
        if package:
            run_command_live(f"sudo apt-get install -y {package}", f"apt_install_{package}.log")
    elif "Remove" in action:
        package = questionary.text("Enter name of package to remove:").ask()
        if package:
            if questionary.confirm(f"Also remove dependencies and config files for {package}? (purge)").ask():
                run_command_live(f"sudo apt-get purge -y {package}", f"apt_purge_{package}.log")
            else:
                run_command_live(f"sudo apt-get remove -y {package}", f"apt_remove_{package}.log")
    elif "Check" in action:
        check_common_utilities()
        # We call the main function again to show the menu after the check
        show_package_manager()
        return # Important to exit after the recursive call

    questionary.press_any_key_to_continue().ask()
    # Rerun the manager to show menu again after an action
    show_package_manager() 