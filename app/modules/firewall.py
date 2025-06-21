import os
import re
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.utils import run_command, run_command_live

console = Console()

COMMON_PORTS = {
    "21": "FTP", "22": "SSH", "25": "SMTP", "53": "DNS",
    "80": "HTTP", "110": "POP3", "143": "IMAP", "443": "HTTPS",
    "465": "SMTPS", "993": "IMAPS", "995": "POP3S", "3306": "MySQL",
    "5432": "PostgreSQL", "8080": "HTTP Alt"
}

def get_rule_explanation(target, details):
    """Generates a human-friendly explanation for a rule."""
    explanation = []
    action = "Allows" if target == "ACCEPT" else "Blocks"
    
    port_match = re.search(r'dpt:(\d+)', details)
    if port_match:
        port = port_match.group(1)
        service = COMMON_PORTS.get(port, f"port {port}")
        explanation.append(f"{action} incoming {service}")

    state_match = re.search(r'state (\w+)', details)
    if state_match:
        state = state_match.group(1)
        if state == "RELATED,ESTABLISHED":
            explanation.append("Allows established connections")

    if not explanation:
        return "Custom rule"
    return " / ".join(explanation)

def manage_iptables():
    """Provides an interactive, safer interface for managing iptables."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel("[bold red]IPTables Interactive Manager[/bold red]", subtitle="[yellow]Chain: FILTER[/yellow]"))
        
        rules_raw = run_command("sudo iptables -L -n -v --line-numbers")
        if rules_raw:
            table = Table(title="IPTables Filter Rules", show_lines=True)
            headers = ["num", "target", "prot", "source", "destination", "details", "explanation"]
            for header in headers:
                table.add_column(header.upper())

            current_chain = ""
            for line in rules_raw.splitlines():
                if line.startswith("Chain"):
                    current_chain = line.split(" ")[1]
                    table.add_section()
                    table.add_row(f"[bold cyan]Chain {current_chain}[/bold cyan]")
                    continue
                
                parts = line.split()
                if len(parts) < 9 or not parts[0].isdigit():
                    continue

                # Normalizing parts for consistent table layout
                num, pkts, bytes, target, prot, opt, in_if, out_if, source, destination = parts[:10]
                details = " ".join(parts[10:])
                explanation = get_rule_explanation(target, details)
                table.add_row(num, target, prot, source, destination, details, f"[dim]{explanation}[/dim]")
            console.print(table)
        else:
            console.print("[red]Could not fetch iptables rules.[/red]")

        action = questionary.select("IPTables Action:",
                                     choices=["Add Rule", "Delete Rule by Number", "Back"]).ask()

        if action == "Back" or action is None:
            break
        elif action == "Add Rule":
            chain = questionary.select("Chain:", choices=["INPUT", "OUTPUT", "FORWARD"]).ask()
            interface = questionary.text("Interface (e.g., eth0, or leave blank for all):").ask()
            proto = questionary.select("Protocol:", choices=["tcp", "udp", "icmp", "all"]).ask()
            port = questionary.text("Port (e.g., 22, 80, or leave blank):").ask()
            ip = questionary.text("Source IP (or leave blank for all):").ask()
            target = questionary.select("Target:", choices=["ACCEPT", "DROP", "REJECT"]).ask()
            
            cmd_parts = ["sudo iptables -A", chain]
            if interface: cmd_parts.extend(["-i", interface])
            if proto != 'all': cmd_parts.extend(["-p", proto])
            if port: cmd_parts.extend(["--dport", port])
            if ip: cmd_parts.extend(["-s", ip])
            cmd_parts.extend(["-j", target])
            
            cmd = " ".join(cmd_parts)
            if questionary.confirm(f"Execute: [cyan]{cmd}[/cyan]?").ask():
                run_command(cmd)
        
        elif action == "Delete Rule by Number":
            chain = questionary.select("From which chain to delete?", choices=["INPUT", "OUTPUT", "FORWARD"]).ask()
            rule_num = questionary.text(f"Rule number in chain {chain} to delete:", validate=lambda t: t.isdigit()).ask()
            if rule_num:
                cmd = f"sudo iptables -D {chain} {rule_num}"
                if questionary.confirm(f"Execute: [cyan]{cmd}[/cyan]?").ask():
                    run_command(cmd)

def manage_ufw():
    """Provides an interactive loop to manage UFW firewall."""
    # This function is mostly unchanged
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        status_output = run_command("sudo ufw status verbose")
        if status_output is None:
            console.print("[red]Could not get UFW status. Is UFW installed?[/red]")
            time.sleep(2); return
            
        console.print(Panel(status_output, title="UFW Status", border_style="yellow"))
        rules_output = run_command("sudo ufw status numbered")
        if rules_output:
            console.print(Panel(rules_output, title="UFW Rules", border_style="cyan"))
        
        action = questionary.select("UFW Action:",
                                     choices=["Add Rule", "Delete Rule", "Enable", "Disable", "Back"]).ask()
        if action == "Back" or action is None: break
        # ... (rest of the UFW logic)

def show_firewall_manager():
    """Allows user to choose which firewall to manage."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold cyan]Firewall Manager[/bold cyan]"))
    
    choices = []
    if os.name != 'nt':
        if run_command("which ufw"): choices.append("UFW (Recommended)")
        if run_command("which iptables"): choices.append("iptables (Advanced)")
    if not choices:
        console.print("[red]No supported firewall found on this system.[/red]")
        time.sleep(2); return

    fw_choice = questionary.select("Which firewall to manage?", choices=choices + ["Back"]).ask()
    if fw_choice == "UFW (Recommended)":
        manage_ufw()
    elif fw_choice == "iptables (Advanced)":
        manage_iptables() 