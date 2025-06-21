import os
import getpass
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from crontab import CronTab
from app.translations import t

console = Console()

def get_cron():
    """Gets the CronTab for the current user, handling permissions."""
    try:
        # This is the most compatible way, should work with old and new versions.
        # The library itself should handle getting the right crontab based on EUID.
        # When run with sudo, it should access root's crontab.
        return CronTab()
    except Exception as e:
        console.print(f"[bold red]{t('cron_error_permission')}[/bold red]")
        console.print(f"[bold red]Error: {e}[/bold red]")
        return None

def list_jobs(cron):
    """Lists all cron jobs for the user."""
    os.system('cls' if os.name == 'nt' else 'clear')
    user = getpass.getuser()
    console.print(Panel(t('cron_current_jobs', user=user)))
    
    if len(cron) == 0:
        console.print(t('cron_no_jobs'))
        return

    table = Table()
    table.add_column(t('cron_col_schedule'), style="cyan")
    table.add_column(t('cron_col_command'), style="magenta")
    table.add_column(t('cron_col_comment'), style="green")

    for job in cron:
        table.add_row(str(job.slices), job.command, job.comment)
    
    console.print(table)

def add_job(cron):
    """Adds a new cron job."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('cron_add_title')))
    
    command = questionary.text(t('cron_add_prompt_command')).ask()
    schedule = questionary.text(t('cron_add_prompt_schedule')).ask()
    comment = questionary.text(t('cron_add_prompt_comment')).ask()

    if command and schedule:
        job = cron.new(command=command, comment=comment)
        job.setall(schedule)
        cron.write()
        console.print(f"[green]{t('cron_add_success')}[/green]")

def remove_job(cron):
    """Removes a cron job."""
    if len(cron) == 0:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(t('cron_no_jobs'))
        return

    job_choices = {f"{job.slices} - {job.command} ({job.comment})": job for job in cron}
    
    selected_job_str = questionary.select(
        t('cron_remove_prompt'),
        choices=list(job_choices.keys())
    ).ask()

    if selected_job_str and questionary.confirm(t('cron_remove_confirm')).ask():
        job_to_remove = job_choices[selected_job_str]
        cron.remove(job_to_remove)
        cron.write()
        console.print(f"[green]{t('cron_remove_success')}[/green]")

def show_cron_manager():
    """Main function for the cron job manager."""
    cron = get_cron()
    if not cron:
        questionary.press_any_key_to_continue().ask()
        return

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('cron_title')}[/bold blue]"))
        
        choice = questionary.select(
            t('cron_prompt_action'),
            choices=[
                t('cron_menu_list'),
                t('cron_menu_add'),
                t('cron_menu_remove'),
                t('cron_menu_back')
            ]
        ).ask()

        if choice == t('cron_menu_list'):
            list_jobs(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('cron_menu_add'):
            add_job(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('cron_menu_remove'):
            remove_job(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('cron_menu_back') or choice is None:
            break 