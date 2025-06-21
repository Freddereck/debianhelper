import pwd
import subprocess
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import os

console = Console()

def run_sudo_command(command):
    """Executes a command with sudo, returning success status and output."""
    try:
        # We need to prepend 'sudo' to the command
        full_command = ['sudo'] + command
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True, result.stdout.strip()
    except FileNotFoundError:
        # This can happen if sudo is not installed, though unlikely on target systems
        return False, "The 'sudo' command was not found."
    except subprocess.CalledProcessError as e:
        # This captures errors from the command itself
        return False, e.stderr.strip()

def get_system_users():
    """Retrieves a list of non-system users (UID >= 1000)."""
    users = []
    for p in pwd.getpwall():
        # Standard convention: UIDs >= 1000 are for regular users
        if p.pw_uid >= 1000 and 'nologin' not in p.pw_shell:
            users.append(p)
    return users

def add_user():
    """Handler for adding a new system user."""
    console.print(Panel("Add New System User", style="green", title_align="left"))
    
    username = questionary.text(
        "Enter the username for the new user:",
        validate=lambda text: True if len(text) > 0 and text.isidentifier() else "Invalid username."
    ).ask()
    if not username:
        return

    # Ask for shell type
    shell = questionary.select(
        "Choose the user's shell:",
        choices=['/bin/bash', '/bin/sh', '/usr/sbin/nologin']
    ).ask()
    if not shell:
        return

    # Command to add user
    command = ['useradd', username, '-m', '-s', shell]
    
    # Optionally add to supplementary groups
    groups_str = questionary.text("Enter supplementary groups (comma-separated, e.g., sudo,www-data):").ask()
    if groups_str:
        command.extend(['-G', groups_str])

    console.print(f"Attempting to create user '{username}'...", style="yellow")
    success, output = run_sudo_command(command)

    if success:
        console.print(f"[bold green]User '{username}' created successfully![/bold green]")
        console.print("Please set the password for the new user using the 'passwd' command.")
        console.print(f"Example: [cyan]sudo passwd {username}[/cyan]")
    else:
        console.print(f"[bold red]Error creating user: {output}[/bold red]")
    
    questionary.press_any_key_to_continue().ask()


def delete_user(user_to_delete):
    """Handler for deleting a system user."""
    console.print(Panel(f"Delete User: {user_to_delete.pw_name}", style="red", title_align="left"))
    
    confirm = questionary.confirm(
        f"Are you sure you want to permanently delete the user '{user_to_delete.pw_name}'?\nThis action cannot be undone.",
        default=False
    ).ask()

    if not confirm:
        console.print("User deletion cancelled.", style="yellow")
        return
        
    remove_home = questionary.confirm(
        f"Do you also want to delete the home directory '{user_to_delete.pw_dir}'?",
        default=False
    ).ask()

    command = ['userdel']
    if remove_home:
        command.append('-r')
    command.append(user_to_delete.pw_name)

    console.print(f"Attempting to delete user '{user_to_delete.pw_name}'...", style="yellow")
    success, output = run_sudo_command(command)

    if success:
        console.print(f"[bold green]User '{user_to_delete.pw_name}' deleted successfully![/bold green]")
    else:
        console.print(f"[bold red]Error deleting user: {output}[/bold red]")
        
    questionary.press_any_key_to_continue().ask()

def show_user_manager():
    """Main function for the User Manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(t('user_manager_title'), style="bold blue"))
        
        choices = [
            t('user_menu_list'),
        ]
        if users:
            choices.extend([questionary.Separator(), "Delete Existing User"])
        choices.extend([questionary.Separator(), "Back to Main Menu"])
        
        action = questionary.select(
            "What would you like to do?",
            choices=choices,
            pointer="👉"
        ).ask()

        if action is None or action == "Back to Main Menu":
            break
        elif action == "Add New User":
            add_user()
        elif action == "Delete Existing User":
            if not users:
                continue # Should not happen due to choice logic but good for safety
            
            user_to_delete_name = questionary.select(
                "Which user do you want to delete?",
                choices=list(user_map.keys())
            ).ask()
            
            if user_to_delete_name:
                delete_user(user_map[user_to_delete_name]) 