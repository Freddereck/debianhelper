import os
import shutil
import subprocess
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import psutil

console = Console()

def show_connections():
    """Displays active network connections using psutil."""
    console.clear()
    console.print(Panel("Active Network Connections", style="cyan", title_align="left"))
    
    try:
        connections = psutil.net_connections()
        table = Table(expand=True)
        table.add_column("Proto", style="cyan")
        table.add_column("Local Address", style="magenta")
        table.add_column("Remote Address", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("PID", style="blue")
        table.add_column("Process Name", style="white")

        for conn in connections:
            # We are interested in established or listening connections mainly
            if conn.status in ('ESTABLISHED', 'LISTEN', 'CLOSE_WAIT'):
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                
                proc_name = ""
                if conn.pid:
                    try:
                        proc_name = psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = "N/A"

                table.add_row(
                    "TCP" if conn.type == 1 else "UDP",
                    laddr,
                    raddr,
                    conn.status,
                    str(conn.pid) if conn.pid else "",
                    proc_name
                )
        console.print(table)
    except psutil.AccessDenied:
        console.print("[bold red]Access Denied. Run with sudo to see all process information.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")

    questionary.press_any_key_to_continue().ask()


def run_network_tool(tool_name, is_windows):
    """Generic handler for running ping or traceroute."""
    host = questionary.text(f"Enter the host to {tool_name}:").ask()
    if not host:
        return

    if tool_name == 'ping':
        command = ['ping', host, '-n', '4'] if is_windows else ['ping', host, '-c', '4']
    elif tool_name == 'traceroute':
        if is_windows:
            command = ['tracert', host]
        else:
            if not shutil.which('traceroute'):
                console.print("[bold yellow]Warning: 'traceroute' is not installed.[/bold yellow]")
                console.print("On Debian/Ubuntu, install it with: [cyan]sudo apt install traceroute[/cyan]")
                questionary.press_any_key_to_continue().ask()
                return
            command = ['traceroute', host]
    else:
        return

    console.clear()
    console.print(Panel(f"Running {tool_name.capitalize()} on [cyan]{host}[/cyan]...", style="green"))
    try:
        # Stream the output directly to the console
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(process.stdout.readline, ''):
            console.print(line, end='')
        process.stdout.close()
        process.wait()
    except FileNotFoundError:
        console.print(f"[bold red]Error: '{command[0]}' not found. Is it installed and in your PATH?[/bold red]")
    except Exception as e:
        console.print(f"[bold red]An error occurred: {e}[/bold red]")

    questionary.press_any_key_to_continue().ask()


def show_network_toolkit():
    """Main menu for the Network Toolkit."""
    is_windows = os.name == 'nt'
    
    while True:
        console.clear()
        console.print(Panel(t('network_toolkit_title'), style="bold blue"))
        
        choice = questionary.select(
            "Select a tool:",
            choices=[
                "View Active Connections",
                "Ping Host",
                "Traceroute Host",
                "Back to Main Menu"
            ],
            pointer="👉"
        ).ask()

        if choice is None or choice == "Back to Main Menu":
            break
        elif choice == "View Active Connections":
            show_connections()
        elif choice == "Ping Host":
            run_network_tool('ping', is_windows)
        elif choice == "Traceroute Host":
            run_network_tool('traceroute', is_windows) 