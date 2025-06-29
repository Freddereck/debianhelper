import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from localization import get_string

console = Console()

def get_os_info():
    """Gathers hostname and OS version."""
    try:
        hostname = subprocess.run(['hostname'], capture_output=True, text=True, check=True).stdout.strip()
        os_release_raw = subprocess.run(['cat', '/etc/os-release'], capture_output=True, text=True, check=True).stdout
        pretty_name_line = [line for line in os_release_raw.split('\n') if 'PRETTY_NAME' in line]
        pretty_name = pretty_name_line[0].split('=')[1].strip('"') if pretty_name_line else "N/A"
        return hostname, pretty_name
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A", "N/A"

def get_uptime():
    """Gets system uptime."""
    try:
        return subprocess.run(['uptime', '-p'], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"
        
def get_mem_usage():
    """Gets memory usage statistics."""
    try:
        result = subprocess.run(['free', '-h'], capture_output=True, text=True, check=True).stdout.strip().split('\n')
        mem_line = result[1].split()
        return mem_line[1], mem_line[2], mem_line[3] # Total, Used, Free
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A", "N/A", "N/A"

def get_load_avg():
    """Gets system load average."""
    try:
        load_avg_raw = subprocess.run(['cat', '/proc/loadavg'], capture_output=True, text=True, check=True).stdout
        return " ".join(load_avg_raw.split()[:3])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"


def run_system_info():
    """Displays a summary of system information."""
    console.print(get_string("system_info_title"))

    hostname, os_version = get_os_info()
    uptime = get_uptime()
    mem_total, mem_used, mem_free = get_mem_usage()
    load_avg = get_load_avg()
    
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="bold magenta")
    info_table.add_column()

    info_table.add_row(f"{get_string('hostname')}:", hostname)
    info_table.add_row(f"{get_string('os_version')}:", os_version)
    info_table.add_row(f"{get_string('uptime')}:", uptime)
    info_table.add_row(f"{get_string('load_avg')}:", load_avg)

    console.print(info_table)

    mem_table = Table(title=get_string('memory_usage'))
    mem_table.add_column(get_string('total_mem'), justify="center")
    mem_table.add_column(get_string('used_mem'), justify="center")
    mem_table.add_column(get_string('free_mem'), justify="center")
    mem_table.add_row(mem_total, mem_used, mem_free, style="green")

    console.print(mem_table) 