import os
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, is_tool_installed, run_command_live
from app.translations import t

console = Console()

# --- Generic Management Functions ---

def service_status(service_name):
    run_command(f"sudo systemctl status {service_name}")

def service_restart(service_name):
    run_command(f"sudo systemctl restart {service_name}", success_message=t('service_restarted_successfully', service=service_name))

def service_reload(service_name):
    run_command(f"sudo systemctl reload {service_name}", success_message=t('service_reloaded_successfully', service=service_name))

def service_uninstall(package_name, non_interactive=False, custom_uninstall_cmd=None):
    if questionary.confirm(t('uninstall_confirm_question', package=package_name)).ask():
        console.print(f"[bold red]{t('uninstalling_package', package=package_name)}...[/bold red]")
        
        if custom_uninstall_cmd:
            command = custom_uninstall_cmd
        else:
            command = f"sudo apt-get purge -y {package_name} && sudo apt-get autoremove -y"
            
        run_command_live(command, f"{package_name}_uninstall.log")
        console.print(f"\n[green]{t('package_uninstalled_successfully', package=package_name)}[/green]")
        questionary.press_any_key_to_continue().ask()

def service_install(package_name, non_interactive=False, custom_install_cmd=None):
    console.print(f"[yellow]{t('installing_package', package=package_name)}...[/yellow]")
    command = custom_install_cmd or f"sudo apt-get update -qq && sudo apt-get install -y {package_name}"
    run_command_live(command, f"{package_name}_install.log")
    console.print(f"\n[green]{t('package_installed_successfully', package=package_name)}[/green]")
    questionary.press_any_key_to_continue().ask()

# --- Specific Management Menus ---

def manage_nginx():
    while True:
        console.clear()
        console.print(Panel(f"[bold green]Nginx {t('management')}[/bold green]", border_style="green"))
        action = questionary.select(t('what_to_do'), choices=[
            t('nginx_menu_status'), t('nginx_menu_test_config'), t('nginx_menu_reload'), 
            t('nginx_menu_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('nginx_menu_status'): service_status('nginx')
        elif action == t('nginx_menu_test_config'): run_command("sudo nginx -t")
        elif action == t('nginx_menu_reload'): service_reload('nginx')
        elif action == t('nginx_menu_restart'): service_restart('nginx')
        elif action == t('uninstall'): service_uninstall('nginx')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_mysql():
    while True:
        console.clear()
        console.print(Panel(f"[bold yellow]MySQL {t('management')}[/bold yellow]", border_style="yellow"))
        action = questionary.select(t('what_to_do'), choices=[
            t('mysql_menu_status'), t('mysql_menu_secure'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('mysql_menu_status'): service_status('mysql')
        elif action == t('mysql_menu_secure'):
            console.print(t('mysql_secure_manual_follow'))
            os.system("sudo mysql_secure_installation")
        elif action == t('uninstall'): 
            service_uninstall("mysql-server mysql-client mysql-common mysql-server-core-* mysql-client-core-*", custom_uninstall_cmd="sudo apt-get purge -y mysql-server mysql-client mysql-common mysql-server-core-* mysql-client-core-* && sudo apt-get autoremove -y && sudo rm -rf /etc/mysql /var/lib/mysql")
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_postgresql():
    while True:
        console.clear()
        console.print(Panel(f"[bold blue]PostgreSQL {t('management')}[/bold blue]", border_style="blue"))
        action = questionary.select(t('what_to_do'), choices=[
            t('service_status'), t('service_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('service_status'): service_status('postgresql')
        elif action == t('service_restart'): service_restart('postgresql')
        elif action == t('uninstall'): service_uninstall('postgresql postgresql-contrib')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_apache():
    while True:
        console.clear()
        console.print(Panel(f"[bold red]Apache2 {t('management')}[/bold red]", border_style="red"))
        action = questionary.select(t('what_to_do'), choices=[
            t('service_status'), t('service_restart'), t('service_reload'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('service_status'): service_status('apache2')
        elif action == t('service_restart'): service_restart('apache2')
        elif action == t('service_reload'): service_reload('apache2')
        elif action == t('uninstall'): service_uninstall('apache2')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_mongodb():
    while True:
        console.clear()
        console.print(Panel(f"[bold green]MongoDB {t('management')}[/bold green]", border_style="dark_green"))
        action = questionary.select(t('what_to_do'), choices=[
            t('service_status'), t('service_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('service_status'): service_status('mongodb')
        elif action == t('service_restart'): service_restart('mongodb')
        elif action == t('uninstall'): service_uninstall('mongodb')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_redis():
    while True:
        console.clear()
        console.print(Panel(f"[bold red]Redis {t('management')}[/bold red]", border_style="red"))
        action = questionary.select(t('what_to_do'), choices=[
            t('service_status'), t('service_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('service_status'): service_status('redis-server')
        elif action == t('service_restart'): service_restart('redis-server')
        elif action == t('uninstall'): service_uninstall('redis-server')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_certbot():
    while True:
        console.clear()
        console.print(Panel(f"[bold yellow]Certbot (Let's Encrypt){t('management')}[/bold yellow]", border_style="yellow"))
        
        # Check for nginx dependency
        if not is_tool_installed('nginx'):
            console.print(f"[bold red]{t('certbot_nginx_required')}[/bold red]")
            questionary.press_any_key_to_continue().ask()
            break

        action = questionary.select(t('what_to_do'), choices=[
            t('certbot_menu_get_cert'), t('certbot_menu_test_renewal'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('certbot_menu_get_cert'):
            console.print(f"[cyan]{t('certbot_get_cert_instructions')}[/cyan]")
            os.system("sudo certbot --nginx")
            questionary.press_any_key_to_continue().ask()
        elif action == t('certbot_menu_test_renewal'):
            console.print(f"[cyan]{t('certbot_testing_renewal')}...[/cyan]")
            run_command("sudo certbot renew --dry-run")
            questionary.press_any_key_to_continue().ask()
        elif action == t('uninstall'): 
            service_uninstall('certbot python3-certbot-nginx')

def install_phpmyadmin_managed(package_name):
    console.print(Panel(f"[bold magenta]{t('pma_installer_title')}[/bold magenta]"))

    # 1. Check dependencies
    nginx_ok = is_tool_installed('nginx')
    php_fpm_ok = is_tool_installed('php-fpm')
    
    if not (nginx_ok and php_fpm_ok):
        console.print(f"[bold red]{t('pma_error_deps_met')}[/bold red]")
        if not nginx_ok: console.print(t('pma_error_no_nginx'))
        if not php_fpm_ok: console.print(t('pma_error_no_php'))
        console.print(f"\n{t('pma_error_deps_instructions')}")
        questionary.press_any_key_to_continue().ask()
        return

    # 2. Install packages
    php_deps = "php-fpm php-mysql php-mbstring php-zip php-gd php-json php-curl"
    console.print(f"[yellow]{t('pma_installing', php_deps=php_deps)}[/yellow]")
    run_command_live(f"sudo apt-get update -qq && sudo apt-get install -y phpmyadmin {php_deps}", "pma_install.log")

    # 3. Post-install instructions
    pma_path = "/usr/share/phpmyadmin"
    web_root = "/var/www/html"
    symlink_path = f"{web_root}/phpmyadmin"

    console.print(f"\n[green]{t('pma_install_finished')}[/green]")
    console.print(t('pma_info_configure_nginx'))
    
    if not os.path.exists(symlink_path):
        run_command(f"sudo ln -s {pma_path} {symlink_path}")

    console.print(f"\n[bold yellow]{t('pma_info_action_required')}[/bold yellow]")
    # ... (show nginx config snippet)
    questionary.press_any_key_to_continue().ask()
    
def manage_phpmyadmin():
    service_uninstall("phpmyadmin")

def install_3x_ui(package_name):
    # Name is passed for consistency but not used
    command = "bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)"
    console.print(f"[yellow]{t('installing_package', package='3X-UI')}...[/yellow]")
    console.print(f"[cyan]{t('running_external_script')}[/cyan]")
    # Use os.system because run_command_live can't handle this type of command string
    os.system(command) 
    console.print(f"\n[green]{t('package_installed_successfully', package='3X-UI')}[/green]")
    questionary.press_any_key_to_continue().ask()

def manage_3x_ui():
    # The x-ui tool is interactive itself
    console.print(f"[cyan]{t('launching_interactive_tool', tool='x-ui')}...[/cyan]")
    os.system("x-ui")
    questionary.press_any_key_to_continue(t('press_any_key_after_exit')).ask()

# --- Main Software Manager ---

SOFTWARE_CATALOG = {
    "Nginx": {"check": "nginx", "install": service_install, "manage": manage_nginx, "package_name": "nginx"},
    "Apache2": {"check": "apache2ctl", "install": service_install, "manage": manage_apache, "package_name": "apache2"},
    "MySQL": {"check": "mysql", "install": service_install, "manage": manage_mysql, "package_name": "mysql-server"},
    "PostgreSQL": {"check": "psql", "install": service_install, "manage": manage_postgresql, "package_name": "postgresql postgresql-contrib"},
    "MongoDB": {"check": "mongod", "install": service_install, "manage": manage_mongodb, "package_name": "mongodb"},
    "Redis": {"check": "redis-server", "install": service_install, "manage": manage_redis, "package_name": "redis-server"},
    "PHPMyAdmin": {"check": "/usr/share/phpmyadmin", "install": install_phpmyadmin_managed, "manage": manage_phpmyadmin, "package_name": "phpmyadmin"},
    "Certbot": {"check": "certbot", "install": service_install, "manage": manage_certbot, "package_name": "certbot python3-certbot-nginx"},
    "3X-UI": {"check": "/usr/local/bin/x-ui", "install": install_3x_ui, "manage": manage_3x_ui, "package_name": "3x-ui"},
    # More software will be added here
}

def show_software_manager():
    """Main menu for the Software Manager."""
    while True:
        console.clear()
        console.print(Panel(f"[bold blue]{t('software_manager_title')}[/bold blue]", border_style="blue"))
        
        choices = []
        for name, software in SOFTWARE_CATALOG.items():
            check_path = software["check"]
            # Check if it's a path or a command
            if "/" in check_path:
                installed = os.path.exists(check_path)
            else:
                installed = is_tool_installed(check_path)
            
            if installed:
                choices.append(f"{t('manage')} {name}")
            else:
                choices.append(f"{t('install')} {name}")
        
        choices.append(t('back'))
        
        action = questionary.select(t('software_manager_prompt'), choices=choices).ask()

        if action is None or action == t('back'):
            break

        # Find which software was selected
        verb, software_name = action.split(" ", 1)
        software = SOFTWARE_CATALOG.get(software_name)

        if software:
            if verb == t('install'):
                software['install'](software['package_name'])
            elif verb == t('manage'):
                software['manage']() 