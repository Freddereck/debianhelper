import os
import re
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.utils import run_command, run_command_live

console = Console()

def run_security_audit():
    """Performs a multi-faceted security audit."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold red]Server Security & Network Audit[/bold red]"))
    
    if os.name != 'nt' and os.geteuid() != 0:
        console.print("[bold red]Security audit must be run as root/sudo.[/bold red]")
        questionary.press_any_key_to_continue().ask()
        return

    # 1. Fail2Ban Status
    console.print("\n[yellow]1. Checking Fail2Ban Status...[/yellow]")
    if run_command("which fail2ban-client"):
        f2b_status_raw = run_command("sudo fail2ban-client status")
        if f2b_status_raw:
            jails = re.findall(r'Jail list:\s*(.*)', f2b_status_raw)
            if jails:
                jail_list = [j.strip() for j in jails[0].split(',')]
                f2b_table = Table(title="Fail2Ban Jail Status"); f2b_table.add_column("Jail Name", style="cyan"); f2b_table.add_column("Banned IPs", style="red")
                for jail in jail_list:
                    jail_status = run_command(f"sudo fail2ban-client status {jail}")
                    banned_count = "0"
                    if jail_status:
                        count = re.search(r'Currently banned:\s*(\d+)', jail_status)
                        if count: banned_count = count.group(1)
                    f2b_table.add_row(jail, banned_count)
                console.print(f2b_table)
    else: console.print("[dim]Fail2Ban client not found. Skipping.[/dim]")

    # 2. Listening ports
    console.print("\n[yellow]2. Analyzing Listening Network Ports...[/yellow]")
    netstat_output = run_command("sudo ss -ltupn")
    if netstat_output:
        port_table = Table(title="Listening Network Ports"); port_table.add_column("Protocol", style="yellow"); port_table.add_column("Local Address:Port", style="cyan"); port_table.add_column("Process", style="green")
        for line in netstat_output.strip().split('\n')[1:]:
            parts = line.split(); proto = parts[0]; local_addr = parts[4]
            proc_match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
            proc_name = f"{proc_match.group(1)} (PID:{proc_match.group(2)})" if proc_match else "N/A"
            port_table.add_row(proto, local_addr, proc_name)
        console.print(port_table)
    else: console.print("[dim]'ss' command failed. Skipping.[/dim]")

    # 3. SSH Configuration
    console.print("\n[yellow]3. Checking SSH Configuration...[/yellow]")
    sshd_config_path = "/etc/ssh/sshd_config"
    sshd_config = run_command(f"sudo cat {sshd_config_path}")
    if sshd_config:
        ssh_table = Table(title="SSH Hardening Checks", show_header=False, box=None)
        ssh_table.add_column("Check")
        ssh_table.add_column("Status", justify="right")
        
        root_login_match = re.search(r"^\s*PermitRootLogin\s+(yes|prohibit-password)", sshd_config, re.MULTILINE)
        if root_login_match and root_login_match.group(1) == "yes":
            ssh_table.add_row("Permit Root Login", "[bold red]ENABLED[/bold red]")
        else:
            ssh_table.add_row("Permit Root Login", "[green]Disabled[/green]")

        pass_auth_match = re.search(r"^\s*PasswordAuthentication\s+yes", sshd_config, re.MULTILINE)
        if pass_auth_match:
            ssh_table.add_row("Password Authentication", "[bold red]ENABLED[/bold red]")
        else:
            ssh_table.add_row("Password Authentication", "[green]Disabled[/green]")
        console.print(ssh_table)
        
        if (root_login_match and root_login_match.group(1) == "yes") or pass_auth_match:
            console.print(
                "\n[yellow]This script can open the SSH config file for you in 'nano'.\n"
                "You should change the highlighted settings to improve security.\n"
                "For example: 'PermitRootLogin no' and 'PasswordAuthentication no'.[/yellow]"
            )
            if questionary.confirm("Open sshd_config in nano to fix these issues?").ask():
                run_command(f"sudo nano {sshd_config_path}", use_shell=True)
    else:
        console.print(f"[dim]Could not read {sshd_config_path}. Skipping.[/dim]")

    # 4. Users with empty passwords
    console.print("\n[yellow]4. Checking for Users with Empty Passwords...[/yellow]")
    empty_pass_users = run_command("sudo awk -F: '($2 == \"\") {print $1}' /etc/shadow")
    if empty_pass_users:
        console.print("[bold red]Found users with empty passwords:[/bold red]")
        for user in empty_pass_users.split('\n'):
            console.print(f"  - {user}")
    else:
        console.print("[green]No users with empty passwords found.[/green]")

    # 5. Lynis
    console.print("\n[yellow]5. Running Lynis Security Audit...[/yellow]")
    console.print(
        "[dim]Lynis is a comprehensive security auditing tool. It performs hundreds of tests\n"
        "to check for vulnerabilities and system hardening opportunities.\n"
        "The scan can take several minutes.[/dim]"
    )
    if not run_command("which lynis"):
        if questionary.confirm("'lynis' is not installed. Install now?").ask():
            run_command_live("sudo apt-get update -qq && sudo apt-get install -y lynis", "lynis_install_log.log")
    if run_command("which lynis"):
        console.print("\n[cyan]Starting Lynis audit...[/cyan]")
        lynis_report = run_command_live("sudo lynis audit system --quiet", "lynis_audit_log.log")
        console.print("[green]Lynis audit complete.[/green]\n")
        if lynis_report:
            warnings = re.findall(r'Warning: (.*) \[test:([A-Z0-9-]+)\]', lynis_report)
            suggestions = re.findall(r'Suggestion: (.*) \[test:([A-Z0-9-]+)\]', lynis_report)
            if warnings:
                warn_table = Table(title="[bold yellow]Lynis Warnings[/bold yellow]"); warn_table.add_column("Warning", style="yellow"); warn_table.add_column("Test ID", style="cyan")
                for warn, test_id in warnings: warn_table.add_row(warn.strip(), test_id.strip())
                console.print(warn_table)
            else: console.print("[green]Lynis found no high-priority warnings.[/green]")
            if suggestions:
                sugg_table = Table(title="\n[bold blue]Lynis Suggestions[/bold blue]"); sugg_table.add_column("Suggestion", style="blue"); sugg_table.add_column("Test ID", style="cyan")
                for sugg, test_id in suggestions: sugg_table.add_row(sugg.strip(), test_id.strip())
                console.print(sugg_table)
            else: console.print("[green]Lynis found no specific suggestions.[/green]")
    console.print("\n[dim]For full details, run 'lynis audit system' manually.[/dim]")
    questionary.press_any_key_to_continue().ask() 