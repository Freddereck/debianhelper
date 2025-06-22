import os
import questionary
from rich.console import Console
from datetime import datetime

from app.translations import t
from app.utils import run_command, is_tool_installed, run_command_for_output

console = Console()

def show_backup_manager():
    """Displays the main backup management menu."""
    console.clear()
    console.print(f"[bold blue underline]{t('backup_manager_title')}[/bold blue underline]\n")

    menu_options = {
        t('backup_menu_create'): create_backup,
        t('backup_menu_list'): list_backups,
        t('back_to_main_menu'): "exit"
    }

    while True:
        action = questionary.select(
            t('backup_menu_prompt'),
            choices=list(menu_options.keys())
        ).ask()

        if action is None or menu_options.get(action) == "exit":
            break
        
        selected_function = menu_options.get(action)
        if selected_function:
            selected_function()
            questionary.press_any_key_to_continue(t('press_any_key')).ask()
            console.clear()
            console.print(f"[bold blue underline]{t('backup_manager_title')}[/bold blue underline]\n")

def create_backup():
    """Guides the user through creating a new backup."""
    backup_type = questionary.select(
        t('backup_type_prompt'),
        choices=[t('backup_type_files'), t('backup_type_mysql'), t('back')]
    ).ask()

    if backup_type == t('backup_type_files'):
        backup_files()
    elif backup_type == t('backup_type_mysql'):
        backup_mysql()
    else:
        return

def get_backup_dir():
    """Gets and creates the backup directory."""
    default_dir = "/var/backups/server_panel"
    backup_dir = questionary.text(t('backup_dir_prompt'), default=default_dir).ask()
    if not backup_dir:
        return None
    
    if not os.path.exists(backup_dir):
        console.print(f"[cyan]{t('creating_backup_dir', dir=backup_dir)}...[/cyan]")
        run_command(f"sudo mkdir -p {backup_dir}")
        run_command(f"sudo chown $USER:$USER {backup_dir}") # Own it for easy access
    
    return backup_dir

def backup_files():
    """Handles backing up files and directories."""
    source_path = questionary.text(t('backup_source_path_prompt')).ask()
    if not source_path or not os.path.exists(source_path):
        console.print(f"[red]{t('invalid_source_path')}[/red]")
        return
        
    backup_dir = get_backup_dir()
    if not backup_dir:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    source_name = os.path.basename(os.path.normpath(source_path))
    dest_file = f"{backup_dir}/{source_name}_{timestamp}.tar.gz"

    console.print(f"[cyan]{t('creating_archive', dest=dest_file)}...[/cyan]")
    try:
        run_command(f"sudo tar -czf {dest_file} -C {os.path.dirname(source_path)} {source_name}")
        console.print(f"[bold green]{t('backup_created_successfully', path=dest_file)}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]{t('error_creating_backup', error=e)}[/bold red]")

def backup_mysql():
    """Handles backing up MySQL databases."""
    if not is_tool_installed('mysqldump'):
        console.print(f"[red]{t('mysqldump_not_found')}[/red]")
        return

    try:
        # This is a simplification. Real-world usage requires credentials.
        # A better way is to check for ~/.my.cnf
        databases_str = run_command_for_output("mysql -e 'show databases;' -s --skip-column-names")
        databases = [db for db in databases_str.split('\\n') if db and db not in ('information_schema', 'performance_schema', 'mysql')]
    except Exception as e:
        console.print(f"[red]{t('error_listing_databases', error=e)}[/red]")
        console.print(f"[yellow]{t('mysql_auth_tip')}[/yellow]")
        return

    if not databases:
        console.print(f"[yellow]{t('no_databases_found')}[/yellow]")
        return

    databases.insert(0, t('all_databases'))
    selected_db = questionary.select(t('select_database_to_backup'), choices=databases).ask()

    if not selected_db:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return

    backup_dir = get_backup_dir()
    if not backup_dir:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    db_name = "all-databases" if selected_db == t('all_databases') else selected_db
    dest_file = f"{backup_dir}/db_{db_name}_{timestamp}.sql.gz"

    console.print(f"[cyan]{t('creating_db_dump', dest=dest_file)}...[/cyan]")
    try:
        dump_cmd = "mysqldump"
        if selected_db == t('all_databases'):
            dump_cmd += " --all-databases"
        else:
            dump_cmd += f" --databases {selected_db}"
            
        run_command(f"{dump_cmd} | gzip > {dest_file}")
        console.print(f"[bold green]{t('backup_created_successfully', path=dest_file)}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]{t('error_creating_backup', error=e)}[/bold red]")


def list_backups():
    """Lists existing backups."""
    default_dir = "/var/backups/server_panel"
    backup_dir = questionary.text(t('backup_dir_prompt_list'), default=default_dir).ask()
    
    if not backup_dir or not os.path.exists(backup_dir):
        console.print(f"[red]{t('backup_dir_not_found', dir=backup_dir)}[/red]")
        return
        
    try:
        files = os.listdir(backup_dir)
        if not files:
            console.print(f"[yellow]{t('no_backups_found', dir=backup_dir)}[/yellow]")
            return
            
        console.print(f"\\n[bold underline]{t('backups_in_dir', dir=backup_dir)}:[/bold underline]")
        for f in sorted(files):
            console.print(f"- {f}")
            
    except Exception as e:
        console.print(f"[red]{t('error_listing_backups', error=e)}[/red]") 