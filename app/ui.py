from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

console = Console()

def make_header_layout(cpu_percent, mem_percent, mem_text, disk_percent, disk_text, uptime_text, sys_info):
    """Creates a more compact and responsive header layout."""
    header = Layout(name="header")

    # Layout for stats bars and text values
    stats_table = Table.grid(expand=True, padding=(0, 1))
    stats_table.add_column(justify="left", no_wrap=True, width=5) # Label (CPU)
    stats_table.add_column(justify="right", width=7) # Percentage
    stats_table.add_column(justify="left") # Bar
    stats_table.add_column(justify="left", no_wrap=True) # Text (1.5G/3.8G)

    stats_table.add_row("[b green]CPU", f"({cpu_percent}%)", ProgressBar(total=100, completed=cpu_percent, width=15))
    stats_table.add_row("[b magenta]MEM", f"({mem_percent}%)", ProgressBar(total=100, completed=mem_percent, width=15), f"({mem_text})")
    stats_table.add_row("[b yellow]DISK", f"({disk_percent}%)", ProgressBar(total=100, completed=disk_percent, width=15), f"({disk_text})")

    # Layout for right-side info
    right_layout = Table.grid(expand=True)
    right_layout.add_column()
    right_layout.add_row(Panel(Text(uptime_text, justify="center"), title="Uptime", border_style="cyan", height=3))
    
    cpu_model = sys_info.get('cpu_model', 'N/A')
    # Truncate long CPU names
    if len(cpu_model) > 30:
        cpu_model = cpu_model[:27] + "..."
    
    sys_info_text = Text(f"CPU: {cpu_model}\n", justify="left")
    sys_info_text.append(f"Cores: {sys_info.get('cores', 'N/A')} | Threads: {sys_info.get('threads', 'N/A')}")
    right_layout.add_row(Panel(sys_info_text, title="System Info", border_style="cyan"))

    # Combine into columns
    header_columns = Columns([stats_table, right_layout], expand=True, equal=True)
    header.update(Panel(header_columns, title="System Overview"))
    return header 