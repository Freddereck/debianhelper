import os
import getpass
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from crontab import CronTab
from app.translations import t

console = Console()

def get_cron_for_user():
    """Gets the CronTab for the current user, ensuring we can operate."""
    try:
        # CronTab(user=True) targets the current user's crontab.
        # When running with sudo, this will be root's crontab unless we specify the user.
        # For simplicity and security, we'll manage the crontab of the user running the script (root if sudo'd).
        user_cron = CronTab(user=getpass.getuser())
        return user_cron
    except (IOError, FileNotFoundError) as e:
        console.print(f"[bold red]{t('cron_error_permission', error=e)}[/bold red]")
        console.print(t('cron_permission_hint'))
        return None
    except Exception as e:
        console.print(f"[bold red]{t('cron_error_generic', error=e)}[/bold red]")
        return None

def list_cron_jobs(cron):
    """Lists all cron jobs with improved readability."""
    os.system('cls' if os.name == 'nt' else 'clear')
    user = getpass.getuser()
    console.print(Panel(t('cron_current_jobs', user=user), border_style="green"))

    if not cron:
        console.print(t('cron_no_jobs'))
        return

    table = Table(title=t('cron_job_list_title'))
    table.add_column(t('cron_col_schedule'), style="cyan", no_wrap=True)
    table.add_column(t('cron_col_command'), style="magenta")
    table.add_column(t('cron_col_comment'), style="green")

    for job in cron:
        table.add_row(str(job.slices), job.command, job.comment)

    console.print(table)

def add_cron_job_wizard(cron):
    """A wizard-like interface for adding a new cron job."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('cron_add_title'), border_style="blue"))

    # 1. Get the core command
    command = questionary.text(t('cron_add_prompt_command')).ask()
    if not command:
        console.print(f"[red]{t('operation_cancelled')}[/red]"); return

    # 2. Get the schedule using presets or manual entry
    schedule_choice = questionary.select(
        t('cron_schedule_prompt'),
        choices=[
            t('cron_schedule_minute'), t('cron_schedule_hour'), t('cron_schedule_day'),
            t('cron_schedule_week'), t('cron_schedule_month'), t('cron_schedule_reboot'),
            t('cron_schedule_manual')
        ]).ask()

    schedule = ""
    if schedule_choice == t('cron_schedule_minute'): schedule = '*/1 * * * *'
    elif schedule_choice == t('cron_schedule_hour'): schedule = '0 * * * *'
    elif schedule_choice == t('cron_schedule_day'): schedule = '0 0 * * *'
    elif schedule_choice == t('cron_schedule_week'): schedule = '0 0 * * 0'
    elif schedule_choice == t('cron_schedule_month'): schedule = '0 0 1 * *'
    elif schedule_choice == t('cron_schedule_reboot'): schedule = '@reboot'
    elif schedule_choice == t('cron_schedule_manual'):
        schedule = questionary.text(t('cron_add_prompt_schedule')).ask()
    
    if not schedule:
        console.print(f"[red]{t('operation_cancelled')}[/red]"); return

    # 3. Handle command output
    output_choice = questionary.select(
        t('cron_output_prompt'),
        choices=[
            t('cron_output_log'), t('cron_output_screen'),
            t('cron_output_email'), t('cron_output_silent')
        ]).ask()

    final_command = command
    comment = questionary.text(t('cron_add_prompt_comment')).ask()

    if output_choice == t('cron_output_log'):
        default_log_path = f"/var/log/{command.split()[0].lower()}.log"
        log_file = questionary.text(t('cron_log_path_prompt'), default=default_log_path).ask()
        if not log_file: console.print(f"[red]{t('operation_cancelled')}[/red]"); return
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if not os.path.isdir(log_dir):
            console.print(t('cron_creating_log_dir', path=log_dir))
            run_command(f"sudo mkdir -p {log_dir} && sudo touch {log_file} && sudo chown {getpass.getuser()} {log_file}")
        final_command = f"{command} >> {log_file} 2>&1"
        if not comment: comment = f"Output to {log_file}"

    elif output_choice == t('cron_output_screen'):
        session_name = questionary.text(t('cron_screen_name_prompt'), default=f"cron_{command.split()[0]}").ask()
        if not session_name: console.print(f"[red]{t('operation_cancelled')}[/red]"); return
        final_command = f"/usr/bin/screen -dmS {session_name} {command}"
        console.print(f"[yellow]{t('cron_screen_warning')}[/yellow]")
        if not comment: comment = f"Runs in screen session '{session_name}'"

    elif output_choice == t('cron_output_silent'):
        final_command = f"{command} >/dev/null 2>&1"
        if not comment: comment = "Silent execution"
        
    # Email is the default behavior, so no command modification is needed.

    # 4. Create and save the job
    try:
        job = cron.new(command=final_command, comment=comment)
        if schedule == '@reboot':
            job.setall(schedule)
        else:
            job.setall(schedule)
        
        if cron.is_valid():
            cron.write()
            console.print(f"\n[bold green]{t('cron_add_success')}[/bold green]")
            console.print(f"{t('cron_col_schedule')}: {schedule}")
            console.print(f"{t('cron_col_command')}: {final_command}")
            console.print(f"{t('cron_col_comment')}: {comment}")
        else:
            console.print(f"[bold red]{t('cron_invalid_schedule')}[/bold red]")

    except Exception as e:
        console.print(f"[bold red]{t('cron_write_failed', error=e)}[/bold red]")


def remove_cron_job(cron):
    """Removes a cron job from a list of choices."""
    if not cron:
        console.print(t('cron_no_jobs')); return

    job_choices = [f"'{job.comment}' | {job.slices} | {job.command}" for job in cron]
    
    selected_job_str = questionary.select(
        t('cron_remove_prompt'),
        choices=job_choices
    ).ask()

    if selected_job_str:
        # Find the job object that corresponds to the string
        selected_job = next((job for job in cron if f"'{job.comment}' | {job.slices} | {job.command}" == selected_job_str), None)
        if selected_job and questionary.confirm(t('cron_remove_confirm')).ask():
            cron.remove(selected_job)
            cron.write()
            console.print(f"[green]{t('cron_remove_success')}[/green]")

def show_cron_manager():
    """Main menu for the 'Smart' Cron Job Manager."""
    cron = get_cron_for_user()
    if cron is None:
        questionary.press_any_key_to_continue().ask()
        return

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('cron_title')}[/bold blue]"))
        
        choice = questionary.select(
            t('cron_prompt_action'),
            choices=[
                t('cron_menu_list'),
                t('cron_menu_add_wizard'),
                t('cron_menu_remove'),
                t('back_to_main_menu')
            ]
        ).ask()

        if choice == t('cron_menu_list'):
            list_cron_jobs(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('cron_menu_add_wizard'):
            add_cron_job_wizard(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('cron_menu_remove'):
            remove_cron_job(cron)
            questionary.press_any_key_to_continue().ask()
        elif choice == t('back_to_main_menu') or choice is None:
            break 