import pwd
import grp
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console
from localization import get_string

console = Console()

SUDOERS_PATH = "/etc/sudoers"


def list_users():
    users = []
    for p in pwd.getpwall():
        if (p.pw_uid == 0) or (p.pw_uid >= 1000 and p.pw_name != 'nobody'):
            users.append({
                'name': p.pw_name,
                'uid': p.pw_uid,
                'gid': p.pw_gid,
                'group': grp.getgrgid(p.pw_gid).gr_name if p.pw_gid in [g.gr_gid for g in grp.getgrall()] else '-',
                'home': p.pw_dir,
                'shell': p.pw_shell,
            })
    return users

def show_users_table():
    users = list_users()
    table = Table(title=get_string("user_manager_title"), show_lines=True)
    table.add_column(get_string("user_name"), style="cyan")
    table.add_column("UID", style="magenta")
    table.add_column("GID", style="green")
    table.add_column("Группа", style="yellow")
    table.add_column("Домашняя папка", style="blue")
    table.add_column("Shell", style="white")
    for u in users:
        table.add_row(u['name'], str(u['uid']), str(u['gid']), u['group'], u['home'], u['shell'])
    console.print(table)

def add_user():
    name = inquirer.text(message=get_string("user_name")).execute()
    if not name:
        return
    shell = inquirer.text(message=get_string("user_shell"), default="/bin/bash").execute()
    subprocess.run(["sudo", "useradd", "-m", "-s", shell, name])
    console.print(f"[green]{get_string('user_add_success', name=name)}[/green]")
    inquirer.text(message=get_string("user_press_enter")).execute()

def delete_user():
    users = [u['name'] for u in list_users()]
    name = inquirer.select(message=get_string("user_delete"), choices=users, vi_mode=True).execute()
    if not name:
        return
    confirm = inquirer.confirm(message=get_string("user_delete_confirm", name=name), default=False).execute()
    if confirm:
        subprocess.run(["sudo", "userdel", "-r", name])
        console.print(f"[red]{get_string('user_delete_success', name=name)}[/red]")
        inquirer.text(message=get_string("user_press_enter")).execute()

def reset_password():
    users = [u['name'] for u in list_users()]
    name = inquirer.select(message=get_string("user_resetpw"), choices=users, vi_mode=True).execute()
    if not name:
        return
    console.print(f"[yellow]{get_string('user_resetpw_info', name=name)}[/yellow]")
    inquirer.text(message=get_string("user_press_enter")).execute()
    subprocess.run(["sudo", "passwd", name])

def lock_unlock_user():
    users = [u['name'] for u in list_users()]
    name = inquirer.select(message=get_string("user_lock"), choices=users, vi_mode=True).execute()
    if not name:
        return
    res = subprocess.run(["passwd", "-S", name], capture_output=True, text=True)
    locked = " L " in res.stdout if res and res.stdout else False
    if locked:
        unlock = inquirer.confirm(message=get_string("user_lock_status", name=name), default=True).execute()
        if unlock:
            subprocess.run(["sudo", "usermod", "-U", name])
            console.print(f"[green]{get_string('user_unlock_success', name=name)}[/green]")
    else:
        lock = inquirer.confirm(message=get_string("user_lock_confirm", name=name), default=False).execute()
        if lock:
            subprocess.run(["sudo", "usermod", "-L", name])
            console.print(f"[yellow]{get_string('user_lock_success', name=name)}[/yellow]")
    inquirer.text(message=get_string("user_press_enter")).execute()

def edit_sudoers():
    console.print(Panel(get_string("user_sudoers_warning"), title="sudoers", border_style="red"))
    confirm = inquirer.confirm(message=get_string("user_sudoers_open"), default=False).execute()
    if confirm:
        subprocess.run(["sudo", "visudo"])
    inquirer.text(message=get_string("user_press_enter")).execute()

def run_user_manager():
    while True:
        clear_console()
        console.print(Panel(f"[bold green]{get_string('user_manager_title')}[/bold green]", border_style="green"))
        choices = [
            Choice("list", get_string("user_list")),
            Choice("add", get_string("user_add")),
            Choice("delete", get_string("user_delete")),
            Choice("resetpw", get_string("user_resetpw")),
            Choice("lock", get_string("user_lock")),
            Choice("sudoers", get_string("user_sudoers")),
            Choice(None, get_string("user_back"))
        ]
        action = inquirer.select(message=get_string("user_manager_title"), choices=choices, vi_mode=True).execute()
        if action == "list":
            show_users_table()
            inquirer.text(message=get_string("user_press_enter")).execute()
        elif action == "add":
            add_user()
        elif action == "delete":
            delete_user()
        elif action == "resetpw":
            reset_password()
        elif action == "lock":
            lock_unlock_user()
        elif action == "sudoers":
            edit_sudoers()
        else:
            break 