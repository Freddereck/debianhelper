import os
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, is_tool_installed, run_command_live, run_command_for_output
from app.translations import t
import re
import qrcode
from rich.table import Table

console = Console()

# --- New Feature Functions ---

def nginx_list_sites():
    console.print(f"[cyan]{t('nginx_listing_sites')}...[/cyan]")
    sites_enabled_path = "/etc/nginx/sites-enabled"
    if os.path.isdir(sites_enabled_path):
        try:
            sites = os.listdir(sites_enabled_path)
            if sites:
                for site in sites:
                    console.print(f" - [bold green]{site}[/bold green]")
            else:
                console.print(f"[yellow]{t('nginx_no_sites_found')}[/yellow]")
        except Exception as e:
            console.print(f"[red]{t('error_listing_sites', error=e)}[/red]")
    else:
        console.print(f"[red]{t('nginx_sites_enabled_not_found', path=sites_enabled_path)}[/red]")

def mysql_list_databases():
    console.print(f"[cyan]{t('mysql_listing_databases')}...[/cyan]")
    command = "sudo mysql -e 'SHOW DATABASES;'"
    run_command(command, show_output=True)

def postgresql_list_databases():
    console.print(f"[cyan]{t('postgresql_listing_databases')}...[/cyan]")
    command = "sudo -u postgres psql -c '\\l'"
    run_command(command, show_output=True)

def certbot_list_certificates():
    console.print(f"[cyan]{t('certbot_listing_certs')}...[/cyan]")
    run_command("sudo certbot certificates", show_output=True)

# --- Generic Management Functions ---

def service_status(service_name):
    run_command(f"sudo systemctl status {service_name}", show_output=True)

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
            t('nginx_menu_list_sites'), t('nginx_menu_status'), t('nginx_menu_test_config'), t('nginx_menu_reload'), 
            t('nginx_menu_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('nginx_menu_list_sites'): nginx_list_sites()
        elif action == t('nginx_menu_status'): service_status('nginx')
        elif action == t('nginx_menu_test_config'): run_command("sudo nginx -t", show_output=True)
        elif action == t('nginx_menu_reload'): service_reload('nginx')
        elif action == t('nginx_menu_restart'): service_restart('nginx')
        elif action == t('uninstall'): service_uninstall('nginx')
        if action != t('back'): questionary.press_any_key_to_continue().ask()

def manage_mysql():
    while True:
        console.clear()
        console.print(Panel(f"[bold yellow]MySQL {t('management')}[/bold yellow]", border_style="yellow"))
        action = questionary.select(t('what_to_do'), choices=[
            t('mysql_menu_list_db'), t('mysql_menu_status'), t('mysql_menu_secure'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('mysql_menu_list_db'): mysql_list_databases()
        elif action == t('mysql_menu_status'): service_status('mysql')
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
            t('postgresql_menu_list_db'), t('service_status'), t('service_restart'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('postgresql_menu_list_db'): postgresql_list_databases()
        elif action == t('service_status'): service_status('postgresql')
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
            t('certbot_menu_list_certs'), t('certbot_menu_get_cert'), t('certbot_menu_test_renewal'), t('uninstall'), t('back')
        ]).ask()

        if action == t('back') or action is None: break
        if action == t('certbot_menu_list_certs'): certbot_list_certificates()
        elif action == t('certbot_menu_get_cert'):
            console.print(f"[cyan]{t('certbot_get_cert_instructions')}[/cyan]")
            os.system("sudo certbot --nginx")
            questionary.press_any_key_to_continue().ask()
        elif action == t('certbot_menu_test_renewal'):
            console.print(f"[cyan]{t('certbot_testing_renewal')}...[/cyan]")
            run_command("sudo certbot renew --dry-run", show_output=True)
            questionary.press_any_key_to_continue().ask()
        elif action == t('uninstall'): 
            service_uninstall('certbot python3-certbot-nginx')
        
        if action != t('back'):
            questionary.press_any_key_to_continue().ask()

def manage_fail2ban():
    while True:
        console.clear()
        console.print(Panel(f"[bold_yellow]Fail2Ban {t('management')}[/bold_yellow]", border_style="yellow"))
        action = questionary.select(t('what_to_do'), choices=[
            t('fail2ban_menu_list_jails'),
            t('fail2ban_menu_unban_ip'),
            t('service_status'),
            t('service_restart'),
            t('uninstall'),
            t('back')
        ]).ask()

        if action == t('back') or action is None: break
        
        console.clear()
        if action == t('service_status'):
            service_status('fail2ban')
        elif action == t('service_restart'):
            service_restart('fail2ban')
        elif action == t('fail2ban_menu_list_jails'):
            console.print(f"[cyan]{t('fail2ban_listing_jails')}...[/cyan]")
            run_command("sudo fail2ban-client status", show_output=True)
        elif action == t('fail2ban_menu_unban_ip'):
            jail = questionary.text(t('fail2ban_prompt_jail')).ask()
            if jail:
                ip_address = questionary.text(t('fail2ban_prompt_ip')).ask()
                if ip_address:
                    console.print(f"[yellow]{t('fail2ban_unbanning_ip', ip=ip_address, jail=jail)}[/yellow]")
                    run_command(f"sudo fail2ban-client set {jail} unbanip {ip_address}", show_output=True)
        elif action == t('uninstall'):
            service_uninstall('fail2ban')
            
        questionary.press_any_key_to_continue().ask()

# --- WireGuard Management (Moved from services.py) ---

def generate_wg_keys():
    """Generates a WireGuard private and public key pair."""
    priv_key = run_command_for_output("wg genkey")
    pub_key = run_command_for_output(f"echo '{priv_key}' | wg pubkey")
    return priv_key.strip(), pub_key.strip()

def get_next_ip(server_config_content):
    """Finds the next available IP address for a new client."""
    peer_ips = re.findall(r"AllowedIPs\s*=\s*([\d\.]+/32)", server_config_content)
    used_ips = {int(ip.split('.')[-1].split('/')[0]) for ip in peer_ips}
    
    network_match = re.search(r"Address\s*=\s*([\d\.]+/\d+)", server_config_content)
    if not network_match: return None # Cannot determine network
    network_address = network_match.group(1).split('/')[0]
    base_ip = ".".join(network_address.split('.')[:3])
    
    next_ip_num = 2
    while next_ip_num in used_ips:
        next_ip_num += 1
    return f"{base_ip}.{next_ip_num}"

def show_qr_code(text):
    """Generates and displays a QR code in the terminal."""
    qr = qrcode.QRCode()
    qr.add_data(text)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

def add_wireguard_client(interface):
    server_conf_path = f"/etc/wireguard/{interface}.conf"
    client_name = questionary.text(t('wg_prompt_client_name')).ask()
    if not client_name: return

    if os.path.exists(f"/etc/wireguard/clients/{client_name}.conf"):
        console.print(f"[red]{t('wg_error_client_exists')}[/red]"); return
        
    with console.status(t('wg_generating_keys')):
        client_priv_key, client_pub_key = generate_wg_keys()
        server_config = run_command_for_output(f"sudo cat {server_conf_path}")
        
        pkey_match = re.search(r"PrivateKey\s*=\s*(.+)", server_config)
        port_match = re.search(r"ListenPort\s*=\s*(\d+)", server_config)
        if not pkey_match or not port_match: console.print("[red]Server config is invalid.[/red]"); return

        server_priv_key = pkey_match.group(1)
        server_pub_key = run_command_for_output(f"echo '{server_priv_key}' | wg pubkey").strip()
        server_endpoint = run_command_for_output("curl -s ifconfig.me").strip() + ":" + port_match.group(1)
        client_ip = get_next_ip(server_config)

    client_config = f"[Interface]\nPrivateKey = {client_priv_key}\nAddress = {client_ip}/32\nDNS = 8.8.8.8\n\n[Peer]\nPublicKey = {server_pub_key}\nEndpoint = {server_endpoint}\nAllowedIPs = 0.0.0.0/0\nPersistentKeepalive = 25"
    peer_entry = f"\n# Client: {client_name}\n[Peer]\nPublicKey = {client_pub_key}\nAllowedIPs = {client_ip}/32"
    
    run_command_for_output(f"echo '{peer_entry}' | sudo tee -a {server_conf_path}")
    os.makedirs("/etc/wireguard/clients", exist_ok=True)
    client_conf_path = f"/etc/wireguard/clients/{client_name}.conf"
    run_command_for_output(f"echo '{client_config}' | sudo tee {client_conf_path}")

    run_command_for_output(f"sudo wg-quick down {interface} && sudo wg-quick up {interface}")

    console.print(Panel(t('wg_client_added_title'), style="bold green"))
    console.print(Panel(client_config, title=t('wg_client_config_title'), border_style="cyan"))
    console.print(t('wg_client_config_path', path=client_conf_path))
    console.print(Panel(t('wg_client_qr_code_title'), border_style="magenta"))
    show_qr_code(client_config)
    questionary.press_any_key_to_continue().ask()

def list_wireguard_clients(interface):
    """Parses the server config to list all clients and their details."""
    server_conf_path = f"/etc/wireguard/{interface}.conf"
    try:
        server_config = run_command_for_output(f"sudo cat {server_conf_path}")
    except FileNotFoundError:
        console.print(t('wg_error_no_interfaces'))
        return

    # Find all peers with a client name comment
    clients = re.findall(r"# Client: (.+)\n\[Peer\]\nPublicKey = (.+)\nAllowedIPs = (.+)", server_config)
    
    if not clients:
        console.print(t('wg_error_no_clients'))
        questionary.press_any_key_to_continue().ask()
        return

    table = Table(title=t('wg_client_list_title'))
    table.add_column(t('wg_col_client_name'), style="cyan")
    table.add_column(t('wg_col_public_key'), style="green")
    table.add_column(t('wg_col_ip'), style="magenta")
    
    client_map = {}
    for name, pub_key, ip in clients:
        table.add_row(name, pub_key, ip)
        client_map[name] = {'pub_key': pub_key, 'ip': ip}

    console.print(table)
    
    client_to_manage = questionary.select(
        t('wg_prompt_select_client'),
        choices=[c[0] for c in clients] + [t('back')]
    ).ask()

    if client_to_manage and client_to_manage != t('back'):
        show_client_details_menu(client_to_manage)

def show_client_details_menu(client_name):
    """Shows a menu with actions for a specific client."""
    client_conf_path = f"/etc/wireguard/clients/{client_name}.conf"
    
    while True:
        console.clear()
        console.print(Panel(t('wg_client_details_title', client_name=client_name), style="bold blue"))
        
        choice = questionary.select(
            "Select an action:",
            choices=[
                t('wg_menu_show_config'),
                t('wg_menu_show_qr'),
                t('back')
            ]
        ).ask()

        if choice == t('back') or choice is None:
            break
        
        try:
            client_config = run_command_for_output(f"sudo cat {client_conf_path}")
            if not client_config:
                console.print("[red]Could not read client config.[/red]"); return
            
            if choice == t('wg_menu_show_config'):
                console.print(Panel(client_config, title=t('wg_client_config_title')))
                questionary.press_any_key_to_continue().ask()
            elif choice == t('wg_menu_show_qr'):
                show_qr_code(client_config)
                questionary.press_any_key_to_continue().ask()
        except FileNotFoundError:
            console.print(f"[red]Config for {client_name} not found.[/red]")
            questionary.press_any_key_to_continue().ask()
            break

def remove_wireguard_client(interface):
    server_conf_path = f"/etc/wireguard/{interface}.conf"
    server_config = run_command_for_output(f"sudo cat {server_conf_path}")
    
    clients = re.findall(r"# Client: (.+)", server_config)
    if not clients:
        console.print(t('wg_error_no_clients')); return

    client_to_remove = questionary.select(t('wg_prompt_remove_client'), choices=clients).ask()
    if not client_to_remove: return

    if questionary.confirm(t('wg_remove_confirm', client_name=client_to_remove)).ask():
        client_pub_key = run_command_for_output(f"sudo cat /etc/wireguard/clients/{client_to_remove}.conf | grep PublicKey | cut -d ' ' -f 3")
        
        # Remove from server config
        updated_config = re.sub(f"# Client: {client_to_remove}\n\[Peer\]\nPublicKey = .+\nAllowedIPs = .+\n", "", server_config)
        run_command_for_output(f"echo '{updated_config}' | sudo tee {server_conf_path}")
        
        # Remove client file
        run_command_for_output(f"sudo rm /etc/wireguard/clients/{client_to_remove}.conf")

        run_command_for_output(f"sudo wg-quick down {interface} && sudo wg-quick up {interface}")
        console.print(f"[green]{t('wg_client_removed', client_name=client_to_remove)}[/green]")
        questionary.press_any_key_to_continue().ask()

def manage_wireguard():
    WG_PATH = "/etc/wireguard"
    try:
        interfaces = [f.replace('.conf', '') for f in os.listdir(WG_PATH) if f.endswith('.conf')]
        if not interfaces: 
            console.print(t('wg_error_no_interfaces'))
            questionary.press_any_key_to_continue().ask()
            return
    except FileNotFoundError:
        console.print(t('wg_error_no_interfaces'))
        questionary.press_any_key_to_continue().ask()
        return

    interface = questionary.select(t('wg_prompt_select_interface'), choices=interfaces).ask()
    if not interface: return

    while True:
        action = questionary.select(t('wg_manage_title'), choices=[t('wg_menu_list_clients'), t('wg_menu_add_client'), t('wg_menu_remove_client'), t('back')]).ask()
        if action == t('wg_menu_list_clients'): list_wireguard_clients(interface)
        elif action == t('wg_menu_add_client'): add_wireguard_client(interface)
        elif action == t('wg_menu_remove_client'): remove_wireguard_client(interface)
        else: break

def manage_webmin():
    service_name = "webmin"
    while True:
        console.clear()
        ip_address = run_command_for_output("hostname -I | awk '{print $1}'").strip()
        status_output = run_command_for_output(f"sudo systemctl status {service_name} || true")

        status_label = f"Status: [red]{t('status_unknown')}[/red]"
        if "Active: active (running)" in status_output:
            status_label = f"Status: [green]{t('status_active')}[/green]"
        elif "Active: inactive (dead)" in status_output:
            status_label = f"Status: [red]{t('status_inactive')}[/red]"
        elif "Active: failed" in status_output:
            status_label = f"Status: [bold red]{t('status_failed')}[/bold red]"

        header = f"[bold]{t('webmin_manage_title', default='Webmin Management')}[/bold]\n"
        header += f"{t('webmin_access_url', default='Access URL: https://{ip}:10000', ip=ip_address)}\n"
        header += status_label
        
        console.print(Panel(header, style="blue"))

        choices = [
            t('service_menu_start'),
            t('service_menu_stop'),
            t('service_menu_restart'),
            t('service_menu_status'),
            t('back')
        ]
        action = questionary.select(t('prompt_action'), choices=choices).ask()

        if action is None or action == t('back'):
            break

        cmd_map = {
            t('service_menu_start'): "start",
            t('service_menu_stop'): "stop",
            t('service_menu_restart'): "restart",
            t('service_menu_status'): "status"
        }
        command = cmd_map.get(action)

        if command:
            console.clear()
            run_command(f"sudo systemctl {command} {service_name}", show_output=True)
            questionary.press_any_key_to_continue().ask()

def install_webmin_wizard(package_name):
    """A guided wizard for installing Webmin."""
    console.clear()
    console.print(Panel(t('webmin_install_wizard_title', default="Webmin Installation Wizard"), style="bold blue"))
    
    if not questionary.confirm(t('webmin_install_prompt', default="This will download and run the official Webmin repository setup script. This is required for installation. Continue?")).ask():
        return

    setup_script_url = "https://raw.githubusercontent.com/webmin/webmin/master/setup-repos.sh"
    setup_script_path = "setup-repos.sh"

    try:
        with console.status(t('webmin_downloading_script', default="Downloading setup script...")):
            run_command(f"curl -o {setup_script_path} {setup_script_url}")

        # The script uses sudo internally, so we run it as the current user
        with console.status(t('webmin_running_script', default="Running repository setup script (may ask for password)...")):
            run_command_live(f"sh {setup_script_path}")
        
        console.print(f"[{'green'}]✔[/green] {t('repo_setup_success', default='Repository setup complete.')}")

        # Now, use the generic service_install to install from the new repo
        service_install(package_name)

        ip_address = run_command_for_output("hostname -I | awk '{print $1}'").strip()
        console.print(Panel(t('webmin_access_info', default="Webmin installed successfully!\nAccess it at: https://{ip}:10000", ip=ip_address), style="green"))

    except Exception as e:
        console.print(f"[red]{t('error_during_installation', default='An error occurred:')} {e}[/red]")
    finally:
        # Clean up the script
        if os.path.exists(setup_script_path):
            with console.status(t('webmin_cleaning_up', default="Cleaning up...")):
                os.remove(setup_script_path)
    
    questionary.press_any_key_to_continue().ask()

def install_nextcloud_wizard(package_name):
    """A guided wizard for installing Nextcloud."""
    console.print(Panel(f"[bold blue]{t('nextcloud_wizard_title')}[/bold blue]", border_style="blue"))
    console.print(t('feature_not_implemented_yet'))
    questionary.press_any_key_to_continue().ask()

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

# --- Map software names to their management functions ---
SOFTWARE_MAP = {
    "Nginx": {
        "manage_func": manage_nginx,
        "install_func": service_install,
        "package_name": "nginx",
        "check_tool": "nginx",
        "version_cmd": "nginx -v 2>&1"  # Nginx prints version to stderr
    },
    "Apache2": {
        "manage_func": manage_apache,
        "install_func": service_install,
        "package_name": "apache2",
        "check_tool": "apache2",
        "version_cmd": "apache2 -v"
    },
    "MySQL": {
        "manage_func": manage_mysql,
        "install_func": service_install,
        "package_name": "mysql-server",
        "check_tool": "mysql",
        "version_cmd": "mysql --version"
    },
    "PostgreSQL": {
        "manage_func": manage_postgresql,
        "install_func": service_install,
        "package_name": "postgresql",
        "check_tool": "psql",
        "version_cmd": "psql --version"
    },
    "MongoDB": {
        "manage_func": manage_mongodb,
        "install_func": service_install,
        "package_name": "mongodb",
        "check_tool": "mongod",
        "version_cmd": "mongod --version"
    },
    "Redis": {
        "manage_func": manage_redis,
        "install_func": service_install,
        "package_name": "redis-server",
        "check_tool": "redis-server",
        "version_cmd": "redis-server --version"
    },
    "Certbot": {
        "manage_func": manage_certbot,
        "install_func": service_install,
        "package_name": "certbot python3-certbot-nginx",
        "check_tool": "certbot",
        "version_cmd": "certbot --version"
    },
    "Fail2Ban": {
        "manage_func": manage_fail2ban,
        "install_func": service_install,
        "package_name": "fail2ban",
        "check_tool": "fail2ban-client",
        "version_cmd": "fail2ban-client --version"
    },
    "Webmin": {
        "manage_func": manage_webmin,
        "install_func": install_webmin_wizard,
        "package_name": "webmin",
        "check_path": "/etc/webmin"
    },
    "Nextcloud": {
        "install_func": install_nextcloud_wizard,
        "package_name": "nextcloud-server", # Wizard is a stub, but for consistency
        "check_path": "/var/www/nextcloud"  # A common install location
    },
    "PHPMyAdmin": {
        "manage_func": manage_phpmyadmin,
        "install_func": install_phpmyadmin_managed,
        "package_name": "phpmyadmin",
        "check_path": "/usr/share/phpmyadmin"
    },
    "3X-UI": {
        "manage_func": manage_3x_ui,
        "install_func": install_3x_ui,
        "package_name": "3x-ui", # For display purposes
        "check_tool": "x-ui"
    },
    "WireGuard": {
        "manage_func": manage_wireguard,
        "install_func": service_install,
        "package_name": "wireguard-tools",
        "check_tool": "wg"
    }
}

# --- Main Software Manager ---

def show_software_manager():
    """Main menu for the Software Manager."""
    while True:
        console.clear()
        console.print(Panel(f"[bold blue]{t('software_manager_title')}[/bold blue]", border_style="blue"))
        
        choices = []
        raw_choices_map = {} # To map styled string back to simple name
        
        with console.status(f"[yellow]{t('gathering_versions_status')}[/yellow]"):
            for name, software in SOFTWARE_MAP.items():
                installed = False
                if software.get("check_tool"):
                    installed = is_tool_installed(software["check_tool"])
                elif software.get("check_path"):
                    installed = os.path.exists(software["check_path"])
                
                if installed:
                    # Only show manage option if a manage function exists
                    if software.get("manage_func"):
                        version_str = ""
                        if software.get("version_cmd"):
                            # Hide errors if command fails (e.g. permission denied for version)
                            version = run_command_for_output(f"{software['version_cmd']} 2>/dev/null")
                            if version:
                                # Extract version number using a more robust regex
                                match = re.search(r'(\d[\d\.-]*\d)', version)
                                if match:
                                    version_str = f" (v{match.group(1)})"
                        
                        display_text = f"[{t('manage')}] {name}{version_str}"
                        choices.append(display_text)
                        raw_choices_map[display_text] = f"manage {name}"
                else:
                    # Only show install option if an install function exists
                    if software.get("install_func"):
                        display_text = f"[{t('install')}] {name}"
                        choices.append(display_text)
                        raw_choices_map[display_text] = f"install {name}"

        choices.sort()
        choices.append(t('back'))
        
        action_display = questionary.select(t('software_manager_prompt'), choices=choices).ask()

        if action_display is None or action_display == t('back'):
            break

        action = raw_choices_map.get(action_display)
        if not action:
            continue

        # Find which software was selected
        verb, software_name = action.split(" ", 1)
        software = SOFTWARE_MAP.get(software_name)

        if software:
            if verb == 'install' and software.get("install_func"):
                # Pass package_name if it exists, as some installers require it
                package_name = software.get("package_name", "")
                software['install_func'](package_name)
            elif verb == 'manage' and software.get("manage_func"):
                software['manage_func']()
            else:
                console.print(f"[red]{t('invalid_action_error', action=verb, software=software_name)}[/red]")
                questionary.press_any_key_to_continue().ask() 