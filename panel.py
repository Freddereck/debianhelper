import sys
import subprocess
import os
import shutil

# --- Dependency Check ---
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.separator import Separator
except ImportError as e:
    # Using simple print because 'rich' might not be installed.
    print("\n[ERROR] A required Python module is not installed.")
    print(f"--> The module '{e.name}' is missing.")
    
    # Check for root privileges
    if os.geteuid() != 0:
        print("\n[ERROR] This script requires root privileges to manage dependencies.")
        print("Please run it with 'sudo'.")
        sys.exit(1)

    # Check for pip
    pip_executable = None
    try:
        subprocess.check_call(['pip3', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pip_executable = 'pip3'
    except FileNotFoundError:
        try:
            subprocess.check_call(['pip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pip_executable = 'pip'
        except FileNotFoundError:
            pass # pip is not installed

    # If pip is not found, offer to install it
    if not pip_executable:
        print("\n[WARNING] 'pip' or 'pip3' is not installed, which is required to fetch dependencies.")
        try:
            answer = input("--> Would you like to attempt to install it via 'apt-get install python3-pip'? [y/N]: ").lower()
            if answer == 'y':
                print("\nAttempting to install 'python3-pip'...")
                subprocess.check_call(['apt-get', 'update'])
                subprocess.check_call(['apt-get', 'install', '-y', 'python3-pip'])
                pip_executable = 'pip3' # Assume pip3 is the one installed
                print("\n'python3-pip' installed successfully.")
            else:
                print("\nInstallation cancelled. Please install 'pip' manually and rerun the script.")
                sys.exit(1)
        except subprocess.CalledProcessError as install_error:
            print(f"\n[ERROR] Failed to install 'python3-pip'. Return code: {install_error.returncode}")
            print("Please try installing it manually.")
            sys.exit(1)
        except (KeyboardInterrupt, EOFError):
             print("\n\nOperation cancelled by user.")
             sys.exit(1)


    # Now, use pip to install dependencies from requirements.txt
    if pip_executable:
        print(f"\n--> Attempting to install required packages using '{pip_executable}'...")
        try:
            # Construct path to requirements.txt relative to the script's location
            script_dir = os.path.dirname(os.path.realpath(__file__))
            requirements_path = os.path.join(script_dir, 'requirements.txt')
            
            if not os.path.exists(requirements_path):
                 print(f"[ERROR] 'requirements.txt' not found at '{requirements_path}'.")
                 sys.exit(1)

            subprocess.check_call([pip_executable, 'install', '-r', requirements_path])
            
            print("\n[SUCCESS] Dependencies installed successfully.")
            print("--> Restarting the script to apply changes...\n")
            
            # Restart the script
            os.execv(sys.executable, ['python3'] + sys.argv)
            
        except subprocess.CalledProcessError as install_error:
            print(f"\n[ERROR] Failed to install dependencies from 'requirements.txt'. Return code: {install_error.returncode}")
            print("Please check the error messages above and try to resolve the issue.")
            sys.exit(1)
        except (KeyboardInterrupt, EOFError):
             print("\n\nOperation cancelled by user.")
             sys.exit(1)

# --- End of Dependency Check ---

from modules.security import run_security_analysis
from modules.system_info import (
    get_os_info, get_uptime, get_mem_usage, get_load_avg
)
from modules.log_viewer import run_log_viewer
from modules.software_manager import run_software_manager
from modules.wireguard_manager import run_wireguard_manager, _is_wireguard_installed as is_wg_installed
from localization import load_language_strings, get_string
from modules.panel_utils import clear_console
from modules.webserver_manager import run_webserver_manager
from modules.pm2_manager import run_pm2_manager

console = Console()

# --- Language Setup ---
# Load the desired language strings. 'en' for English, 'ru' for Russian.
load_language_strings('ru')

VERSION = '3.0 PRE-Release'

def display_header():
    """Displays the application header with ASCII art and a system info dashboard."""
    
    # --- System Info Panel ---
    hostname, os_version = get_os_info()
    uptime = get_uptime()
    mem_total, mem_used, _ = get_mem_usage()
    load_avg = get_load_avg()

    # Format load average for color display
    load_text = load_avg
    if load_avg != "N/A":
        load_values = load_avg.split()
        if len(load_values) >= 3:
            load_text = f"[green]{load_values[0]}[/] [yellow]{load_values[1]}[/] [red]{load_values[2]}[/]"

    info_table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 1))
    info_table.add_column(style="bold magenta", no_wrap=True)
    info_table.add_column(style="cyan")
    info_table.add_row(f"{get_string('hostname')}:", hostname)
    info_table.add_row(f"{get_string('os_version')}:", os_version)
    info_table.add_row(f"{get_string('uptime')}:", uptime)
    info_table.add_row(f"{get_string('memory_usage')}:", f"{mem_used} / {mem_total}")
    info_table.add_row(f"{get_string('load_avg')}:", load_text)

    ascii_art = Text("""
██╗  ██╗███████╗██╗     ██████╗ ███████╗██████╗ 
██║  ██║██╔════╝██║     ██╔══██╗██╔════╝██╔══██╗
███████║█████╗  ██║     ██████╔╝█████╗  ██████╔╝
██╔══██║██╔══╝  ██║     ██╔═══╝ ██╔══╝  ██╔══██╗
██║  ██║███████╗███████╗██║     ███████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝
    """, style="bold blue", justify="left")

    # --- Main Layout ---
    top_layout = Columns([
        ascii_art,
        Panel(info_table, title="[bold]System State[/bold]", border_style="green", padding=(0, 2))
    ], equal=True)
    console.print(top_layout)
    
    # --- App Title and Copyright ---
    title = get_string("app_title")
    copyright_text = get_string("copyright_text")
    console.print(Panel(Align.center(title, vertical="middle"), style="bold green", subtitle=copyright_text))

def get_language():
    """Prompts the user to select a language using an interactive menu."""
    clear_console()
    console.print(Panel("Please select a language / Пожалуйста, выберите язык", title="Language / Язык", border_style="bold yellow"))
    lang_choice = inquirer.select(
        message="Select a language:",
        choices=[
            Choice("en", name="English"),
            Choice("ru", name="Русский"),
        ],
        default="en",
    ).execute()
    if lang_choice is None:
        return False
    load_language_strings(lang_choice)
    return True

def update_self():
    import time
    # Проверка git
    if not shutil.which('git'):
        console.print(Panel("Git не установлен. Устанавливаю git...", title="[yellow]Установка git[/yellow]", border_style="yellow"))
        res = subprocess.run(['apt-get', 'update'])
        res2 = subprocess.run(['apt-get', 'install', '-y', 'git'])
        if not shutil.which('git'):
            console.print(Panel("[red]Не удалось установить git. Установите вручную: apt-get install -y git[/red]", title="[red]Ошибка[/red]", border_style="red"))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return
        else:
            console.print(Panel("[green]Git успешно установлен![/green]", title="[green]Успех[/green]", border_style="green"))
            time.sleep(1)
    # Проверка git-репозитория
    if not os.path.exists('.git'):
        console.print(Panel("Текущая папка не является git-репозиторием. Автообновление невозможно.", title="[red]Ошибка[/red]", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    # git fetch и проверка обновлений
    fetch = subprocess.run(['git', 'fetch'], capture_output=True, text=True)
    status = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)
    if 'Your branch is up to date' in status.stdout or 'Ваша ветка обновлена' in status.stdout:
        console.print(Panel("Панель уже обновлена до последней версии.", title="[green]Нет обновлений[/green]", border_style="green"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    else:
        console.print(Panel("Доступны обновления! Хотите обновить панель?", title="[yellow]Обновление доступно[/yellow]", border_style="yellow"))
        confirm = inquirer.confirm(message="Выполнить обновление?", default=True).execute()
        if not confirm:
            return
        # git pull
        pull = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        if pull.returncode == 0:
            console.print(Panel(pull.stdout, title="[green]Обновление завершено[/green]", border_style="green"))
            # Проверяем, изменился ли requirements.txt
            if 'requirements.txt' in pull.stdout:
                console.print(Panel("Обнаружены изменения в requirements.txt. Обновляю зависимости...", title="[yellow]Обновление зависимостей[/yellow]", border_style="yellow"))
                pip_exec = shutil.which('pip3') or shutil.which('pip')
                if pip_exec:
                    req_res = subprocess.run([pip_exec, 'install', '-r', 'requirements.txt'], capture_output=True, text=True)
                    if req_res.returncode == 0:
                        console.print(Panel("Зависимости успешно обновлены!", title="[green]Успех[/green]", border_style="green"))
                    else:
                        console.print(Panel(req_res.stderr or req_res.stdout, title="[red]Ошибка обновления зависимостей[/red]", border_style="red"))
                else:
                    console.print(Panel("[red]pip не найден. Установите pip вручную![/red]", title="[red]Ошибка[/red]", border_style="red"))
            console.print(Panel("Рекомендуется перезапустить панель для применения обновлений!", title="[yellow]Требуется перезапуск[/yellow]", border_style="yellow"))
        else:
            console.print(Panel(pull.stderr or pull.stdout, title="[red]Ошибка git pull[/red]", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()

def main_menu():
    """Displays the main menu and handles user choices."""
    ascii_art = rf"""
██╗  ██╗███████╗██╗     ██████╗ ███████╗██████╗ 
██║  ██║██╔════╝██║     ██╔══██╗██╔════╝██╔══██╗
███████║█████╗  ██║     ██████╔╝█████╗  ██████╔╝
██╔══██║██╔══╝  ██║     ██╔═══╝ ██╔══╝  ██╔══██╗
██║  ██║███████╗███████╗██║     ███████╗██║  ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝

         Linux Helper Panel v{VERSION}
"""
    while True:
        try:
            clear_console()
            # --- ASCII и копирайт ---
            console.print(Align.center(ascii_art, vertical="top"))
            console.print(Align.center(get_string("copyright_text"), vertical="top"))
            # --- Системная информация ---
            os_info = get_os_info()
            uptime = get_uptime()
            mem = get_mem_usage()
            load = get_load_avg()
            sysinfo = (
                f"[bold]OS:[/bold] [cyan]{os_info}[/cyan]\n"
                f"[bold]Uptime:[/bold] [green]{uptime}[/green]\n"
                f"[bold]RAM:[/bold] [magenta]{mem}[/magenta]\n"
                f"[bold]Load:[/bold] [yellow]{load}[/yellow]"
            )
            console.print(Panel(sysinfo, title="[cyan]Системная информация[/cyan]", border_style="cyan"))
            # --- Главное меню ---
            choices = [
                Choice("processes", name="Мониторинг процессов"),
                Choice("user_manager", name="Управление пользователями"),
                Choice("cron_manager", name="Управление задачами (cron)"),
                Choice("network_manager", name="Управление сетью"),
                Choice("software", name=get_string("main_menu_software_manager")),
                Choice("update_self", name="Обновить панель"),
            ]
            if is_wg_installed():
                choices.append(Choice("wireguard", name=get_string("main_menu_wireguard_manager")))
            choices.append(Choice("webserver", name=get_string("main_menu_webserver_manager")))
            if shutil.which("pm2"):
                choices.append(Choice("pm2", name=get_string("main_menu_pm2_manager")))
            choices.extend([
                Choice("security", name=get_string("main_menu_security_analysis")),
                Choice("log_viewer", name=get_string("main_menu_log_viewer")),
                Choice(None, name=get_string("main_menu_exit")),
            ])
            selected = inquirer.select(
                message=get_string("main_menu_prompt"),
                choices=choices,
                vi_mode=True
            ).execute()
            if selected == "processes":
                from modules.process_manager import run_process_manager
                run_process_manager()
            elif selected == "user_manager":
                from modules.user_manager import run_user_manager
                run_user_manager()
            elif selected == "cron_manager":
                from modules.cron_manager import run_cron_manager
                run_cron_manager()
            elif selected == "network_manager":
                from modules.network_manager import run_network_manager
                run_network_manager()
            elif selected == "software":
                run_software_manager()
            elif selected == "update_self":
                update_self()
            elif selected == "wireguard":
                run_wireguard_manager()
            elif selected == "webserver":
                run_webserver_manager()
            elif selected == "pm2":
                run_pm2_manager()
            elif selected == "security":
                run_security_analysis()
            elif selected == "log_viewer":
                run_log_viewer()
            else:
                break
        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break

def main():
    """Main function to run the application."""
    if not get_language():
        print("\nLanguage selection cancelled. Exiting.")
        return
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print(f'\n{get_string("operation_cancelled")}')
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f'\n{get_string("operation_cancelled")}')
    except Exception as e:
        # Catch any unexpected errors to ensure cleanup happens
        console.print_exception(show_locals=True)
    finally:
        # This will run no matter how the program exits (normal, Ctrl+C, or error)
        # It restores the terminal to a usable state.
        os.system('stty sane')
        print("\nTerminal restored. Exiting.") 