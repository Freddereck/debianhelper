import os
import subprocess
from rich.console import Console

console = Console()

def clear_console():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def is_root():
    """Check if the script is run as root."""
    return os.geteuid() == 0

def run_command(cmd, spinner_message=None, cwd=None):
    """Runs a command (can be string for shell or list for exec) and shows a spinner."""
    try:
        if isinstance(cmd, str):
            shell = True
        else:
            shell = False
        if spinner_message:
            with console.status(spinner_message):
                console.print(f"[yellow]Выполняется команда:[/yellow] {cmd}")
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, shell=shell)
        else:
            res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, shell=shell)
        return res
    except Exception as e:
        return None
        
    return result_obj 