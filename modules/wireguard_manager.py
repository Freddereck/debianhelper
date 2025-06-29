import os
import shutil
import subprocess
import time
from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from localization import get_string
from modules.panel_utils import clear_console, run_command, is_root
from modules import software_manager

console = Console()
WG_CONF_PATH = "/etc/wireguard/wg0.conf"
CLIENT_CONFIGS_PATH = "/etc/wireguard/clients"


def _is_wireguard_installed():
    """Checks if the wireguard-tools are installed by looking for the wg executable."""
    return os.path.exists('/usr/bin/wg')


def _get_server_public_key(config_path):
    """Reads a wg config and returns the public key derived from the private key."""
    try:
        with open(config_path, "r") as f:
            lines = f.readlines()
            
        # Find the start of the [Interface] section
        try:
            interface_start_index = next(i for i, line in enumerate(lines) if line.strip() == '[Interface]')
        except StopIteration:
            return None # No [Interface] section found

        # Search for the private key only within that section
        for i in range(interface_start_index + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('['): # We've hit the next section
                return None # Key not found in the interface section
            if line.startswith("PrivateKey"):
                server_private_key = line.split("=", 1)[1].strip()
                
                # Now derive the public key
                pub_key_cmd = subprocess.Popen(["echo", server_private_key], stdout=subprocess.PIPE)
                res = run_command(["wg", "pubkey"], stdin=pub_key_cmd.stdout)
                pub_key_cmd.wait()
                return res.stdout.strip() if res and res.returncode == 0 else None
        
        return None # Reached end of file without finding key in section
    except (FileNotFoundError, IndexError):
        return None

def _is_config_valid():
    """Checks if the wg0.conf file exists and seems valid (has an Interface with a PrivateKey)."""
    if not os.path.exists(WG_CONF_PATH):
        return False
    
    with open(WG_CONF_PATH, "r") as f:
        content = f.read()
        
    if "[Interface]" in content and "PrivateKey" in content:
        return True
        
    return False

def _create_server_config():
    """Guides the user through creating a default wg0.conf and adds the first client."""
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return False
        
    console.print("[yellow]Выполняется предварительная очистка для обеспечения чистого состояния...[/yellow]")
    run_command("wg-quick down wg0 >/dev/null 2>&1", spinner_message="Attempting to bring down any existing wg0 interface...")
    run_command("ip link del dev wg0 >/dev/null 2>&1", spinner_message="Ensuring wg0 interface is deleted...")
        
    try:
        clear_console()
        console.print(Panel(get_string("wg_creating_config"), style="yellow"))

        public_ip = inquirer.text(
            message=get_string("wg_server_public_ip_prompt"),
            long_instruction=get_string("wg_server_public_ip_help")
        ).execute()
        if not public_ip:
            console.print(f'\n{get_string("operation_cancelled")}')
            return False
        
        # --- Server Key Generation ---
        res = run_command(["wg", "genkey"])
        if not res or res.returncode != 0: return False
        server_private_key = res.stdout.strip()
        
        server_public_key_cmd = subprocess.Popen(["echo", server_private_key], stdout=subprocess.PIPE)
        res_pub = run_command(["wg", "pubkey"], stdin=server_public_key_cmd.stdout)
        server_public_key_cmd.wait()
        if not res_pub or res_pub.returncode != 0: return False
        server_public_key = res_pub.stdout.strip()

        # --- First Client Key Generation ---
        first_client_name = "dlya-testa"
        console.print(f"[yellow]Создается первый клиент с именем: [bold]{first_client_name}[/bold]...[/yellow]")
        res_client_priv = run_command(["wg", "genkey"])
        if not res_client_priv or res_client_priv.returncode != 0: return False
        client_private_key = res_client_priv.stdout.strip()

        client_public_key_cmd = subprocess.Popen(["echo", client_private_key], stdout=subprocess.PIPE)
        res_client_pub = run_command(["wg", "pubkey"], stdin=client_public_key_cmd.stdout)
        client_public_key_cmd.wait()
        if not res_client_pub or res_client_pub.returncode != 0: return False
        client_public_key = res_client_pub.stdout.strip()
        
        console.print("[yellow]Определяется основной сетевой интерфейс для правил NAT...[/yellow]")
        iface_find_cmd = "ip -4 route ls | grep default | grep -Po '(?<=dev )(\\S+)' | head -1"
        res = run_command(iface_find_cmd, spinner_message="Auto-detecting network interface...")

        if not res or not res.stdout.strip() or res.returncode != 0:
            console.print(Panel(
                "[red]Не удалось автоматически определить основной сетевой интерфейс.[/red]\n"
                "[yellow]Невозможно создать правила iptables. Установка не может быть продолжена.[/yellow]\n"
                f"Вывод ошибки (если есть):\n[red]{res.stderr if res else 'Нет вывода'}[/red]",
                title="[bold red]ОШИБКА ОПРЕДЕЛЕНИЯ ИНТЕРФЕЙСА[/bold red]"
            ))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return False

        default_iface = res.stdout.strip()
        console.print(f"[green]Сетевой интерфейс определен как: [bold]{default_iface}[/bold][/green]")

        # --- Assemble full config in memory ---
        server_ip = "10.0.0.1/24"
        client_ip = "10.0.0.2/32"

        config_content = f"""# Server Config
# Public IP: {public_ip}
[Interface]
Address = {server_ip}
SaveConfig = false
ListenPort = 51820
PrivateKey = {server_private_key}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_iface} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_iface} -j MASQUERADE

# --- First Client: {first_client_name} ---
[Peer]
# Client: {first_client_name}
PublicKey = {client_public_key}
AllowedIPs = {client_ip}
"""
        # --- Write server config once ---
        with open(WG_CONF_PATH, "w") as f:
            f.write(config_content)

        # --- Create first client config file ---
        os.makedirs(CLIENT_CONFIGS_PATH, exist_ok=True)
        client_config_content = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip.replace('/32', '/24')}
DNS = 8.8.8.8, 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {public_ip}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        client_conf_path = os.path.join(CLIENT_CONFIGS_PATH, f"{first_client_name}.conf")
        with open(client_conf_path, "w") as f:
            f.write(client_config_content)
        os.chmod(client_conf_path, 0o600)

        
        run_command(["systemctl", "daemon-reload"], spinner_message="Reloading systemd daemon...")
        run_command(["systemctl", "enable", "wg-quick@wg0"], spinner_message="Enabling WireGuard service...")
        run_command(["systemctl", "restart", "wg-quick@wg0"], spinner_message="Starting WireGuard service...")
        
        time.sleep(1)

        if not _is_config_valid():
            console.print(Panel(
                "[bold red]КРИТИЧЕСКАЯ ОШИБКА: САМОДИАГНОСТИКА ПРОВАЛЕНА[/bold red]\n\n"
                "Файл `wg0.conf` был [bold]успешно создан[/bold], но был [bold]немедленно поврежден[/bold] после попытки запуска службы `wg-quick@wg0`.\n\n"
                "Это почти всегда означает, что команды `PostUp`/`PostDown` в файле конфигурации не могут выполниться из-за проблем в вашей системе (например, с `iptables`).\n\n"
                "[yellow]Что делать:[/yellow]\n"
                "1.  Проверьте логи службы, чтобы увидеть точную ошибку:\n"
                "    [bold cyan]journalctl -u wg-quick@wg0[/bold cyan]\n"
                "2.  Проверьте, установлен ли у вас `iptables`.\n"
                "3.  Попробуйте вручную запустить службу, чтобы увидеть вывод:\n"
                "    [bold cyan]wg-quick up wg0[/bold cyan]",
                title="[bold red]ОШИБКА ПОСЛЕ СОЗДАНИЯ КОНФИГА[/bold red]"
            ))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return False

        console.print(Panel(
            get_string("wg_config_created_with_client", client_name=first_client_name, path=client_conf_path),
            title="[green]Success[/green]",
            border_style="green"
        ))
        return True
    except (KeyboardInterrupt, TypeError):
        console.print(f'\n{get_string("operation_cancelled")}')
        return False

def _add_client():
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return

    clear_console()
    console.print(Panel(get_string("wg_adding_client"), style="yellow"))

    try:
        client_name = inquirer.text(
            message=get_string("wg_client_name_prompt"),
            validate=lambda result: len(result) > 0 and ' ' not in result,
            invalid_message="Имя не может быть пустым или содержать пробелы"
        ).execute()
        if not client_name: return

        os.makedirs(CLIENT_CONFIGS_PATH, exist_ok=True)

        with open(WG_CONF_PATH, "r") as f:
            server_config_lines = f.readlines()

        last_ip_suffix = 1
        server_pub_ip = ""
        for line in server_config_lines:
            if "AllowedIPs" in line:
                ip = line.split("=")[1].strip().split('/')[0]
                suffix = int(ip.split('.')[-1])
                if suffix > last_ip_suffix:
                    last_ip_suffix = suffix
            if line.strip().startswith("# Public IP:"):
                server_pub_ip = line.split(":", 1)[1].strip()
        
        server_pub_key = _get_server_public_key(WG_CONF_PATH)
        
        if not server_pub_key:
            console.print(Panel(
                "[red]Не удалось получить публичный ключ сервера из `wg0.conf`.[/red]\n\n"
                "Это может означать, что файл конфигурации поврежден (например, отсутствует или некорректен `PrivateKey`).\n"
                "Пожалуйста, выйдите и войдите в менеджер WireGuard заново. Программа предложит пересоздать поврежденный конфиг.",
                title="[bold red]Критическая ошибка чтения конфигурации[/bold red]"
            ))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return
            
        if not server_pub_ip:
            console.print("[yellow]Не удалось найти публичный IP-адрес в комментариях wg0.conf.[/yellow]")
            server_pub_ip = inquirer.text(message=get_string("wg_server_public_ip_prompt")).execute()
            if not server_pub_ip:
                console.print("[red]IP-адрес не был предоставлен. Операция отменена.[/red]")
                inquirer.text(message=get_string("press_enter_to_continue")).execute()
                return

        new_client_ip = f"10.0.0.{last_ip_suffix + 1}"

        res_priv = run_command(["wg", "genkey"])
        if not res_priv or res_priv.returncode != 0:
            console.print("[red]Не удалось сгенерировать приватный ключ клиента.[/red]")
            return
        client_private_key = res_priv.stdout.strip()

        client_public_key_cmd = subprocess.Popen(["echo", client_private_key], stdout=subprocess.PIPE)
        res_pub = run_command(["wg", "pubkey"], stdin=client_public_key_cmd.stdout)
        client_public_key_cmd.wait()
        if not res_pub or res_pub.returncode != 0:
            console.print("[red]Не удалось сгенерировать публичный ключ клиента.[/red]")
            return
        client_public_key = res_pub.stdout.strip()

        peer_config = f"""
[Peer]
# Client: {client_name}
PublicKey = {client_public_key}
AllowedIPs = {new_client_ip}/32
"""
        with open(WG_CONF_PATH, "a") as f:
            f.write(peer_config)

        run_command(["systemctl", "restart", "wg-quick@wg0"], spinner_message="Reloading WireGuard service to apply changes...")

        client_config_content = f"""[Interface]
PrivateKey = {client_private_key}
Address = {new_client_ip.replace('/32', '/24')}
DNS = 8.8.8.8, 1.1.1.1

[Peer]
PublicKey = {server_pub_key}
Endpoint = {server_pub_ip}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        client_conf_path = os.path.join(CLIENT_CONFIGS_PATH, f"{client_name}.conf")
        with open(client_conf_path, "w") as f:
            f.write(client_config_content)
        
        os.chmod(client_conf_path, 0o600)

        console.print(f"[green]Клиент '{client_name}' успешно добавлен.[/green]")
        console.print(f"[cyan]Файл конфигурации сохранен в: {client_conf_path}[/cyan]")
        console.print("[yellow]Вы можете безопасно передать этот файл клиенту.[/yellow]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()

    except (KeyboardInterrupt, TypeError):
        console.print(f'\n{get_string("operation_cancelled")}')

def _get_peers():
    try:
        with open(WG_CONF_PATH, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    peers = []
    peer_lines = []
    for line in lines + ['[Interface]']:
        if line.strip().startswith('[') and peer_lines:
            peer_name = "Unnamed"
            pub_key = "N/A"
            allowed_ips = "N/A"

            for peer_line in peer_lines:
                if peer_line.strip().startswith("# Client:"):
                    try:
                        peer_name = peer_line.split(":", 1)[1].strip()
                    except IndexError:
                        peer_name = "Unnamed-Malformed"
                elif "PublicKey" in peer_line:
                    pub_key = peer_line.split("=")[1].strip()
                elif "AllowedIPs" in peer_line:
                    allowed_ips = peer_line.split("=")[1].strip()

            peers.append({
                "name": peer_name,
                "public_key": pub_key,
                "allowed_ips": allowed_ips,
                "config_lines": peer_lines
            })
            peer_lines = []

        if line.strip() == '[Peer]':
            peer_lines.append(line)
        elif peer_lines and not line.strip().startswith('['):
             peer_lines.append(line)
    return peers

def _view_clients():
    clear_console()
    peers = _get_peers()

    if not peers:
        console.print("[yellow]Клиенты не найдены в конфигурации.[/yellow]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return

    from rich.table import Table
    
    table = Table(title=get_string("wg_client_list_title"))
    table.add_column(get_string("wg_table_col_name"), justify="left", style="cyan")
    table.add_column(get_string("wg_table_col_key"), justify="left", style="magenta", no_wrap=True)
    table.add_column(get_string("wg_table_col_ip"), justify="left", style="green")
    
    for peer in peers:
        table.add_row(peer["name"], peer["public_key"], peer["allowed_ips"])
        
    console.print(table)
    inquirer.text(message=get_string("press_enter_to_continue")).execute()

def _view_config_file():
    clear_console()
    try:
        with open(WG_CONF_PATH, "r") as f:
            content = f.read()
        console.print(Panel(content, title=f"Содержимое {WG_CONF_PATH}", border_style="blue"))
    except FileNotFoundError:
        console.print(f"[red]Файл конфигурации {WG_CONF_PATH} не найден.[/red]")
    
    inquirer.text(message=get_string("press_enter_to_continue")).execute()

def _revoke_client():
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return

    clear_console()
    console.print(Panel(get_string("wg_revoking_client"), style="yellow"))

    try:
        peers = _get_peers()
            
        if not peers:
            console.print("[yellow]Не найдено ни одного клиента для удаления.[/yellow]")
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return
            
        choices = [Choice(value=peer, name=f'{peer["name"]} ({peer["allowed_ips"]})') for peer in peers]
        choices.append(Choice(value=None, name=get_string("action_back")))
        
        peer_to_revoke = inquirer.select(
            message=get_string("wg_revoke_client_prompt"),
            choices=choices
        ).execute()

        if not peer_to_revoke:
            return

        with open(WG_CONF_PATH, "r") as f:
            all_lines = f.readlines()

        new_config_lines = [line for line in all_lines if line not in peer_to_revoke["config_lines"]]
        
        with open(WG_CONF_PATH, "w") as f:
            f.writelines(new_config_lines)
            
        run_command(["systemctl", "restart", "wg-quick@wg0"], spinner_message="Reloading WireGuard service...")

        client_conf_path = os.path.join(CLIENT_CONFIGS_PATH, f"{peer_to_revoke['name']}.conf")
        if os.path.exists(client_conf_path):
            os.remove(client_conf_path)
            console.print(f"Удален файл конфигурации клиента: {client_conf_path}")

        console.print(f"[green]Клиент '{peer_to_revoke['name']}' успешно удален.[/green]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()

    except (KeyboardInterrupt, TypeError):
        console.print(f'\n{get_string("operation_cancelled")}')

def _ensure_valid_config():
    """
    Checks if wg0.conf exists and is valid. 
    If not, prompts the user to create or recreate it.
    Returns True if a valid config is present or created, False otherwise.
    """
    if _is_config_valid():
        return True

    if os.path.exists(WG_CONF_PATH):
        console.print(Panel("[red]Обнаружен поврежденный файл конфигурации `wg0.conf` (отсутствует PrivateKey).[/red]", title="[bold yellow]Поврежденная конфигурация[/bold yellow]"))
        recreate = inquirer.confirm(
            message="Хотите удалить поврежденный файл и создать новый?",
            default=True
        ).execute()
        
        if recreate:
            try:
                os.remove(WG_CONF_PATH)
                return _create_server_config()
            except OSError as e:
                console.print(f"[red]Не удалось удалить поврежденный файл: {e}[/red]")
                return False
        else:
            return False

    else:
        console.print(Panel(get_string("wg_config_not_found"), style="yellow", title="Внимание"))
        create = inquirer.confirm(
            message=get_string("wg_create_config_prompt"),
            default=True
        ).execute()
        if create:
            return _create_server_config()
        else:
            return False

def run_wireguard_manager():
    """Main menu for managing WireGuard."""
    if not _is_wireguard_installed():
        console.print(get_string("wg_not_installed_error"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return

    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return

    if not _ensure_valid_config():
        return

    while True:
        try:
            clear_console()
            console.print(Panel("WireGuard Manager", style="bold blue"))
            
            is_ui_installed = software_manager._is_package_installed("wg-dashboard")

            choices = []
            if is_ui_installed:
                console.print("[green]Обнаружен WireGuard-UI. Управление клиентами доступно через веб-интерфейс.[/green]")
                choices.append(Choice("install_ui", name=get_string("manage_wireguard_ui_service")))
            else:
                 choices.extend([
                    Choice("add", name=get_string("wg_add_client")),
                    Choice("revoke", name=get_string("wg_revoke_client")),
                    Choice("view", name=get_string("wg_view_clients")),
                 ])
                 choices.append(Choice("install_ui", name=get_string("install_wireguard_ui")))
            
            choices.append(Choice("config", name=get_string("wg_view_config")))
            choices.append(Choice(None, name=get_string("action_back")))

            action = inquirer.select(
                message=get_string("wg_menu_prompt"),
                choices=choices,
                vi_mode=True
            ).execute()

            if action == "add":
                _add_client()
            elif action == "revoke":
                _revoke_client()
            elif action == "view":
                _view_clients()
            elif action == "config":
                _view_config_file()
            elif action == "install_ui":
                if is_ui_installed:
                    software_manager._show_service_menu("wg-dashboard")
                else:
                    software_manager._handle_install("wg-dashboard")
            elif action == "back":
                break
            
            if action is None:
                break
        
        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break 