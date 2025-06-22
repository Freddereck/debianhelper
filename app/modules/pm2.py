import json
import os
import shutil
import subprocess
import time
from datetime import datetime

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

console = Console()

def is_pm2_installed():
    """Check if PM2 is installed and available in the system's PATH."""
    return shutil.which("pm2") is not None

def get_pm2_processes():
    """Get a list of all processes managed by PM2 in JSON format."""
    try:
        # 'jlist' provides a machine-readable JSON output
        result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]Error fetching PM2 process list: {e}[/bold red]")
        return None

def format_memory(size_bytes):
    """Formats memory size from bytes to a human-readable string."""
    if size_bytes is None or size_bytes == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size_bytes >= power and n < len(power_labels):
        size_bytes /= power
        n += 1
    return f"{size_bytes:.1f} {power_labels[n]}B"

def format_uptime(start_timestamp_ms):
    """Formats uptime from a start timestamp in milliseconds to a human-readable string."""
    if not start_timestamp_ms or start_timestamp_ms == 0:
        return "N/A"
    
    start_time = datetime.fromtimestamp(start_timestamp_ms / 1000)
    uptime = datetime.now() - start_time

    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def show_pm2_logs(process_name):
    """Displays real-time logs for a specific PM2 process."""
    console.clear()
    console.print(Panel(f"Logs for [bold cyan]{process_name}[/]. Press Ctrl+C to return.", border_style="green", title_align="left"))
    try:
        # Using a subprocess to stream logs
        process = subprocess.Popen(
            ['pm2', 'logs', process_name, '--raw', '--lines', '100'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in iter(process.stdout.readline, ''):
            console.print(line.strip())
        process.stdout.close()
        process.wait()

    except KeyboardInterrupt:
        return
    except Exception as e:
        console.print(f"[bold red]Failed to fetch logs: {e}[/bold red]")
        time.sleep(3)


def perform_pm2_action(action, process_name):
    """Executes a given action (start, stop, restart) on a PM2 process."""
    try:
        console.print(f"Executing '{action}' on process [cyan]{process_name}[/cyan]...")
        subprocess.run(['pm2', action, process_name], check=True, capture_output=True)
        console.print(f"[bold green]Action '{action}' for '{process_name}' completed successfully![/bold green]")
        time.sleep(2)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error executing PM2 command: {e.stderr}[/bold red]")
        time.sleep(4)


def show_pm2_manager():
    """Main function for the PM2 Process Manager."""
    if not is_pm2_installed():
        console.print(Panel("[bold yellow]PM2 is not installed or not in the system's PATH.[/bold yellow]\nThis feature requires PM2 to be installed globally.", title="Warning", border_style="yellow"))
        questionary.press_any_key_to_continue("Press any key to return...").ask()
        return

    while True:
        console.clear()
        processes = get_pm2_processes()

        if processes is None: # Error occurred
            questionary.press_any_key_to_continue("Press any key to return...").ask()
            return
        
        table = Table(title="PM2 Managed Processes", border_style="magenta")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("ID", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("CPU", style="green")
        table.add_column("Memory", style="blue")
        table.add_column("Restarts", style="red")
        table.add_column("Uptime", style="green")
        table.add_column("Mode", style="blue")
        table.add_column("User", style="yellow")

        if not processes:
            console.print(Panel("No processes managed by PM2.", title="Info"))
        else:
            for p in processes:
                # Extracting info safely
                info = p.get('pm2_env', {})
                monit = p.get('monit', {})
                status = info.get('status', 'N/A').capitalize()
                color = "green" if status == "Online" else "red" if status == "Stopped" else "yellow"
                
                uptime = format_uptime(info.get('pm_uptime'))
                exec_mode = info.get('exec_mode', 'N/A').replace('_mode', '').capitalize()
                user = info.get('username', 'N/A')

                table.add_row(
                    p.get('name', 'N/A'),
                    str(info.get('pm_id', 'N/A')),
                    f"[{color}]{status}[/{color}]",
                    f"{monit.get('cpu', 0)}%",
                    format_memory(monit.get('memory', 0)),
                    str(info.get('restart_time', 0)),
                    uptime,
                    exec_mode,
                    user
                )
            console.print(table)

        choices = {f"{p.get('name')} (ID: {p.get('pm2_env', {}).get('pm_id')})": p for p in processes}
        
        selected_choice = questionary.select(
            "Select a process to manage:",
            choices=list(choices.keys()) + [questionary.Separator(), "Back to Main Menu"],
            pointer="👉"
        ).ask()

        if selected_choice is None or selected_choice == "Back to Main Menu":
            break
        
        process = choices[selected_choice]
        process_name = process.get('name')
        status = process.get('pm2_env', {}).get('status')

        action_choices = ["restart", "reload", "view logs"]
        if status == "online":
            action_choices.append("stop")
        else:
            action_choices.append("start")
        action_choices.append("Back")
        
        action = questionary.select(
            f"Action for '{process_name}':",
            choices=action_choices,
            pointer="✅"
        ).ask()

        if action == "Back" or action is None:
            continue
        elif action == "view logs":
            show_pm2_logs(process_name)
        else:
            perform_pm2_action(action, process_name)