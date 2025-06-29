import psutil
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console
import datetime
import signal
import time
import threading
import os
from collections import defaultdict, deque
import shutil
import subprocess

console = Console()

STATUS_COLORS = {
    'running': 'green',
    'sleeping': 'yellow',
    'stopped': 'red',
    'zombie': 'magenta',
    'dead': 'grey50',
    'idle': 'cyan',
    'disk-sleep': 'blue',
    'tracing-stop': 'bright_red',
    'waking': 'bright_yellow',
    'parked': 'bright_cyan',
    'locked': 'bright_magenta',
    'waiting': 'bright_blue',
}

HTOP_INSTALL_CMDS = [
    ("apt", ["apt", "install", "-y", "htop"]),
    ("yum", ["yum", "install", "-y", "htop"]),
    ("pacman", ["pacman", "-Sy", "htop"]),
]

def format_time(ts):
    try:
        return datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    except Exception:
        return "-"

def get_sys_panel():
    # CPU, RAM, uptime, load
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    uptime = "-"
    try:
        uptime_sec = time.time() - psutil.boot_time()
        uptime = str(datetime.timedelta(seconds=int(uptime_sec)))
    except Exception:
        pass
    load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
    return Panel(f"[bold]CPU:[/bold] {cpu:.1f}%  [bold]RAM:[/bold] {mem.percent:.1f}%  [bold]Uptime:[/bold] {uptime}  [bold]Load:[/bold] {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}", title="Системная нагрузка", border_style="green")

def get_proc_table(sort_by='cpu', search=None):
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'cmdline', 'status', 'create_time', 'ppid', 'num_threads']):
        try:
            info = p.info
            cmd = ' '.join(info.get('cmdline') or [])
            processes.append({
                'pid': info['pid'],
                'name': info.get('name', ''),
                'user': info.get('username', ''),
                'cpu': info.get('cpu_percent', 0.0),
                'mem': info.get('memory_percent', 0.0),
                'cmd': cmd,
                'status': info.get('status', ''),
                'start': format_time(info.get('create_time', 0)),
                'ppid': info.get('ppid', 0),
                'threads': info.get('num_threads', 0),
            })
        except Exception:
            continue
    if search:
        processes = [p for p in processes if search.lower() in p['name'].lower() or search.lower() in p['cmd'].lower()]
    processes.sort(key=lambda x: x[sort_by] if sort_by in x else 0, reverse=True)
    table = Table(title="Процессы (Q — выход, F — фильтр, S — сортировка)", show_lines=False, row_styles=["none", "dim"])
    table.add_column("PID", style="cyan", no_wrap=True)
    table.add_column("Имя", style="magenta")
    table.add_column("Пользователь", style="green")
    table.add_column("CPU %", style="yellow")
    table.add_column("RAM %", style="blue")
    table.add_column("Статус", style="white")
    table.add_column("Threads", style="bright_cyan")
    table.add_column("PPID", style="bright_magenta")
    table.add_column("Старт", style="bright_yellow")
    table.add_column("Команда", style="white")
    for proc in processes[:30]:
        status_col = STATUS_COLORS.get(proc['status'], 'white')
        cpu_col = "red" if proc['cpu'] > 50 else ("yellow" if proc['cpu'] > 10 else "green")
        mem_col = "red" if proc['mem'] > 30 else ("yellow" if proc['mem'] > 10 else "blue")
        table.add_row(
            str(proc['pid']), proc['name'], proc['user'], f"[{cpu_col}]{proc['cpu']:.1f}[/{cpu_col}]", f"[{mem_col}]{proc['mem']:.1f}[/{mem_col}]",
            f"[{status_col}]{proc['status']}[/{status_col}]", str(proc['threads']), str(proc['ppid']), proc['start'], proc['cmd']
        )
    return table

def build_proc_tree(processes):
    """Строит дерево процессов: возвращает root-процессы и мапу pid->children."""
    by_pid = {p['pid']: p for p in processes}
    children = defaultdict(list)
    roots = []
    for p in processes:
        parent = p['ppid']
        if parent in by_pid:
            children[parent].append(p)
        else:
            roots.append(p)
    return roots, children

def get_proc_tree(processes, limit=100):
    roots, children = build_proc_tree(processes)
    table = Table(title="Дерево процессов (Q — выход, F — фильтр, S — сортировка, T — таблица)", show_lines=False, row_styles=["none", "dim"])
    table.add_column("PID", style="cyan", no_wrap=True)
    table.add_column("Имя", style="magenta")
    table.add_column("Пользователь", style="green")
    table.add_column("CPU %", style="yellow")
    table.add_column("RAM %", style="blue")
    table.add_column("Статус", style="white")
    table.add_column("Threads", style="bright_cyan")
    table.add_column("PPID", style="bright_magenta")
    table.add_column("Старт", style="bright_yellow")
    table.add_column("Команда", style="white")
    shown = 0
    def add_row(proc, level=0, branch_prefix=""):
        nonlocal shown
        if shown >= limit:
            return
        status_col = STATUS_COLORS.get(proc['status'], 'white')
        cpu_col = "red" if proc['cpu'] > 50 else ("yellow" if proc['cpu'] > 10 else "green")
        mem_col = "red" if proc['mem'] > 30 else ("yellow" if proc['mem'] > 10 else "blue")
        indent = "  " * level + (branch_prefix if level else "")
        table.add_row(
            str(proc['pid']),
            indent + proc['name'],
            proc['user'],
            f"[{cpu_col}]{proc['cpu']:.1f}[/{cpu_col}]",
            f"[{mem_col}]{proc['mem']:.1f}[/{mem_col}]",
            f"[{status_col}]{proc['status']}[/{status_col}]",
            str(proc['threads']),
            str(proc['ppid']),
            proc['start'],
            proc['cmd']
        )
        shown += 1
        kids = sorted(children.get(proc['pid'], []), key=lambda x: x['pid'])
        for i, child in enumerate(kids):
            last = (i == len(kids) - 1)
            branch = ("└─ " if last else "├─ ")
            add_row(child, level+1, branch)
    for root in sorted(roots, key=lambda x: x['pid']):
        add_row(root)
        if shown >= limit:
            break
    return table

def follow_mode():
    sort_by = 'cpu'
    search = None
    stop = threading.Event()
    show_tree = False
    def key_listener():
        import sys
        while not stop.is_set():
            ch = sys.stdin.read(1)
            if ch.lower() == 'q':
                stop.set()
            elif ch.lower() == 'f':
                console.print("\n[cyan]Введите фильтр по имени процесса:[/cyan]", end=' ')
                search_val = input()
                nonlocal search
                search = search_val.strip() or None
            elif ch.lower() == 's':
                console.print("\n[cyan]Сортировать по (cpu/mem/pid/name/start):[/cyan]", end=' ')
                val = input().strip()
                if val in ('cpu','mem','pid','name','start'):
                    nonlocal sort_by
                    sort_by = val
            elif ch.lower() == 't':
                nonlocal show_tree
                show_tree = not show_tree
    console.clear()
    console.print("[bold green]Режим мониторинга процессов (htop-like)[/bold green]")
    console.print("[yellow]Q — выход, F — фильтр, S — сортировка, T — дерево/таблица[/yellow]")
    t = threading.Thread(target=key_listener, daemon=True)
    t.start()
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while not stop.is_set():
            # Получаем процессы
            processes = []
            for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'cmdline', 'status', 'create_time', 'ppid', 'num_threads']):
                try:
                    info = p.info
                    cmd = ' '.join(info.get('cmdline') or [])
                    processes.append({
                        'pid': info['pid'],
                        'name': info.get('name', ''),
                        'user': info.get('username', ''),
                        'cpu': info.get('cpu_percent', 0.0),
                        'mem': info.get('memory_percent', 0.0),
                        'cmd': cmd,
                        'status': info.get('status', ''),
                        'start': format_time(info.get('create_time', 0)),
                        'ppid': info.get('ppid', 0),
                        'threads': info.get('num_threads', 0),
                    })
                except Exception:
                    continue
            if search:
                processes = [p for p in processes if search.lower() in p['name'].lower() or search.lower() in p['cmd'].lower()]
            if show_tree:
                table = get_proc_tree(processes)
            else:
                processes.sort(key=lambda x: x[sort_by] if sort_by in x else 0, reverse=True)
                table = get_proc_table(sort_by, search)
            live.update(Group(get_sys_panel(), table))
            time.sleep(2)
    t.join()
    console.print("[green]Выход из режима мониторинга процессов.[/green]")

def run_process_manager():
    clear_console()
    if not shutil.which("htop"):
        console.print("[yellow]htop не установлен![/yellow]")
        install = inquirer.confirm(message="Установить htop сейчас?", default=True).execute()
        if install:
            for mgr, cmd in HTOP_INSTALL_CMDS:
                if shutil.which(mgr):
                    console.print(f"[cyan]Устанавливаю htop через {mgr}...[/cyan]")
                    subprocess.run(["sudo"] + cmd)
                    break
            else:
                console.print("[red]Не удалось определить пакетный менеджер. Установите htop вручную![/red]")
                inquirer.text(message="Нажмите Enter для возврата...").execute()
                return
        else:
            console.print("[yellow]Мониторинг процессов отменён.[/yellow]")
            inquirer.text(message="Нажмите Enter для возврата...").execute()
            return
    # Запуск htop
    console.print("[green]Запуск htop. Для выхода нажмите F10 или q.[/green]")
    inquirer.text(message="Нажмите Enter для запуска htop...").execute()
    subprocess.run(["htop"])
    console.print("[cyan]Вы вышли из htop. Возврат в меню.")
    inquirer.text(message="Нажмите Enter для возврата...").execute() 