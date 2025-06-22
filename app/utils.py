import os
import re
import subprocess
import time
from datetime import timedelta
import shutil

import psutil
from rich.console import Console

console = Console()

def run_command(command, show_output=False, ignore_errors=False):
    """
    Runs a command and captures its output.
    Returns the command's stdout as a string.
    """
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=not ignore_errors,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if show_output:
            if process.stdout:
                console.print(process.stdout)
            if process.stderr:
                console.print(f"[yellow]{process.stderr}[/yellow]")
        
        return process.stdout

    except subprocess.CalledProcessError as e:
        if show_output:
            if e.stdout:
                console.print(e.stdout)
            if e.stderr:
                console.print(f"[red]{e.stderr}[/red]")
        return e.stdout if e.stdout else ""
    except FileNotFoundError:
        console.print(f"[bold red]Error: Command not found: {command.split()[0]}[/bold red]")
        return ""

def run_command_live(command, log_filename):
    """Executes a command with live output and saves it to a log file."""
    full_output = []
    with console.status("[bold green]Running command...", spinner="dots"):
        try:
            with open(log_filename, "w", encoding="utf-8") as log_file:
                log_file.write(f"Executing command: {command}\n" + "="*50 + "\n")
                process = subprocess.Popen(
                    command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace'
                )
                for line in iter(process.stdout.readline, ''):
                    console.print(f"[dim]  {line.strip()}[/dim]")
                    log_file.write(line)
                    full_output.append(line)
                process.wait()
                if process.returncode != 0:
                    console.print(f"\n[bold red]Command finished with error (code {process.returncode}).[/bold red]")
                    return None
            return "".join(full_output)
        except Exception as e:
            console.print(f"\n[bold red]Failed to execute command: {e}[/bold red]")
            return None

def is_tool_installed(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None

def get_uptime():
    """Returns the system uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_string = f.readline().split()[0]
        uptime_seconds = float(uptime_string)
        return str(timedelta(seconds=uptime_seconds))
    except (IOError, ValueError):
        return "N/A"

def run_command_for_output(command):
    """A reusable utility to run a command and capture its output."""
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', timeout=15
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""

def get_top_processes(sort_by='cpu_percent'):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'cmdline']):
        try:
            p.info['memory_mb'] = p.info['memory_info'].rss / (1024 * 1024)
            p.info['command'] = ' '.join(p.info['cmdline']) if p.info['cmdline'] else p.info['name']
            if not p.info['command']: p.info['command'] = p.info['name']
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return sorted(procs, key=lambda x: x.get(sort_by, 0), reverse=True)

def get_system_info():
    """Gathers static system information like CPU model and cores."""
    info = {}
    if os.name == 'nt': # Windows compatibility
        info['cpu_model'] = "N/A on Windows"
        info['threads'] = psutil.cpu_count(logical=True)
        info['cores'] = psutil.cpu_count(logical=False)
        return info
    try:
        cpu_info_raw = run_command("lscpu")
        if cpu_info_raw:
            model_search = re.search(r"Model name:\s+(.*)", cpu_info_raw)
            info['cpu_model'] = model_search.group(1).strip() if model_search else "N/A"
        else:
            info['cpu_model'] = "N/A"
        info['threads'] = psutil.cpu_count(logical=True)
        info['cores'] = psutil.cpu_count(logical=False)
    except Exception:
        info['cpu_model'] = "N/A"
        info['threads'] = "N/A"
        info['cores'] = "N/A"
    return info 

def format_bytes(size):
    """Formats bytes into a human-readable string (KiB, MiB, GiB)."""
    if size is None:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KiB', 2: 'MiB', 3: 'GiB', 4: 'TiB'}
    while size >= power and n < len(power_labels):
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}" 