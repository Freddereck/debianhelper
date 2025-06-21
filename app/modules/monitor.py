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
from rich.group import Group
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

    for p in processes[:10]: # Limit to top 10
        table.add_row(
            str(p['pid']),
            p['name'],
            f"{p['cpu_percent']:.1f}%",
            f"{p['memory_percent']:.1f}%"
        )
    return table

def get_layout() -> Layout:
    """Defines the layout for the htop-like monitor."""
    layout = Layout(name="root")
    
    procs = [p.info for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])]
    
    # Sort by CPU and Memory
    top_cpu = sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)
    top_mem = sorted(procs, key=lambda p: p['memory_percent'], reverse=True)

    # Get usage stats
    cpu_usage = psutil.cpu_percent(percpu=True)
    ram_usage = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')

    # Create tables
    process_table_cpu = get_process_table(top_cpu, t('monitor_top_cpu'), "green")
    process_table_mem = get_process_table(top_mem, t('monitor_top_mem'), "magenta")
    
    # Create disk usage bars
    disk_usage_bars = Group(
        Text(f"{t('monitor_disk_total')}: {disk_usage.total / (1024**3):.2f} GB"),
        Text(f"{t('monitor_disk_used')}: {disk_usage.used / (1024**3):.2f} GB ({disk_usage.percent}%)"),
        get_cpu_bar(disk_usage.percent)
    )

    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=7, name="footer"),
    )

    layout["main"].split_row(Layout(process_table_cpu, name="side"), Layout(process_table_mem, name="body"))
    
    layout["header"].update(Header())
    layout["footer"].update(Panel(
        Align.center(disk_usage_bars, vertical="middle"),
        title=t('monitor_disk_title'),
        border_style="cyan"
    ))
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