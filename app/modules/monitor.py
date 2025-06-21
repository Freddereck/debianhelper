import os
import time

import psutil
import questionary
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress_bar import ProgressBar

from app.ui import make_header_layout
from app.utils import get_system_info, get_top_processes, get_uptime, format_bytes

console = Console()

def create_process_table(title, processes, border_style, highlight_pids=None):
    if highlight_pids is None:
        highlight_pids = set()
    table = Table(title=title, expand=True, border_style=border_style)
    table.add_column("PID", style="cyan", width=6)
    table.add_column("%CPU", style="green", justify="right", width=5)
    table.add_column("Mem(MB)", style="magenta", justify="right", width=7)
    table.add_column("Command", style="white", overflow="ellipsis")
    for proc in processes:
        style = "bold yellow" if proc['pid'] not in highlight_pids else "white"
        table.add_row(
            str(proc['pid']), 
            f"{proc['cpu_percent']:.1f}", 
            f"{proc['memory_mb']:.1f}", 
            Text(proc['command'], style=style)
        )
    return table

def show_live_monitor():
    """Displays a live dashboard with smoother updates."""
    layout = Layout()
    layout.split(Layout(name="header", size=8), Layout(name="main"), Layout(name="footer", size=3))
    layout["main"].split_row(Layout(name="proc_cpu"), Layout(name="proc_mem"))
    layout["footer"].update(Panel(Text("Press Ctrl+C to exit. Enter PID to kill process.", justify="center"), border_style="dim"))
    
    system_info = get_system_info()
    prev_cpu_pids, prev_mem_pids = set(), set()

    with Live(layout, screen=True, redirect_stderr=False, transient=True) as live:
        try:
            psutil.cpu_percent(interval=None) # Prime the pump
            while True:
                # Gather data
                cpu_percent = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                mem_percent, mem_text = mem.percent, f"{mem.used/1024**3:.2f}G/{mem.total/1024**3:.2f}G"
                disk = psutil.disk_usage('/')
                disk_percent, disk_text = disk.percent, f"{disk.used/1024**3:.2f}G/{disk.total/1024**3:.2f}G"
                uptime_text = get_uptime()
                
                # Update header
                layout["header"].update(make_header_layout(cpu_percent, mem_percent, mem_text, disk_percent, disk_text, uptime_text, system_info))

                # Update processes
                view_height = max(5, os.get_terminal_size().lines - 12)
                cpu_procs = get_top_processes(sort_by='cpu_percent')[:view_height]
                mem_procs = get_top_processes(sort_by='memory_mb')[:view_height]

                current_cpu_pids = {p['pid'] for p in cpu_procs}
                cpu_table = Table(title="Top Processes by CPU", expand=True, border_style="green")
                cpu_table.add_column("PID", style="cyan", width=6)
                cpu_table.add_column("%CPU", style="green", justify="right", width=5)
                cpu_table.add_column("Mem(MB)", style="magenta", justify="right", width=7)
                cpu_table.add_column("Command", style="white", overflow="ellipsis")
                for proc in cpu_procs:
                    style = "bold yellow" if proc['pid'] not in prev_cpu_pids else "white"
                    cpu_table.add_row(str(proc['pid']), f"{proc['cpu_percent']:.1f}", f"{proc['memory_mb']:.1f}", Text(proc['command'], style=style))
                layout["proc_cpu"].update(Panel(cpu_table, border_style="green"))
                prev_cpu_pids = current_cpu_pids

                current_mem_pids = {p['pid'] for p in mem_procs}
                mem_table = Table(title="Top Processes by Memory", expand=True, border_style="magenta")
                mem_table.add_column("PID", style="cyan", width=6)
                mem_table.add_column("Mem(MB)", style="magenta", justify="right", width=7)
                mem_table.add_column("%CPU", style="green", justify="right", width=5)
                mem_table.add_column("Command", style="white", overflow="ellipsis")
                for proc in mem_procs:
                    style = "bold yellow" if proc['pid'] not in prev_mem_pids else "white"
                    mem_table.add_row(str(proc['pid']), f"{proc['memory_mb']:.1f}", f"{proc['cpu_percent']:.1f}", Text(proc['command'], style=style))
                layout["proc_mem"].update(Panel(mem_table, border_style="magenta"))
                prev_mem_pids = current_mem_pids
                
                time.sleep(2) # This now correctly controls the refresh rate
        except KeyboardInterrupt:
            pass

    # Ask to kill process after exiting the live view
    pid_to_kill = questionary.text(
        "Enter PID of process to kill, or leave empty to continue:",
        validate=lambda text: text.isdigit() or text == ""
    ).ask()
    
    if pid_to_kill:
        try:
            p = psutil.Process(int(pid_to_kill))
            p_name = p.name()
            p.terminate()
            console.print(f"[green]Process {pid_to_kill} ({p_name}) terminated.[/green]")
        except psutil.NoSuchProcess:
            console.print(f"[red]Error: Process with PID {pid_to_kill} not found.[/red]")
        except psutil.AccessDenied:
            console.print(f"[red]Error: Access denied. Try running with sudo.[/red]")
        time.sleep(2) 

def show_advanced_monitor():
    """Displays a more detailed, real-time system monitor."""
    layout = Layout()
    layout.split(
        Layout(name="main", ratio=3),
        Layout(name="processes", ratio=2)
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right", ratio=2)
    )
    layout["left"].split(Layout(name="cpu"), Layout(name="mem"))
    layout["processes"].split_row(Layout(name="proc_cpu"), Layout(name="proc_mem"))

    # To calculate network speed
    last_net_io = psutil.net_io_counters(pernic=True)

    with Live(layout, screen=True, redirect_stderr=False) as live:
        try:
            psutil.cpu_percent(interval=None, percpu=True) # Prime the pump
            while True:
                # --- CPU Panel ---
                cpu_percents = psutil.cpu_percent(interval=None, percpu=True)
                cpu_bars = Table(title="CPU Core Usage", show_header=False, show_edge=False, box=None)
                for i, percent in enumerate(cpu_percents):
                    cpu_bars.add_row(f"Core {i}", ProgressBar(total=100, completed=percent), f"{percent}%")
                layout["cpu"].update(Panel(cpu_bars, title="[bold green]CPU[/]", border_style="green"))

                # --- Memory Panel ---
                mem_table = Table(title="Memory Usage", show_header=False, show_edge=False, box=None)
                vmem = psutil.virtual_memory()
                swap = psutil.swap_memory()
                mem_table.add_row("Virtual", ProgressBar(total=100, completed=vmem.percent), f"{vmem.percent}%")
                mem_table.add_row("Swap", ProgressBar(total=100, completed=swap.percent), f"{swap.percent}%")
                layout["mem"].update(Panel(mem_table, title="[bold magenta]Memory[/]", border_style="magenta"))
                
                # --- Network Panel ---
                net_io = psutil.net_io_counters(pernic=True)
                net_table = Table(title="Network I/O", show_edge=True, box=None, expand=True)
                net_table.add_column("Interface", style="cyan")
                net_table.add_column("Sent", style="green", justify="right")
                net_table.add_column("Recv", style="blue", justify="right")
                net_table.add_column("Speed (S)", style="yellow", justify="right")
                net_table.add_column("Speed (R)", style="yellow", justify="right")
                
                for iface, io in net_io.items():
                    if iface in last_net_io:
                        sent_speed = io.bytes_sent - last_net_io[iface].bytes_sent
                        recv_speed = io.bytes_recv - last_net_io[iface].bytes_recv
                        net_table.add_row(
                            iface,
                            format_bytes(io.bytes_sent),
                            format_bytes(io.bytes_recv),
                            f"{format_bytes(sent_speed)}/s",
                            f"{format_bytes(recv_speed)}/s"
                        )
                last_net_io = net_io
                layout["right"].update(Panel(net_table, title="[bold cyan]Network[/]", border_style="cyan"))

                # --- Process Panels ---
                top_cpu = get_top_processes('cpu_percent')[:5]
                top_mem = get_top_processes('memory_mb')[:5]
                
                cpu_proc_table = create_process_table("Top 5 by CPU", top_cpu, "green")
                mem_proc_table = create_process_table("Top 5 by Memory", top_mem, "magenta")

                layout["proc_cpu"].update(Panel(cpu_proc_table, border_style="green"))
                layout["proc_mem"].update(Panel(mem_proc_table, border_style="magenta"))

                time.sleep(1) # Refresh rate

        except KeyboardInterrupt:
            pass # Exit gracefully
        except Exception as e:
            # This is important to catch errors within the loop
            console.print(f"An error occurred in the monitor loop: {e}")
            time.sleep(5) 