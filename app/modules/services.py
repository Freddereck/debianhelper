import os
import subprocess
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
import shutil

from app.utils import run_command, run_command_live

console = Console()

SERVICES = {
    "Nginx": {"package": "nginx", "config": "/etc/nginx/nginx.conf", "service": "nginx"},
    "Apache2": {"package": "apache2", "config": "/etc/apache2/apache2.conf", "service": "apache2"},
    "MySQL": {"package": "mysql-server", "config": "/etc/mysql/my.cnf", "service": "mysql"},
    "MariaDB": {"package": "mariadb-server", "config": "/etc/mysql/mariadb.conf.d/50-server.cnf", "service": "mariadb"},
    "PostgreSQL": {"package": "postgresql", "config": "/etc/postgresql/", "service": "postgresql"},
    "Docker": {"package": "docker.io", "config": "/etc/docker/daemon.json", "service": "docker"},
    "WireGuard": {"package": "wireguard-tools", "config": "/etc/wireguard/", "service": "wg-quick@"},
    "Fail2Ban": {"package": "fail2ban", "config": "/etc/fail2ban/jail.local", "service": "fail2ban"},
    "Redis": {"package": "redis-server", "config": "/etc/redis/redis.conf", "service": "redis-server"},
    "Memcached": {"package": "memcached", "config": "/etc/memcached.conf", "service": "memcached"},
    'ssh': {'service_name': 'ssh', 'description': 'Secure Shell server for remote access.'},
    'nginx': {'service_name': 'nginx', 'description': 'High-performance web server.'},
    'postgresql': {'service_name': 'postgresql', 'description': 'PostgreSQL database server.'},
    'mysql': {'service_name': 'mysql', 'description': 'MySQL/MariaDB database server.'},
    'redis': {'service_name': 'redis-server', 'description': 'In-memory data structure store.'},
    'fail2ban': {'service_name': 'fail2ban', 'description': 'Intrusion prevention software.'},
    'ufw': {'service_name': 'ufw', 'description': 'Uncomplicated Firewall.'},
    'cron': {'service_name': 'cron', 'description': 'Job scheduler.'},
    'docker': {'service_name': 'docker', 'description': 'Containerization platform.'}
}

def show_service_manager():
    """A manager for common system services."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold green]System Service Manager[/bold green]"))

    choices = list(SERVICES.keys()) + ["X-UI (custom)", "Back"]
    service_name = questionary.select("Which service to manage?", choices=choices).ask()
    
    if service_name == "Back" or service_name is None:
        return

    if service_name == "X-UI (custom)":
        svc = {"package": None, "config": "/etc/x-ui/config.json", "service": "x-ui"}
    else:
        svc = SERVICES[service_name]
    
    package = svc.get('package')
    service = svc.get('service')

    # Handle wildcard services like WireGuard
    if service.endswith('@'):
        base_service = service
        try:
            configs = [f for f in os.listdir(svc['config']) if f.endswith('.conf')]
            if not configs:
                console.print(f"[yellow]No config files found for {service_name} in {svc['config']}[/yellow]"); time.sleep(2); return
            
            conf_to_manage = questionary.select(f"Which {service_name} interface?", choices=[c.replace('.conf', '') for c in configs]).ask()
            if not conf_to_manage: return
            service = f"{base_service}{conf_to_manage}"
        except FileNotFoundError:
            console.print(f"[red]Config directory not found: {svc['config']}[/red]"); time.sleep(2); return

    # More reliable check for installation status
    if package:
        status_output = run_command(f"dpkg-query -W -f='${{Status}}' {package}")
        is_installed = status_output and "install ok installed" in status_output
    else: # Fallback for custom services like X-UI
        is_installed = bool(run_command(f"which {service}"))


    if not is_installed:
        if package and questionary.confirm(f"{service_name} not installed. Install now?").ask():
            run_command_live(f"sudo apt-get update -qq && sudo apt-get install -y {package}", f"{package}_install.log")
        elif service_name == "X-UI (custom)":
            console.print("[cyan]To install X-UI, please run their official script.[/cyan]"); time.sleep(3)
        return

    while True:
        status_raw = run_command(f"systemctl status {service}")
        status = "[bold red]Unknown[/bold red]"
        if status_raw:
            if "active (running)" in status_raw: status = "[green]Active[/green]"
            elif "inactive (dead)" in status_raw: status = "[red]Inactive[/red]"
            elif "active (exited)" in status_raw: status = "[yellow]Active (Exited)[/yellow]"
            elif "not-found" in status_raw: status = "[bold red]Not Found[/bold red]"

        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"Managing: [bold cyan]{service_name} ({service})[/bold cyan] | Status: {status}"))
        
        action = questionary.select("Action:", choices=["Start", "Stop", "Restart", "Enable on Boot", "Disable on Boot", "Edit Config", "Back"]).ask()

        if action == "Back" or action is None: break

        cmd_map = {"Start": "start", "Stop": "stop", "Restart": "restart",
                   "Enable on Boot": "enable", "Disable on Boot": "disable"}
        
        if action in cmd_map:
            run_command_live(f"sudo systemctl {cmd_map[action]} {service}", f"{service}_cmd.log")
        elif action == "Edit Config":
            config_path = svc.get('config')
            
            # Handle case where default config doesn't exist (e.g., jail.local, custom paths)
            if not os.path.exists(config_path):
                alt_config_path = config_path.replace('.local', '.conf') if '.local' in config_path else None
                if alt_config_path and os.path.exists(alt_config_path):
                    config_path = alt_config_path
                else:
                    console.print(f"[yellow]Default config not found at '{config_path}'[/yellow]")
                    new_path = questionary.path("Please enter the correct path to the config file (or press Enter to cancel):").ask()
                    if new_path and os.path.exists(new_path):
                        config_path = new_path
                    else:
                        console.print("[red]Invalid path or cancelled.[/red]"); time.sleep(1); continue

            if os.path.isdir(config_path):
                try:
                    files = [os.path.join(config_path, f) for f in os.listdir(config_path)]
                    config_path = questionary.select("Which config file to edit?", choices=files).ask()
                except (FileNotFoundError, PermissionError):
                    console.print(f"[red]Cannot access {config_path}[/red]"); time.sleep(2); continue
            
            if config_path and os.path.exists(config_path) and not os.path.isdir(config_path):
                subprocess.run(f"sudo nano {config_path}", shell=True)
            elif not (config_path and os.path.exists(config_path)):
                console.print(f"[red]Config not found or is a directory: {config_path}[/red]"); time.sleep(2) 

def is_service_installed(service_key):
    """Check if a service's command exists."""
    # For docker, check for the command. For others, assume systemd service name.
    if service_key == 'docker':
        return shutil.which('docker') is not None
    
    # A simple check for other services - might need refinement.
    # This is tricky because service file names can vary.
    # We will assume for now the key matches the command or a common name.
    return shutil.which(service_key) is not None or service_exists(SERVICES[service_key]['service_name'])

def service_exists(service_name):
    """Check if a systemd service file exists."""
    pass # Placeholder for existing code 