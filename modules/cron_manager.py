import subprocess
import pwd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console
from localization import get_string

console = Console()


def get_users():
    users = []
    for p in pwd.getpwall():
        if (p.pw_uid == 0) or (p.pw_uid >= 1000 and p.pw_name != 'nobody'):
            users.append(p.pw_name)
    return users

def get_crontab(user):
    try:
        res = subprocess.run(["crontab", "-l", "-u", user], capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.splitlines()
        else:
            return []
    except Exception:
        return []

def show_crontab(user):
    lines = get_crontab(user)
    table = Table(title=get_string("cron_show_table", user=user), show_lines=True)
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column(get_string("cron_add_command"), style="white")
    for i, line in enumerate(lines):
        table.add_row(str(i+1), line)
    console.print(table)

def add_cron_job(user):
    console.print(Panel(get_string("cron_help_panel"), title="Справка по cron", border_style="blue"))
    expr = inquirer.text(message=get_string("cron_add_schedule")).execute()
    cmd = inquirer.text(message=get_string("cron_add_command")).execute()
    if not expr or not cmd:
        return
    # Добавить задание
    lines = get_crontab(user)
    lines.append(f"{expr} {cmd}")
    tmpfile = f"/tmp/cron_{user}.txt"
    with open(tmpfile, "w") as f:
        f.write("\n".join(lines) + "\n")
    subprocess.run(["crontab", "-u", user, tmpfile])
    console.print(f"[green]{get_string('cron_add_success', user=user)}[/green]")
    inquirer.text(message=get_string("cron_press_enter")).execute()

def delete_cron_job(user):
    lines = get_crontab(user)
    if not lines:
        console.print(f"[yellow]{get_string('cron_no_jobs')}[/yellow]")
        inquirer.text(message=get_string("cron_press_enter")).execute()
        return
    choices = [Choice(str(i), f"{line}") for i, line in enumerate(lines)]
    idx = inquirer.select(message=get_string("cron_delete_select"), choices=choices, vi_mode=True).execute()
    if idx is None:
        return
    idx = int(idx)
    lines.pop(idx)
    tmpfile = f"/tmp/cron_{user}.txt"
    with open(tmpfile, "w") as f:
        f.write("\n".join(lines) + "\n")
    subprocess.run(["crontab", "-u", user, tmpfile])
    console.print(f"[red]{get_string('cron_delete_success', user=user)}[/red]")
    inquirer.text(message=get_string("cron_press_enter")).execute()

def edit_crontab(user):
    console.print(Panel(get_string("cron_edit_info"), title=get_string("cron_edit"), border_style="yellow"))
    inquirer.text(message=get_string("cron_press_enter")).execute()
    subprocess.run(["crontab", "-e", "-u", user])

def run_cron_manager():
    while True:
        clear_console()
        console.print(Panel(f"[bold green]{get_string('cron_manager_title')}[/bold green]", border_style="green"))
        users = get_users()
        user = inquirer.select(message=get_string("cron_select_user"), choices=users, vi_mode=True).execute()
        if not user:
            break
        while True:
            clear_console()
            show_crontab(user)
            choices = [
                Choice("add", get_string("cron_add")),
                Choice("delete", get_string("cron_delete")),
                Choice("edit", get_string("cron_edit")),
                Choice("back", get_string("cron_back_user")),
                Choice(None, get_string("cron_exit"))
            ]
            action = inquirer.select(message=get_string("cron_manager_title"), choices=choices, vi_mode=True).execute()
            if action == "add":
                add_cron_job(user)
            elif action == "delete":
                delete_cron_job(user)
            elif action == "edit":
                edit_crontab(user)
            elif action == "back":
                break
            else:
                return 