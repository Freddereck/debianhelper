import time
import psutil
import os
from datetime import timedelta
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress_bar import ProgressBar
from rich.align import Align
from rich.text import Text
from app.utils import get_uptime
from app.translations import t

console = Console()

class Header:
    """Displays header with clock and system info."""
    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            f"[b]{t('monitor_title')}[/b]",
            f"{get_uptime()} | {time.ctime()}",
        )
        return Panel(grid, style="bold white on blue")

def get_cpu_bar(usage):
    """Returns a progress bar for CPU usage."""
    if usage < 40:
        color = "green"
    elif usage < 70:
        color = "yellow"
    else:
        color = "red"
    return ProgressBar(total=100, completed=usage, width=50, style=color, complete_style=color)

def get_process_table(processes, title, border_style):
    """Creates a table of processes."""
    table = Table(title=title, border_style=border_style)
    table.add_column(t('monitor_col_pid'), justify="right")
    table.add_column(t('monitor_col_name'))
    table.add_column(t('monitor_col_cpu'), justify="right")
    table.add_column(t('monitor_col_mem'), justify="right")

    for p in processes[:100]: # Limit to top 100 for performance
        table.add_row(
            str(p['pid']),
            p['name'],
            f"{p['cpu_percent']:.1f}%",
            f"{p['memory_percent']:.1f}%"
        )
    return table

def get_meters_panel():
    """Creates a panel with CPU, RAM, and Disk usage meters."""
    # Get usage stats
    cpu_usage = psutil.cpu_percent(percpu=True)
    ram_usage = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')

    # Grids for meters
    cpu_grid = Table.grid(padding=(0, 1))
    cpu_grid.add_column()
    cpu_grid.add_column(width=50)
    for i, usage in enumerate(cpu_usage):
        cpu_grid.add_row(f"CPU {i+1}:", get_cpu_bar(usage))

    ram_bar = get_cpu_bar(ram_usage.percent)
    disk_bar = get_cpu_bar(disk_usage.percent)
    
    ram_text = f"RAM: {ram_usage.used / (1024**3):.1f}/{ram_usage.total / (1024**3):.1f} GB"
    disk_text = f"Disk: {disk_usage.used / (1024**3):.1f}/{disk_usage.total / (1024**3):.1f} GB"

    meters_grid = Table.grid(expand=True)
    meters_grid.add_column(ratio=1)
    meters_grid.add_column(ratio=2)
    meters_grid.add_row(Panel(cpu_grid, title=t('monitor_cpu_title'), border_style="red"), 
                        Panel(Table.grid(expand=True).add_row(ram_text, ram_bar).add_row(disk_text, disk_bar), 
                              title=t('monitor_mem_disk_title'), border_style="yellow"))

    return meters_grid

def get_layout() -> Layout:
    """Defines the layout for the htop-like monitor."""
    layout = Layout(name="root")
    
    procs = [p.info for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])]
    procs = sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)

    process_table = get_process_table(procs, t('monitor_process_list'), "green")

    layout.split(
        Layout(Header(), name="header", size=3),
        Layout(get_meters_panel(), name="meters", size=max(5, len(psutil.cpu_percent(percpu=True)) + 2)),
        Layout(process_table, name="processes")
    )
    return layout

def show_htop_monitor():
    """Displays a more advanced, htop-like system monitor."""
    os.system('cls' if os.name == 'nt' else 'clear')

    with Live(get_layout(), screen=True, redirect_stderr=False, vertical_overflow="visible") as live:
        try:
            while True:
                time.sleep(1)
                live.update(get_layout())
        except KeyboardInterrupt:
            pass 