import os
import glob
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from app.translations import t
from app.utils import run_command
import platform

console = Console()

# A map of common log files with user-friendly names and descriptions.
# The `t()` function is used with default values for easy localization.
LOG_FILES_MAP = [
    # System & Security
    {'name': t('log_name_system', default='System Log'), 'path': '/var/log/syslog', 'desc': t('log_desc_system', default='Core system log, contains messages from the kernel and services.')},
    {'name': t('log_name_auth', default='Auth Log'), 'path': '/var/log/auth.log', 'desc': t('log_desc_auth', default='Authentication logs, including logins and authorization attempts.')},
    {'name': t('log_name_kernel', default='Kernel Log'), 'path': '/var/log/kern.log', 'desc': t('log_desc_kernel', default='Linux kernel logs.')},
    {'name': t('log_name_dmesg', default='Boot (dmesg)'), 'path': '/var/log/dmesg', 'desc': t('log_desc_dmesg', default='Contains messages displayed during system boot.')},
    {'name': t('log_name_daemon', default='Daemon Log'), 'path': '/var/log/daemon.log', 'desc': t('log_desc_daemon', default='Logs from system services (daemons).')},
    {'name': t('log_name_messages', default='Messages'), 'path': '/var/log/messages', 'desc': t('log_desc_messages', default='General messages from services and applications.')},
    {'name': t('log_name_user', default='User Log'), 'path': '/var/log/user.log', 'desc': t('log_desc_user', default='User logs not related to authentication.')},
    {'name': t('log_name_fail2ban', default='Fail2Ban'), 'path': '/var/log/fail2ban.log', 'desc': t('log_desc_fail2ban', default='IP bans and other actions from Fail2Ban.')},
    {'name': t('log_name_ufw', default='UFW Firewall'), 'path': '/var/log/ufw.log', 'desc': t('log_desc_ufw', default='UFW firewall allowed and denied connections.')},
    {'name': t('log_name_dpkg', default='DPKG Log'), 'path': '/var/log/dpkg.log', 'desc': t('log_desc_dpkg', default='Installation and removal of packages.')},
    
    # Web Servers
    {'name': t('log_name_nginx_access', default='Nginx Access'), 'path': '/var/log/nginx/access.log', 'desc': t('log_desc_nginx_access', default='Records all requests to the Nginx server.')},
    {'name': t('log_name_nginx_error', default='Nginx Error'), 'path': '/var/log/nginx/error.log', 'desc': t('log_desc_nginx_error', default='Nginx errors, including script errors.')},
    {'name': t('log_name_apache_access', default='Apache Access'), 'path': '/var/log/apache2/access.log', 'desc': t('log_desc_apache_access', default='Records all requests to the Apache server.')},
    {'name': t('log_name_apache_error', default='Apache Error'), 'path': '/var/log/apache2/error.log', 'desc': t('log_desc_apache_error', default='Apache errors and diagnostic information.')},

    # Databases
    {'name': t('log_name_mysql_error', default='MySQL Errors'), 'path': '/var/log/mysql/error.log', 'desc': t('log_desc_mysql_error', default='MySQL server startup, shutdown, and error messages.')},
    
    # Other services
    {'name': t('log_name_cron', default='Cron Jobs'), 'path': '/var/log/cron.log', 'desc': t('log_desc_cron', default='Logs of cron job executions (if enabled).')},
    
    # --- Other common system logs ---
    {'name': t('log_name_3xui_banned', default='3X-UI Banned IPs'), 'path': '/var/log/3xipl-banned.log', 'desc': t('log_desc_3xui_banned', default='Log of IPs banned by 3X-UI panel.')},
    {'name': t('log_name_3xui_access', default='3X-UI Access'), 'path': '/var/log/3xipl-ap.log', 'desc': t('log_desc_3xui_access', default='Access or API logs for the 3X-UI panel.')},
    {'name': t('log_name_3xui_general', default='3X-UI General'), 'path': '/var/log/3xipl.log', 'desc': t('log_desc_3xui_general', default='General logs for the 3X-UI panel.')},
    {'name': t('log_name_cloud_init', default='Cloud-Init'), 'path': '/var/log/cloud-init.log', 'desc': t('log_desc_cloud_init', default='Logs for the cloud-init service during instance boot.')},
    {'name': t('log_name_cloud_init_output', default='Cloud-Init Output'), 'path': '/var/log/cloud-init-output.log', 'desc': t('log_desc_cloud_init_output', default='Output from user-data scripts run by cloud-init.')},
    {'name': t('log_name_alternatives', default='Alternatives Log'), 'path': '/var/log/alternatives.log', 'desc': t('log_desc_alternatives', default='Logs from the update-alternatives command.')},
    {'name': t('log_name_fontconfig', default='Fontconfig Log'), 'path': '/var/log/fontconfig.log', 'desc': t('log_desc_fontconfig', default='Logs related to font configuration and caching.')},
    {'name': t('log_name_lynis', default='Lynis Audit'), 'path': '/var/log/lynis.log', 'desc': t('log_desc_lynis', default='Log file for the Lynis security auditing tool.')},
]


def get_log_files():
    """
    Dynamically discovers existing log files and maps them to translations.
    On non-Linux systems, it falls back to checking a predefined list.
    """
    if platform.system() != "Linux":
        # Fallback for non-Linux systems like Windows for local testing
        return [log_info for log_info in LOG_FILES_MAP if os.path.exists(log_info['path'])]

    # --- Linux-specific discovery logic ---
    path_to_meta = {log['path']: log for log in LOG_FILES_MAP}
    available_logs = []
    processed_paths = set()

    # 1. Add prioritized logs from our map that actually exist
    for log_info in LOG_FILES_MAP:
        if os.path.exists(log_info['path']) and os.path.isfile(log_info['path']):
            available_logs.append(log_info)
            processed_paths.add(log_info['path'])

    # 2. Discover other log files in common directories
    # Search patterns for common log files
    search_patterns = [
        '/var/log/*.log',
        '/var/log/nginx/*.log',
        '/var/log/apache2/*.log',
        '/var/log/mysql/*.log'
    ]

    for pattern in search_patterns:
        for path in glob.glob(pattern):
            if path not in processed_paths and os.path.isfile(path):
                # This is a newly discovered log file
                available_logs.append({
                    'name': os.path.basename(path),
                    'path': path,
                    'desc': t('log_desc_discovered', default='Discovered log file.')
                })
                processed_paths.add(path)
    
    # 3. Special handling for PostgreSQL due to its versioned naming
    try:
        pg_logs = glob.glob('/var/log/postgresql/postgresql-*-main.log')
        for pg_log in pg_logs:
            if pg_log not in processed_paths:
                available_logs.append({
                    'name': t('log_name_postgresql', default='PostgreSQL'),
                    'path': pg_log,
                    'desc': t('log_desc_postgresql', default=f'PostgreSQL server log ({os.path.basename(pg_log)}).')
                })
    except Exception:
        pass # Ignore errors if glob fails

    return available_logs

def view_log_file(filepath, lines=50):
    """Displays the last N lines of a specific log file, handling permissions and non-existence."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(t('logs_viewing_title', default="Viewing last {lines} lines of: {filepath}", filepath=filepath, lines=lines), border_style="cyan"))

    # Check for file existence first, as direct open() and sudo tail will both fail.
    # This is important because get_log_files() on Linux no longer pre-filters.
    if not os.path.exists(filepath):
        console.print(f"[bold red]{t('logs_error_not_exist', path=filepath)}[/bold red]")
        questionary.press_any_key_to_continue().ask()
        return

    try:
        # First, try to read the file directly. This works for user-accessible logs.
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines_content = f.readlines()[-lines:]
            for line in lines_content:
                console.print(line.strip())

    except PermissionError:
        # If direct access fails, it's likely a protected file. Fallback to sudo tail.
        console.print(f"[yellow]{t('logs_permission_fallback', default='Permission denied. Falling back to using sudo...')}[/yellow]")
        # Use run_command to handle potential errors with sudo itself
        run_command(f"sudo tail -n {lines} {filepath}", show_output=True)

    except FileNotFoundError: # This is a fallback, but os.path.exists should catch it.
        console.print(f"[bold red]{t('logs_error_not_exist', path=filepath)}[/bold red]")

    except Exception as e:
        console.print(f"[bold red]{t('logs_error_unexpected', default='An unexpected error occurred: {error}', error=e)}[/bold red]")

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

        # Create user-friendly choices with descriptions
        choices = [
            questionary.Choice(
                title=f"{log['name']:<18} - {log['desc']}",
                value=log['path']
            ) for log in log_files
        ]
        choices.extend([
            questionary.Separator(),
            questionary.Choice(title=t('logs_menu_custom'), value='custom'),
            questionary.Choice(title=t('logs_menu_back'), value='back')
        ])
        
        log_choice = questionary.select(
            t('logs_prompt_select'),
            choices=choices,
            pointer="👉"
        ).ask()

        if log_choice == 'back' or log_choice is None:
            break
        elif log_choice == 'custom':
            custom_path = questionary.text(t('logs_prompt_custom_path')).ask()
            if custom_path and os.path.exists(custom_path):
                view_log_file(custom_path)
            elif custom_path:
                console.print(t('logs_error_not_exist', path=custom_path))
                questionary.press_any_key_to_continue().ask()
        else:
            # log_choice is the file path from the Choice value
            view_log_file(log_choice) 