import os
import getpass
import time
import questionary
from crontab import CronTab
from rich.console import Console
from rich.panel import Panel

console = Console()

def show_cron_manager():
    """Manages user-specific cron jobs."""
    if os.name == 'nt':
        console.print("[yellow]Cron is not available on Windows.[/yellow]")
        time.sleep(2)
        return
        
    try:
        # FIX: Use user=True which is a more robust way to get current user's crontab
        cron = CronTab(user=True)
    except (IOError, FileNotFoundError):
        console.print("[red]Could not open crontab. Is cron installed and have you used it before?[/red]")
        time.sleep(3)
        return

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel("[bold cyan]Cron Job Manager[/bold cyan]"))
        jobs = list(cron)
        job_choices = [f"[{'✅' if job.is_enabled() else '❌'}] {job}" for job in jobs]
        
        action = questionary.select(
            "Select a job to manage or an action:",
            choices=job_choices + ["Add New Job", "Back"],
            pointer="👉"
        ).ask()

        if action == "Back" or action is None:
            break
        elif action == "Add New Job":
            command = questionary.text("Enter command for the new job:").ask()
            if not command: continue
            schedule = questionary.text("Enter schedule (e.g., '*/5 * * * *'):").ask()
            if not schedule: continue
            
            new_job = cron.new(command=command)
            if new_job.setall(schedule):
                cron.write()
                console.print(f"[green]Job '{command}' added.[/green]")
            else:
                console.print("[red]Invalid schedule format.[/red]")
            time.sleep(1)
        else:
            job_index = job_choices.index(action)
            job = jobs[job_index]
            job_action = questionary.select(
                f"Action for job: {job}",
                choices=["Enable/Disable", "Delete", "Edit Command", "Edit Schedule", "Cancel"],
                pointer="👉"
            ).ask()
            
            if job_action == "Cancel":
                continue

            if job_action == "Enable/Disable":
                job.enable(not job.is_enabled())
            elif job_action == "Delete":
                cron.remove(job)
            elif job_action == "Edit Command":
                job.command = questionary.text("New command:", default=job.command).ask()
            elif job_action == "Edit Schedule":
                new_schedule = questionary.text("New schedule:", default=str(job.slices)).ask()
                if not job.setall(new_schedule):
                    console.print("[red]Invalid schedule format. No changes made.[/red]")
                    time.sleep(2)
                    continue
            
            cron.write()
            console.print("[green]Crontab updated.[/green]")
            time.sleep(1) 