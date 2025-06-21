import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import re

from app.utils import run_command, run_command_live

console = Console()

def run_system_health_check():
    """Runs a series of checks and maintenance tasks."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold cyan]Server Health Check & Maintenance[/bold cyan]"))
    
    if os.name != 'nt' and os.geteuid() != 0:
        console.print("[bold red]Health check requires sudo privileges.[/bold red]")
        questionary.press_any_key_to_continue().ask()
        return

    # 1. Check for updates
    console.print("\n[yellow]1. Checking for system updates...[/yellow]")
    if run_command("sudo apt-get update -qq", timeout=120) is None:
        console.print("[red]Failed to check for updates (command timed out or failed). Skipping.[/red]")
    else:
        upgradable_raw = run_command("apt list --upgradable")
        if upgradable_raw:
            upgradable_lines = upgradable_raw.strip().split('\n')
            num_upgradable = len(upgradable_lines) - 1
            if num_upgradable > 0:
                console.print(f"[bold yellow]Found {num_upgradable} packages to upgrade.[/bold yellow]")
                if questionary.confirm("Do you want to see the list of packages?").ask():
                    package_table = Table(title="Upgradable Packages")
                    package_table.add_column("Package", style="cyan"); package_table.add_column("New Version", style="magenta"); package_table.add_column("Current Version", style="green")
                    for line in upgradable_lines[1:]:
                        parts = line.split(); pkg_name = parts[0].split('/')[0]; new_version = parts[1]; current_version = parts[3] if len(parts) > 3 else "N/A"
                        package_table.add_row(pkg_name, new_version, current_version)
                    console.print(package_table)
                if questionary.confirm("Do you want to upgrade them now?").ask():
                    run_command_live("sudo apt-get upgrade -y", "upgrade_log.log")
            else: console.print("[green]System is up-to-date.[/green]")
        else: console.print("[green]System is up-to-date.[/green]")

    # 2. Clean system
    if questionary.confirm("\nClean unnecessary packages (autoremove & clean)?").ask():
        run_command_live("sudo apt-get autoremove -y && sudo apt-get clean", "cleanup_log.log")

    # 3. Check dmesg for errors
    console.print("\n[yellow]3. Checking for kernel/driver errors (dmesg)...[/yellow]")
    dmesg_errors = run_command("sudo dmesg -l err,crit,alert,emerg")
    if dmesg_errors:
        console.print("[bold red]Found critical errors in dmesg log:[/bold red]")
        console.print(Panel(dmesg_errors, border_style="red", title="dmesg Critical Errors"))

        # Add specific check for I/O errors
        io_errors = re.findall(r'.*I/O error.*', dmesg_errors)
        if io_errors:
            console.print("[bold red]Specifically found disk I/O errors, consider checking disk health (smartctl).[/bold red]")
    else:
        console.print("[green]No critical kernel errors found in dmesg.[/green]")
        
    # 4. Check status of key services
    console.print("\n[yellow]4. Checking status of key services...[/yellow]")
    services_to_check = ["sshd", "cron", "nginx", "docker", "fail2ban", "ufw"]
    table = Table(title="Service Status"); table.add_column("Service", style="cyan"); table.add_column("Status", style="magenta")
    for service in services_to_check:
        status = "[green]● Active[/green]" if run_command(f"systemctl is-active {service}") == "active" else "[red]○ Inactive/Not Found[/red]"
        table.add_row(service, status)
    console.print(table)
    
    console.print("\n[bold green]Health check complete![/bold green]")
    questionary.press_any_key_to_continue().ask() 