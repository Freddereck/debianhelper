import os
import re
import questionary
import stat
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.utils import run_command, run_command_live
from app.translations import t

console = Console()

# --- Quick Checks ---

def check_ssh_config():
    """Checks for common insecure SSH configurations."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold yellow]{t('ssh_check_title')}[/bold yellow]"))
    
    config_path = "/etc/ssh/sshd_config"
    try:
        with open(config_path, 'r') as f:
            config = f.read()
    except FileNotFoundError:
        console.print(f"[red]Could not find sshd_config at {config_path}[/red]")
        questionary.press_any_key_to_continue().ask()
        return

    table = Table(show_header=False, box=None)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="white")
    
    # Check PermitRootLogin
    root_login = re.search(r"^\s*PermitRootLogin\s+(yes)", config, re.MULTILINE)
    if root_login:
        table.add_row(t('ssh_check_root_login'), f"[bold red]{t('ssh_check_insecure')}[/bold red]")
    else:
        table.add_row(t('ssh_check_root_login'), f"[green]{t('ssh_check_secure')}[/green]")

    # Check PasswordAuthentication
    pass_auth = re.search(r"^\s*PasswordAuthentication\s+yes", config, re.MULTILINE)
    if pass_auth:
        table.add_row(t('ssh_check_pass_auth'), f"[bold red]{t('ssh_check_insecure')}[/bold red]")
    else:
        table.add_row(t('ssh_check_pass_auth'), f"[green]{t('ssh_check_secure')}[/green]")

    console.print(table)
    if root_login or pass_auth:
        console.print(f"\n[yellow]{t('ssh_recommendation')}[/yellow]")

    questionary.press_any_key_to_continue().ask()

def check_empty_passwords():
    """Checks for users with empty passwords in /etc/shadow."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold yellow]{t('empty_pass_title')}[/bold yellow]"))
    
    # This command is safer as it doesn't require sudo if the user has read access to shadow via group
    output = run_command("cat /etc/shadow | awk -F: '($2 == \"\") {print $1}'")
    
    if output:
        console.print(f"[bold red]{t('empty_pass_found')}[/bold red]")
        table = Table(title=t('empty_pass_col_user'))
        table.add_column("User", style="red")
        for user in output.strip().split('\n'):
            table.add_row(user)
        console.print(table)
    else:
        console.print(f"[green]{t('empty_pass_not_found')}[/green]")
        
    questionary.press_any_key_to_continue().ask()

def check_critical_permissions():
    """Checks permissions of critical system files."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold yellow]{t('permissions_title')}[/bold yellow]"))
    
    files_to_check = {
        "/etc/passwd": "644",
        "/etc/shadow": "640",
        "/etc/sudoers": "440",
        "/etc/group": "644",
        "/etc/gshadow": "640"
    }

    table = Table()
    table.add_column(t('permissions_col_file'), style="cyan")
    table.add_column(t('permissions_col_expected'), style="yellow")
    table.add_column(t('permissions_col_actual'), style="magenta")
    table.add_column(t('permissions_col_status'), style="white")

    for f, expected_perm in files_to_check.items():
        try:
            current_perm = oct(stat.S_IMODE(os.stat(f).st_mode))[-3:]
            if current_perm == expected_perm:
                status = f"[green]{t('permissions_status_ok')}[/green]"
            else:
                status = f"[bold red]{t('permissions_status_warning')}[/bold red]"
            table.add_row(f, expected_perm, current_perm, status)
        except FileNotFoundError:
            table.add_row(f, expected_perm, "Not Found", "[bold red]ERROR[/bold red]")
            
    console.print(table)
    questionary.press_any_key_to_continue().ask()

# --- Network Audit ---

def check_fail2ban():
    """Checks the status of Fail2Ban and lists banned IPs."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold yellow]{t('fail2ban_title')}[/bold yellow]"))
    console.print(t('fail2ban_checking'))
    
    status = run_command("sudo systemctl is-active fail2ban")
    if status == "active":
        console.print(f"[green]{t('fail2ban_active')}[/green]")
        status_all = run_command("sudo fail2ban-client status")
        jail_list_str = re.search(r"Jail list:\s*(.*)", status_all)
        if jail_list_str:
            jails = [j.strip() for j in jail_list_str.group(1).split(',')]
            table = Table(title=t('fail2ban_table_title'))
            table.add_column(t('fail2ban_col_jail'), style="cyan")
            table.add_column(t('fail2ban_col_banned'), style="magenta")
            for jail in jails:
                banned_ips = run_command(f"sudo fail2ban-client status {jail} | grep 'Banned IP list' | sed 's/.*://'")
                table.add_row(jail, banned_ips.strip() if banned_ips else "0")
            console.print(table)
        else:
            console.print(f"[yellow]{t('fail2ban_no_jails')}[/yellow]")
    else:
        console.print(f"[red]{t('fail2ban_inactive')}[/red]")
    questionary.press_any_key_to_continue().ask()

def check_listening_ports():
    """Checks for listening network ports using ss."""
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel(f"[bold cyan]{t('ports_title')}[/bold cyan]"))
    console.print(t('ports_fetching'))
    
    ports_raw = run_command("sudo ss -tulpn")
    if ports_raw:
        table = Table(title=t('ports_table_title'))
        headers = ports_raw.strip().split('\n')[0].split()
        # Custom headers for better readability and translation
        translated_headers = [
            t('ports_col_proto'), t('ports_col_recv'), t('ports_col_send'),
            t('ports_col_local'), t('ports_col_peer'), t('ports_col_user'), t('ports_col_program')
        ]
        for header in translated_headers[:len(headers)]: # Match headers to available columns
            table.add_column(header)
        
        for line in ports_raw.strip().split('\n')[1:]:
            parts = line.split(maxsplit=len(headers)-1)
            table.add_row(*parts)
        console.print(table)
    questionary.press_any_key_to_continue().ask()

# --- Deep Audit ---

def run_lynis_audit():
    """Runs the Lynis security audit."""
    if not is_lynis_installed():
        install_lynis()

    if is_lynis_installed():
        console.print(Panel(t('security_lynis_running_panel')))
        with console.status(t('security_lynis_running_status')):
            # We want to see the output, so show_output=True, but we handle the messages manually
            run_command("sudo lynis audit system", show_output=True, ignore_errors=True)
        console.print(f"\n[green]{t('security_lynis_completed')}[/green]")
    else:
        console.print(f"[red]{t('security_lynis_install_failed')}[/red]")
    
    questionary.press_any_key_to_continue().ask()

# --- Main Menus ---

def show_quick_checks_menu():
    """Menu for quick, targeted security checks."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold cyan]{t('quick_check_title')}[/bold cyan]"))
        choice = questionary.select(
            t('security_prompt'),
            choices=[
                t('quick_check_ssh'),
                t('quick_check_passwords'),
                t('quick_check_permissions'),
                t('security_menu_back')
            ]
        ).ask()
        
        if choice == t('quick_check_ssh'):
            check_ssh_config()
        elif choice == t('quick_check_passwords'):
            check_empty_passwords()
        elif choice == t('quick_check_permissions'):
            check_critical_permissions()
        elif choice == t('security_menu_back') or choice is None:
            break

def show_network_audit_menu():
    """Menu for network-related security checks."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold cyan]{t('security_menu_network')}[/bold cyan]"))
        choice = questionary.select(
            t('security_prompt'),
            choices=[
                t('security_menu_fail2ban'),
                t('security_menu_ports'),
                t('security_menu_back')
            ]
        ).ask()

        if choice == t('security_menu_fail2ban'):
            check_fail2ban()
        elif choice == t('security_menu_ports'):
            check_listening_ports()
        elif choice == t('security_menu_back') or choice is None:
            break

def run_security_audit():
    """Main menu for the security and network audit module."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold cyan]{t('security_title')}[/bold cyan]"))
        
        choice = questionary.select(
            t('security_prompt'),
            choices=[
                t('security_menu_quick'),
                t('security_menu_network'),
                t('security_menu_deep'),
                t('security_menu_back')
            ]
        ).ask()

        if choice == t('security_menu_quick'):
            show_quick_checks_menu()
        elif choice == t('security_menu_network'):
            show_network_audit_menu()
        elif choice == t('security_menu_deep'):
            run_lynis_audit()
        elif choice == t('security_menu_back') or choice is None:
            break 