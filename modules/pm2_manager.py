from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console, run_command
from localization import get_string
import shutil

console = Console()

def _list_pm2_processes():
    res = run_command(["pm2", "ls"], get_string("pm2_list"))
    if res and res.stdout:
        console.print(Panel(res.stdout, title="pm2 list", border_style="green"))
    else:
        console.print("[yellow]Нет процессов pm2 или pm2 не установлен.[/yellow]")

def _show_pm2_logs():
    name = inquirer.text(message=get_string("pm2_logs_prompt")).execute()
    if name:
        res = run_command(["pm2", "logs", name], get_string("pm2_logs", name=name))
        if res and res.stdout:
            console.print(Panel(res.stdout, title=f"pm2 logs {name}", border_style="cyan"))
        else:
            console.print("[yellow]Лог пуст или процесс не найден.[/yellow]")

def _start_pm2_process():
    cmd = inquirer.text(message=get_string("pm2_start_cmd_prompt")).execute()
    name = inquirer.text(message=get_string("pm2_start_name_prompt")).execute()
    cwd = inquirer.text(message="Укажите директорию проекта (например, /var/www/yourproject):").execute()
    if cmd and name and cwd:
        res = run_command(["pm2", "start"] + cmd.split() + ["--name", name], get_string("pm2_starting", name=name), cwd=cwd)
        if res and res.stdout:
            console.print(Panel(res.stdout, title=f"pm2 start {name}", border_style="green"))

def _stop_pm2_process():
    name = inquirer.text(message=get_string("pm2_stop_name_prompt")).execute()
    if name:
        res = run_command(["pm2", "stop", name], get_string("pm2_stopping", name=name))
        if res and res.stdout:
            console.print(Panel(res.stdout, title=f"pm2 stop {name}", border_style="red"))

def _restart_pm2_process():
    name = inquirer.text(message=get_string("pm2_restart_name_prompt")).execute()
    if name:
        res = run_command(["pm2", "restart", name], get_string("pm2_restarting", name=name))
        if res and res.stdout:
            console.print(Panel(res.stdout, title=f"pm2 restart {name}", border_style="yellow"))

def _delete_pm2_process():
    name = inquirer.text(message=get_string("pm2_delete_name_prompt")).execute()
    if name:
        res = run_command(["pm2", "delete", name], get_string("pm2_deleting", name=name))
        if res and res.stdout:
            console.print(Panel(res.stdout, title=f"pm2 delete {name}", border_style="red"))

def _reload_pm2():
    res = run_command(["pm2", "reload", "all"], get_string("pm2_reload"))
    if res and res.stdout:
        console.print(Panel(res.stdout, title="pm2 reload all", border_style="green"))

def _monit_pm2():
    if not shutil.which("pm2"):
        console.print("[red]pm2 не установлен. Установите через npm install -g pm2[/red]")
        return
    console.print(get_string("pm2_monit_hint"))
    import subprocess
    try:
        subprocess.run(["pm2", "monit"])
    except Exception as e:
        console.print(f"[red]Ошибка запуска pm2 monit: {e}[/red]")

def run_pm2_manager():
    if not shutil.which("pm2"):
        console.print("[red]pm2 не установлен. Установите через npm install -g pm2[/red]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    while True:
        clear_console()
        console.print(Panel(get_string("pm2_manager_title"), border_style="green"))
        choices = [
            Choice("list", name=get_string("pm2_list")),
            Choice("logs", name=get_string("pm2_logs_menu")),
            Choice("start", name=get_string("pm2_start_menu")),
            Choice("stop", name=get_string("pm2_stop_menu")),
            Choice("restart", name=get_string("pm2_restart_menu")),
            Choice("delete", name=get_string("pm2_delete_menu")),
            Choice("reload", name=get_string("pm2_reload_menu")),
            Choice("monit", name=get_string("pm2_monit_menu")),
            Choice(None, name=get_string("action_back")),
        ]
        action = inquirer.select(message=get_string("pm2_manager_prompt"), choices=choices, vi_mode=True).execute()
        if action == "list":
            _list_pm2_processes()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "logs":
            _show_pm2_logs()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "start":
            _start_pm2_process()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "stop":
            _stop_pm2_process()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "restart":
            _restart_pm2_process()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "delete":
            _delete_pm2_process()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "reload":
            _reload_pm2()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "monit":
            _monit_pm2()
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        else:
            break 