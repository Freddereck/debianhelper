import os
import re
import shutil
import questionary
import qrcode
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from app.translations import t

console = Console()

def run_command_for_output(command):
    """A local utility to run a command and capture its output, for simplicity."""
    try:
        # Using shell=True for simplicity with pipes, but be cautious with user input.
        # In this module, inputs are controlled, so it's relatively safe.
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True, encoding='utf-8', timeout=15
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""

# --- WireGuard Management ---

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
        if not interfaces: console.print(t('wg_error_no_interfaces')); return
    except FileNotFoundError:
        console.print(t('wg_error_no_interfaces')); return

    interface = questionary.select(t('wg_prompt_select_interface'), choices=interfaces).ask()
    if not interface: return

    while True:
        action = questionary.select(t('wg_manage_title'), choices=[t('wg_menu_add_client'), t('wg_menu_remove_client'), t('services_menu_back')]).ask()
        if action == t('wg_menu_add_client'): add_wireguard_client(interface)
        elif action == t('wg_menu_remove_client'): remove_wireguard_client(interface)
        else: break

# --- Generic Service Management ---

# List of common services to check
COMMON_SERVICES = ["ssh", "cron", "nginx", "apache2", "mysql", "postgresql", "docker", "fail2ban", "ufw"]

def is_wireguard_installed():
    """Check if 'wg' command is available."""
    return shutil.which("wg") is not None

def get_service_status(service_name):
    """Gets the status of a single service using systemctl."""
    output = run_command_for_output(f"systemctl is-active {service_name}")
    return output.strip() if output else "not found"

def show_all_services():
    """Displays the status of all common services in a table."""
    os.system('cls' if os.name == 'nt' else 'clear')
    table = Table(title=t('services_table_title'))
    table.add_column(t('services_col_service'), style="cyan")
    table.add_column(t('services_col_status'), style="magenta")

    with console.status(t('services_checking_status')):
        for service in COMMON_SERVICES:
            status = get_service_status(service)
            if status == "active":
                status_text = f"[green]{status}[/green]"
            elif status == "inactive" or status == "failed":
                status_text = f"[red]{status}[/red]"
            else:
                status_text = f"[yellow]{status}[/yellow]"
            
            # Only show services that are installed (not 'not found')
            if status != "not found":
                table.add_row(service, status_text)
    
    console.print(table)
    questionary.press_any_key_to_continue().ask()

def show_service_manager():
    """Main menu for the service manager."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('services_title')}[/bold blue]"))

        choices = [ t('services_menu_list_all') ]
        if is_wireguard_installed():
            choices.append(t('wg_manage_title'))
            
        choices.append(t('services_menu_back'))

        choice = questionary.select(t('services_prompt_action'), choices=choices).ask()

        if choice == t('services_menu_list_all'): show_all_services()
        elif choice == t('wg_manage_title'): manage_wireguard()
        elif choice == t('services_menu_back') or choice is None: break 