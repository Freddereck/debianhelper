import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from app.translations import t
from app.utils import run_command

console = Console()

def get_log_files():
    """Returns a list of common log files."""
    log_dirs = ['/var/log/']
    common_logs = ['syslog', 'auth.log', 'kern.log', 'fail2ban.log', 'ufw.log', 'nginx/access.log', 'nginx/error.log']
    log_files = []
    for d in log_dirs:
        for log in common_logs:
            if os.path.exists(os.path.join(d, log)):
                log_files.append(os.path.join(d, log))
    return log_files

def view_log_file(filepath, lines=50):
    """Displays the last N lines of a specific log file within a panel."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('logs_viewing_title', filepath=filepath, lines=lines), border_style="cyan"))
    
    try:
        # Use sudo to read protected log files
        command = f"sudo tail -n {lines} {filepath}"
        return_code = run_command(command, show_output=True, ignore_errors=True)
        
        if return_code != 0:
            console.print(t('logs_error_reading', filepath=filepath))

    except Exception as e:
        console.print(t('logs_error_unexpected', error=e))
    
    questionary.press_any_key_to_continue().ask()

def show_log_viewer():
    """Main menu for the log viewer."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('logs_title')}[/bold blue]"))
        
        log_files = get_log_files()
        if not log_files:
            console.print(t('logs_not_found'))
            questionary.press_any_key_to_continue().ask()
            break

        choices = log_files + [t('logs_menu_custom'), t('logs_menu_back')]
        
        log_choice = questionary.select(
            t('logs_prompt_select'),
            choices=choices
        ).ask()

        if log_choice == t('logs_menu_back') or log_choice is None:
            break
        elif log_choice == t('logs_menu_custom'):
            custom_path = questionary.text(t('logs_prompt_custom_path')).ask()
            if custom_path and os.path.exists(custom_path):
                view_log_file(custom_path)
            elif custom_path:
                console.print(t('logs_error_not_exist', path=custom_path))
                questionary.press_any_key_to_continue().ask()
        else:
            view_log_file(log_choice) 