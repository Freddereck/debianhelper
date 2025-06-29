import os
import re
import shutil
import subprocess
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from InquirerPy.utils import get_style
from prompt_toolkit.formatted_text import ANSI
import tempfile
import configparser
import getpass
import webbrowser
import socket

from localization import get_string
from modules.panel_utils import clear_console, run_command, is_root

console = Console()

JAVA_PATH_CONFIG = os.path.expanduser('~/.linux_helper_java_path')

def strip_rich_markup(text):
    """Removes rich markup tags from a string."""
    return re.sub(r'\[(/?[a-zA-Z\s,=#]+)\]', '', text)

# Define the software we can manage
# 'key': { 'package_name': '...', 'service_name': '...', 'version_cmd': '...', 'pre_install': [...], ... }
SUPPORTED_SOFTWARE = {
    "mysql": {
        "display_name": "MySQL Server",
        "package_name": "mysql-server",
        "service_name": "mysql",
        "version_cmd": "mysql --version",
        "pre_install": [
             { "cmd": "systemctl stop mysql", "msg": "Остановка существующих служб MySQL..." },
             { "cmd": "DEBIAN_FRONTEND=noninteractive apt-get purge -y 'mysql*' && apt-get autoremove -y --purge && apt-get clean", "msg": "Полная очистка предыдущих установок MySQL..." },
             { "cmd": "rm -rf /etc/mysql /var/lib/mysql", "msg": "Удаление старых конфигураций и данных..." },
             { "cmd": "apt-get update", "msg": "Обновление списка пакетов..." },
             { "cmd": "apt-get install -y wget debconf-utils curl gnupg", "msg": "Установка зависимостей..." },
             { "cmd": "curl -fsSL https://repo.mysql.com/RPM-GPG-KEY-mysql-2023 | gpg --dearmor -o /usr/share/keyrings/mysql.gpg", "msg": "Импорт официального GPG ключа MySQL..." },
             { "cmd": "echo 'deb [signed-by=/usr/share/keyrings/mysql.gpg] http://repo.mysql.com/apt/debian/ bookworm mysql-8.0' > /etc/apt/sources.list.d/mysql.list", "msg": "Добавление репозитория MySQL вручную..." },
             { "cmd": "echo 'mysql-community-server mysql-community-server/root-pass password ' | debconf-set-selections", "msg": "Настройка пустого пароля для автоматизации..." },
             { "cmd": "echo 'mysql-community-server mysql-community-server/re-root-pass password ' | debconf-set-selections", "msg": "Подтверждение пустого пароля..." },
             { "cmd": "apt-get update", "msg": "Повторное обновление списка пакетов..." }
        ],
        "post_install": [
            { "cmd": "systemctl enable mysql", "msg": "Включение службы MySQL в автозагрузку..." },
            { "cmd": "bash -c 'for i in {1..30}; do mysqladmin ping &>/dev/null && break; echo -n . && sleep 1; done'", "msg": "Ожидание полной готовности сервера..." },
            { 
              "cmd": """
password=$(openssl rand -base64 12)
mysql --execute="ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '$password';"
mysql --execute="DELETE FROM mysql.user WHERE User='';"
mysql --execute="DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
mysql --execute="DROP DATABASE IF EXISTS test;"
mysql --execute="FLUSH PRIVILEGES;"
echo "--- ВАЖНО ---"
echo "Пароль для root@localhost был установлен на: $password"
echo "Сохраните его в надежном месте."
echo "---------------"
""",
              "msg": "Защита установки MySQL и установка пароля root...",
              "show_output": True
            }
        ]
    },
    "docker": {
        "display_name": "Docker Engine",
        "package_name": "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "service_name": "docker",
        "version_cmd": "docker --version",
        "is_installed_check": lambda: shutil.which('docker') is not None,
        "pre_install": [
            { "cmd": "rm -f /etc/apt/sources.list.d/docker.list", "msg": "Очистка старых конфигураций репозитория Docker..." },
            { "cmd": "apt-get update && apt-get install -y ca-certificates curl", "msg": "Установка зависимостей (ca-certificates, curl)..." },
            { "cmd": "install -m 0755 -d /etc/apt/keyrings", "msg": "Создание директории для ключей APT..." },
            { "cmd": "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc", "msg": "Импорт официального GPG ключа Docker..." },
            { "cmd": "chmod a+r /etc/apt/keyrings/docker.asc", "msg": "Настройка прав для ключа..." },
            { "cmd": "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null", "msg": "Добавление репозитория Docker..." },
            { "cmd": "apt-get update", "msg": "Повторное обновление списка пакетов..." }
        ],
        "post_install": [
             { "cmd": "systemctl enable --now docker", "msg": "Включение и запуск службы Docker..." }
        ]
    },
    "3x-ui": {
        "display_name": "3x-ui (Xray/WireGuard панель)",
        "service_name": "x-ui",
        "is_installed_check": lambda: shutil.which('x-ui') is not None or os.path.exists('/etc/systemd/system/x-ui.service'),
        "version_cmd": "x-ui version",
        "install_cmd": "apt-get update && apt-get install -y curl && yes \"\" | bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)",
        "uninstall_cmd": "x-ui uninstall",
        "show_output_on_success": True
    },
    "mariadb": {
        "display_name": "MariaDB Server",
        "package_name": "mariadb-server",
        "service_name": "mariadb",
        "version_cmd": "mariadb --version",
        "pre_install": [
            { "cmd": "rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list", "msg": "Очистка старых конфигураций репозитория..." },
            { "cmd": "apt-get update", "msg": "Обновление списка пакетов..." },
            { "cmd": "apt-get install -y gnupg curl", "msg": "Установка зависимостей (gnupg, curl)..." },
            { "cmd": "curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --batch --yes --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg", "msg": "Импорт GPG ключа MongoDB..." },
            { "cmd": "echo \"deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main\" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list", "msg": "Добавление репозитория MongoDB для Debian Bookworm..." },
            { "cmd": "apt-get update", "msg": "Повторное обновление списка пакетов..." }
        ],
        "post_install": [
            { "cmd": "systemctl enable --now mongod", "msg": "Включение и запуск службы MongoDB..." },
            { "cmd": """
set -e
password=$(openssl rand -base64 12)
mongosh --norc --eval "db.getSiblingDB('admin').createUser({ user: 'admin', pwd: '$password', roles: [ { role: 'userAdminAnyDatabase', db: 'admin' }, { role: 'root', db: 'admin' } ] })"
if ! grep -q "authorization: *enabled" /etc/mongod.conf; then
  echo -e "\\nsecurity:\\n  authorization: enabled" >> /etc/mongod.conf
  systemctl restart mongod
fi
echo "--- ВАЖНО ---"
echo "Для MongoDB включена аутентификация."
echo "Создан пользователь-администратор:"
echo "Логин: admin"
echo "Пароль: $password"
echo "Сохраните его в надежном месте."
echo "---------------"
""",
              "msg": "Настройка безопасности и создание пароля администратора...",
              "show_output": True
            }
        ]
    },
    "mongodb": {
        "display_name": "MongoDB",
        "package_name": "mongodb-org",
        "service_name": "mongod",
        "version_cmd": "mongod --version",
        "pre_install": [
            { "cmd": "rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list", "msg": "Очистка старых конфигураций репозитория..." },
            { "cmd": "apt-get update", "msg": "Обновление списка пакетов..." },
            { "cmd": "apt-get install -y gnupg curl", "msg": "Установка зависимостей (gnupg, curl)..." },
            { "cmd": "curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --batch --yes --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg", "msg": "Импорт GPG ключа MongoDB..." },
            { "cmd": "echo \"deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main\" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list", "msg": "Добавление репозитория MongoDB для Debian Bookworm..." },
            { "cmd": "apt-get update", "msg": "Повторное обновление списка пакетов..." }
        ],
        "post_install": [
            { "cmd": "systemctl enable --now mongod", "msg": "Включение и запуск службы MongoDB..." }
        ]
    },
    "wireguard": {
        "display_name": "WireGuard",
        "package_name": "wireguard-tools",
        "version_cmd": "wg --version",
        "is_installed_check": lambda: os.path.exists('/usr/bin/wg'),
        "post_install": [
            {"cmd": "grep -qxF 'net.ipv4.ip_forward=1' /etc/sysctl.conf || echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf", "msg": "Настройка постоянного IP-форвардинга..."},
            {"cmd": "sysctl -p", "msg": "Применение настроек ядра для IP-форвардинга..."}
        ]
    },
    "java": {
        "display_name": get_string("java_display_name"),
        "package_name": "openjdk-17-jdk",
        "version_cmd": "java -version",
        "is_installed_check": lambda: shutil.which('java') is not None or (os.path.exists(JAVA_PATH_CONFIG) and os.access(open(JAVA_PATH_CONFIG).read().strip(), os.X_OK)),
    },
    "wg-dashboard": {
        "display_name": "WireGuard Dashboard",
        "package_name": "",
        "service_name": "",
        "version_cmd": "",
        "is_installed_check": lambda: False,  # Заглушка, всегда не установлен
    },
    "webmin": {
        "display_name": "Webmin (веб-панель управления сервером)",
        "package_name": "webmin",
        "service_name": "webmin",
        "version_cmd": "/usr/share/webmin/miniserv.pl --version || webmin --version",
        "is_installed_check": lambda: os.path.exists('/etc/webmin'),
        "install_cmd": "wget -qO- http://www.webmin.com/jcameron-key.asc | apt-key add - && echo 'deb http://download.webmin.com/download/repository sarge contrib' > /etc/apt/sources.list.d/webmin.list && apt-get update && apt-get install -y webmin",
        "uninstall_cmd": "apt-get purge -y webmin && rm -rf /etc/webmin /var/webmin",
        "show_output_on_success": True
    },
    "pterodactyl": {
        "display_name": "Pterodactyl (панель для игровых серверов)",
        "package_name": "pterodactyl-panel",
        "service_name": "pterodactyl-panel",
        "version_cmd": "cd /var/www/pterodactyl && php artisan --version",
        "is_installed_check": lambda: os.path.exists('/var/www/pterodactyl'),
        "install_cmd": "echo 'Pterodactyl будет установлен по официальной инструкции. Требуется: nginx, MySQL/MariaDB, PHP 8.1+, composer, nodejs, yarn.\nСм. https://pterodactyl.io/panel/1.11/getting_started.html' && sleep 2 && bash <(curl -s https://raw.githubusercontent.com/pterodactyl/installer/main/install.sh)",
        "uninstall_cmd": "rm -rf /var/www/pterodactyl /etc/systemd/system/pterodactyl* && systemctl daemon-reload",
        "service_status_cmd": "systemctl status pterodactyl-panel",
        "service_start_cmd": "systemctl start pterodactyl-panel",
        "service_stop_cmd": "systemctl stop pterodactyl-panel",
        "service_restart_cmd": "systemctl restart pterodactyl-panel",
    },
    "wings": {
        "display_name": "Wings (Pterodactyl Node)",
        "package_name": "wings",
        "service_name": "wings",
        "version_cmd": "/usr/local/bin/wings --version",
        "is_installed_check": lambda: shutil.which('wings') is not None or os.path.exists('/usr/local/bin/wings'),
        "install_cmd": "bash <(curl -s https://pterodactyl.io/install/standalone.sh)",
        "uninstall_cmd": "systemctl stop wings && systemctl disable wings && rm -f /etc/systemd/system/wings.service /usr/local/bin/wings && systemctl daemon-reload",
        "service_status_cmd": "systemctl status wings",
        "service_start_cmd": "systemctl start wings",
        "service_stop_cmd": "systemctl stop wings",
        "service_restart_cmd": "systemctl restart wings",
    },
}

def _is_root():
    return os.geteuid() == 0

def _is_package_installed(key):
    """Checks if a software is installed using a custom check if available."""
    software_data = SUPPORTED_SOFTWARE[key]
    
    # Use custom check if it exists
    if "is_installed_check" in software_data:
        return software_data["is_installed_check"]()
        
    # Fallback to dpkg check for others
    package_names = software_data.get('package_name')
    if not package_names:
        return False
    packages = package_names.split()
    if not packages:
        return False
        
    for package_name in packages:
        # Use run_command and check its result
        res = run_command(['dpkg-query', '-W', '-f=${Status}', package_name], spinner_message=f"Checking status of {package_name}...")
        if not res or res.returncode != 0 or "install ok installed" not in res.stdout:
            return False
    return True

def _handle_install(key):
    data = SUPPORTED_SOFTWARE[key]
    
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return

    # --- NEW: Docker running check for docker-based software ---
    if data.get("service_manager") == "docker":
        docker_status = run_command(["systemctl", "is-active", "docker"], spinner_message="Проверка статуса Docker...")
        if not docker_status or docker_status.stdout.strip() != "active":
            console.print("[red]Docker не запущен! Запустите его командой: systemctl start docker[/red]")
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
            return

    # --- NEW: wg-quick@wg0 active check for wg-dashboard ---
    if key == "wg-dashboard":
        wgquick_status = run_command(["systemctl", "is-active", "wg-quick@wg0"], spinner_message="Проверка статуса wg-quick@wg0...")
        if wgquick_status and wgquick_status.stdout.strip() == "active":
            console.print("[yellow]Внимание: wg-quick@wg0 сейчас активен! Это может вызвать конфликт с WGDashboard. Отключите его командой: systemctl disable --now wg-quick@wg0[/yellow]")
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()

    # --- Dependency Check ---
    if "dependencies" in data:
        for dep_key in data["dependencies"]:
            if not _is_package_installed(dep_key):
                dep_data = SUPPORTED_SOFTWARE[dep_key]
                console.print(f"[bold red]Ошибка: Для установки {data['display_name']} требуется {dep_data['display_name']}.[/bold red]")
                try:
                    install_dep = inquirer.confirm(
                        message=f"Хотите сначала установить {dep_data['display_name']}?",
                        default=True
                    ).execute()
                except KeyboardInterrupt:
                    console.print(f'\n{get_string("operation_cancelled")}')
                    return
                if install_dep:
                    _handle_install(dep_key) # Recursive call
                    if not _is_package_installed(dep_key):
                        console.print(f"[red]Не удалось установить зависимость {dep_data['display_name']}. Установка {data['display_name']} отменена.[/red]")
                        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
                        return
                else:
                    console.print(f"[yellow]Установка {data['display_name']} отменена из-за отсутствия зависимости.[/yellow]")
                    inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
                    return

    # --- Описание Webmin перед установкой ---
    if key == "webmin":
        console.print(Panel(
            "[bold cyan]Webmin[/bold cyan] — это мощная и гибкая веб-панель для администрирования Linux-серверов через браузер.\n\n"
            "• Позволяет управлять пользователями, сервисами, сетевыми настройками, брандмауэром, пакетами, cron, логами и многим другим.\n"
            "• Поддерживает плагины, SSL, управление несколькими серверами.\n"
            "• Интерфейс доступен по адресу: https://<IP>:10000 (после установки).\n\n"
            "[yellow]Внимание:[/yellow] Webmin открывает доступ к управлению сервером через веб. Не забудьте настроить безопасный пароль и firewall!\n\n"
            "Подробнее: [link=https://www.webmin.com/]https://www.webmin.com/[/link]",
            title="О Webmin",
            border_style="blue"
        ))
        inquirer.text(message="Нажмите Enter для продолжения...").execute()

    # --- Custom Install Command ---
    if "install_cmd" in data:
        try:
            res = run_command(data["install_cmd"], get_string("installing", package=data['display_name']))
        except FileNotFoundError as e:
            console.print(Panel(f"[red]Команда не найдена: {e}[/red]", title="[red]Ошибка установки[/red]", border_style="red"))
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
            return
        if res and res.returncode == 0:
            console.print(get_string("install_success", package=data['display_name']))
            if data.get("show_output_on_success") and res.stdout:
                console.print(res.stdout.strip())
        else:
            err_out = (res.stderr or '') + '\n' + (res.stdout or '') if res else ''
            console.print(Panel(err_out.strip() or '[red]Неизвестная ошибка[/red]', title="[red]Детали ошибки[/red]", border_style="red"))
            # Fallback: советы и ссылки
            if key in ("webmin", "pterodactyl", "wings"):
                doc_links = {
                    "webmin": "https://www.webmin.com/",
                    "pterodactyl": "https://pterodactyl.io/panel/1.11/getting_started.html",
                    "wings": "https://pterodactyl.io/wings/1.11/installing.html"
                }
                console.print(Panel(f"[yellow]Попробуйте ручную установку по инструкции: {doc_links[key]}[/yellow]", title="[yellow]Что делать?[/yellow]", border_style="yellow"))
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return

    # --- EXISTING: Standard Apt Install ---
    package_name = data['package_name']

    if "pre_install" in data:
        console.print(Panel(f"Подготовка к установке {data['display_name']}. Это может занять некоторое время...", style="yellow", title="Шаги предварительной установки"))
        for step in data["pre_install"]:
            res = run_command(step["cmd"], step["msg"])
            if res and res.returncode != 0:
                console.print(f"[red]Шаг предварительной установки провален: {step['msg']}[/red]")
                console.print(Panel(res.stderr, title="[red]Детали ошибки[/red]", border_style="red"))
                inquirer.text(message="Нажмите Enter для отмены установки").execute()
                return
        console.print("[green]Шаги предварительной установки успешно завершены.[/green]")

    res = run_command(
        f"DEBIAN_FRONTEND=noninteractive apt-get install -y {package_name}",
        get_string("installing", package=data['display_name'])
    )
    if res and res.returncode == 0:
        console.print(get_string("install_success", package=data['display_name']))
        
        if "post_install" in data:
            console.print(Panel(f"Выполнение пост-установочной настройки для {data['display_name']}...", style="yellow", title="Пост-установочная настройка"))
            for step in data["post_install"]:
                res = run_command(step["cmd"], step["msg"])
                if res and res.returncode != 0:
                    console.print(f"[red]Шаг пост-установки провален: {step['msg']}[/red]")
                    console.print(Panel(res.stderr, title="[red]Детали ошибки[/red]", border_style="red"))
                if res and step.get("show_output"):
                    console.print(Panel(res.stdout, title="[cyan]Вывод команды[/cyan]", border_style="cyan"))
            console.print("[green]Пост-установочная настройка успешно завершена.[/green]")
    else:
        console.print(get_string("install_fail", package=data['display_name']))
        if res:
            console.print(Panel(res.stderr, title="[red]Error Details[/red]", border_style="red"))
    
    inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()

    if key == 'pterodactyl':
        console.print(Panel(get_string('pterodactyl_description'), title='Pterodactyl', border_style='blue'))
        confirm = inquirer.confirm(message=get_string('uninstall_confirm', package='Pterodactyl')).execute()
        if not confirm:
            return

def _handle_uninstall(key):
    data = SUPPORTED_SOFTWARE[key]
    package_name = data.get('package_name') # Use .get as it might not exist
    
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return

    try:
        confirmed = inquirer.confirm(
            message=get_string("uninstall_confirm", package=data['display_name']),
            default=False
        ).execute()
    except KeyboardInterrupt:
        console.print(f'\n{get_string("operation_cancelled")}')
        return

    if not confirmed:
        return

    # --- Custom Uninstall Command ---
    if "uninstall_cmd" in data:
        try:
            res = run_command(data["uninstall_cmd"], get_string("uninstalling", package=data['display_name']))
        except FileNotFoundError as e:
            console.print(Panel(f"[red]Команда не найдена: {e}[/red]", title="[red]Ошибка удаления[/red]", border_style="red"))
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
            return
        if res and res.returncode == 0:
            console.print(get_string("uninstall_success", package=data['display_name']))
        else:
            err_out = (res.stderr or '') + '\n' + (res.stdout or '') if res else ''
            console.print(Panel(err_out.strip() or '[red]Неизвестная ошибка[/red]', title="[red]Детали ошибки[/red]", border_style="red"))
            # Fallback: ручное удаление
            if key in ("webmin", "pterodactyl", "wings"):
                manual_steps = []
                if key == "webmin":
                    manual_steps = [
                        (['systemctl', 'stop', 'webmin'], "Остановка сервиса webmin..."),
                        (['systemctl', 'disable', 'webmin'], "Отключение автозапуска webmin..."),
                        (['rm', '-rf', '/etc/webmin', '/var/webmin'], "Удаление конфигов webmin..."),
                        (['apt-get', 'purge', '-y', 'webmin'], "Удаление пакета webmin..."),
                        (['systemctl', 'daemon-reload'], "Перезагрузка systemd...")
                    ]
                elif key == "pterodactyl":
                    manual_steps = [
                        (['systemctl', 'stop', 'pterodactyl-panel'], "Остановка сервиса pterodactyl-panel..."),
                        (['systemctl', 'disable', 'pterodactyl-panel'], "Отключение автозапуска..."),
                        (['rm', '-rf', '/var/www/pterodactyl', '/etc/systemd/system/pterodactyl*'], "Удаление файлов панели..."),
                        (['systemctl', 'daemon-reload'], "Перезагрузка systemd...")
                    ]
                elif key == "wings":
                    manual_steps = [
                        (['systemctl', 'stop', 'wings'], "Остановка сервиса wings..."),
                        (['systemctl', 'disable', 'wings'], "Отключение автозапуска..."),
                        (['rm', '-f', '/etc/systemd/system/wings.service', '/usr/local/bin/wings'], "Удаление файлов wings..."),
                        (['systemctl', 'daemon-reload'], "Перезагрузка systemd...")
                    ]
                all_ok = True
                for cmd, msg in manual_steps:
                    res2 = run_command(cmd, msg)
                    if res2 and res2.returncode != 0:
                        all_ok = False
                        console.print(Panel(res2.stderr or f"Ошибка при выполнении: {' '.join(cmd)}", title="[red]Ошибка ручного удаления[/red]", border_style="red"))
                if all_ok:
                    console.print(Panel(f"{data['display_name']} и все его следы были удалены вручную!", title="[green]Удаление завершено[/green]", border_style="green"))
                else:
                    console.print(Panel("Некоторые шаги удаления завершились с ошибкой. Проверьте вывод выше и удалите остатки вручную.", title="[yellow]Удаление частично завершено[/yellow]", border_style="yellow"))
            # Fallback: советы и ссылки
            if key in ("webmin", "pterodactyl", "wings"):
                doc_links = {
                    "webmin": "https://www.webmin.com/",
                    "pterodactyl": "https://pterodactyl.io/panel/1.11/getting_started.html",
                    "wings": "https://pterodactyl.io/wings/1.11/installing.html"
                }
                console.print(Panel(f"[yellow]Попробуйте ручное удаление по инструкции: {doc_links[key]}[/yellow]", title="[yellow]Что делать?[/yellow]", border_style="yellow"))
            inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return
    # --- Обычная логика для остальных ---
    if "uninstall_cmd" in data:
        res = run_command(data["uninstall_cmd"], get_string("uninstalling", package=data['display_name']))
    elif package_name: # Only run apt-get if there's a package name
        res = run_command(
            f"DEBIAN_FRONTEND=noninteractive apt-get purge -y {package_name}",
            get_string("uninstalling", package=data['display_name'])
        )
    else:
        # No uninstall method defined
        console.print(f"[yellow]Для {data['display_name']} не определен метод удаления.[/yellow]")
        res = None

    if res and res.returncode == 0:
        console.print(get_string("uninstall_success", package=data['display_name']))
    else:
        console.print(get_string("uninstall_fail", package=data['display_name']))
        extra_hint = False
        if res:
            if res.stderr:
                console.print(Panel(res.stderr, title="[red]Error Details[/red]", border_style="red"))
                extra_hint = True
            elif res.stdout and ("is not installed" in res.stdout or "not installed" in res.stdout):
                console.print("[yellow]WireGuard уже не установлен или не найден в системе.[/yellow]")
                extra_hint = True
        if not extra_hint:
            console.print(Panel(
                "Возможные причины: WireGuard уже удалён, установлен не через apt, или возникли проблемы с apt.\n"
                "\n[bold]Попытка автоматического удаления вручную...[/bold]",
                title="[yellow]Что делать, если не удаляется?[/yellow]",
                border_style="yellow"
            ))
            # Автоматическое удаление вручную
            manual_steps = [
                (['systemctl', 'stop', 'wg-quick@wg0'], "Остановка сервиса wg-quick@wg0..."),
                (['systemctl', 'disable', 'wg-quick@wg0'], "Отключение автозапуска wg-quick@wg0..."),
                (['rm', '-rf', '/etc/wireguard'], "Удаление конфигов /etc/wireguard..."),
                (['rm', '-f', '/usr/bin/wg', '/usr/bin/wg-quick'], "Удаление бинарников wg/wg-quick..."),
                (['rm', '-f', '/etc/systemd/system/wg-quick@wg0.service'], "Удаление systemd unit wg-quick@wg0.service..."),
                (['systemctl', 'daemon-reload'], "Перезагрузка systemd...")
            ]
            all_ok = True
            for cmd, msg in manual_steps:
                res2 = run_command(cmd, msg)
                if res2 and res2.returncode != 0:
                    all_ok = False
                    console.print(Panel(res2.stderr or f"Ошибка при выполнении: {' '.join(cmd)}", title="[red]Ошибка ручного удаления[/red]", border_style="red"))
            if all_ok:
                console.print(Panel("WireGuard и все его следы были удалены вручную!", title="[green]Удаление завершено[/green]", border_style="green"))
            else:
                console.print(Panel("Некоторые шаги удаления завершились с ошибкой. Проверьте вывод выше и удалите оставшиеся файлы вручную.", title="[yellow]Удаление частично завершено[/yellow]", border_style="yellow"))
    inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()

def _handle_version_check(key):
    data = SUPPORTED_SOFTWARE[key]
    try:
        res = run_command(data['version_cmd'].split(), spinner_message=f"Checking version for {data['display_name']}...")
    except FileNotFoundError as e:
        console.print(Panel(f"[red]Команда не найдена: {e}[/red]", title="[red]Ошибка версии[/red]", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return
    if res and res.returncode == 0:
        console.print(Panel(f"[bold cyan]{get_string('version_info', package=data['display_name'])}[/bold cyan]\n\n{res.stdout.strip()}", title="Version", border_style="cyan"))
    else:
        err_out = (res.stderr or '') + '\n' + (res.stdout or '') if res else ''
        console.print(Panel(err_out.strip() or '[red]Не удалось получить версию[/red]', title="[red]Ошибка версии[/red]", border_style="red"))
        if key in ("webmin", "pterodactyl", "wings"):
            doc_links = {
                "webmin": "https://www.webmin.com/",
                "pterodactyl": "https://pterodactyl.io/panel/1.11/getting_started.html",
                "wings": "https://pterodactyl.io/wings/1.11/installing.html"
            }
            console.print(Panel(f"[yellow]Проверьте документацию: {doc_links[key]}[/yellow]", title="[yellow]Что делать?[/yellow]", border_style="yellow"))
        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()

def _show_service_menu(key):
    """Shows the service management menu for a package."""
    data = SUPPORTED_SOFTWARE[key]
    service_name = data['service_name']
    manager = data.get('service_manager', 'systemctl')
    
    if not is_root():
        console.print(get_string("need_root_warning"))
        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
        return

    while True:
        try:
            clear_console()
            
            status_text = "Unknown"
            status_style = "yellow"
            full_status_output = "Could not get status."
            
            # Get fresh status every time we show the menu
            if manager == 'systemctl':
                status_res = run_command(['systemctl', 'status', service_name], "Checking service status...")
                full_status_output = status_res.stdout if status_res else "Could not get status."
                if status_res and status_res.stdout:
                    if 'Active: active (running)' in status_res.stdout:
                        status_text = "Active (Running)"
                        status_style = "green"
                    elif 'Active: inactive (dead)' in status_res.stdout:
                        status_text = "Inactive (Dead)"
                        status_style = "red"
                    elif 'Active: failed' in status_res.stdout:
                        status_text = "Failed"
                        status_style = "bold red"
                # Note: systemctl status returns 3 if service is inactive. We shouldn't treat it as a critical error.
                elif status_res and status_res.returncode != 0 and status_res.returncode != 3:
                     console.print(Panel(status_res.stderr, title="[red]Error checking status[/red]", border_style="red"))
            
            elif manager == 'docker':
                # For docker, we check the container state
                status_res = run_command(['docker', 'inspect', "-f='{{.State.Status}}'", service_name], f"Checking status for container {service_name}...")
                if status_res and status_res.returncode == 0 and status_res.stdout:
                    container_status = status_res.stdout.strip().replace("'", "")
                    full_status_output = f"Container '{service_name}' status: {container_status}"
                    if container_status == 'running':
                        status_text = "Running"
                        status_style = "green"
                    elif container_status in ['exited', 'created', 'dead']:
                        status_text = f"Stopped ({container_status})"
                        status_style = "red"
                    else:
                        status_text = container_status.capitalize()
                else:
                    full_status_output = status_res.stderr if (status_res and status_res.stderr) else "Container not found or Docker error."


            console.print(Panel(
                f"Service: [bold cyan]{service_name}[/bold cyan]\nStatus: [{status_style}]{status_text}[/{status_style}]",
                title=f"Managing {data['display_name']}",
                border_style="blue"
            ))

            choices = [
                Choice("start", name=get_string("service_start")),
                Choice("stop", name=get_string("service_stop")),
                Choice("restart", name=get_string("service_restart")),
                Choice("status", name=get_string("service_status")),
                Choice("webmin_settings", name=get_string("webmin_settings_menu")),
                Choice(None, name=get_string("action_back"))
            ]

            op = inquirer.select(
                message=get_string("service_actions_prompt", package=data['display_name']),
                choices=choices,
                vi_mode=True
            ).execute()

            if op is None:
                break
            
            if op == 'status':
                clear_console()
                console.print(Panel(full_status_output, title=f"Status for {service_name}"))
                inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
            elif op == 'webmin_settings':
                webmin_settings_menu()
            else:
                cmd = []
                if manager == 'systemctl':
                    cmd = ['systemctl', op, service_name]
                elif manager == 'docker':
                    # 'status' is already handled, 'enable/disable' is not applicable
                    if op in ['start', 'stop', 'restart']:
                         cmd = ['docker', op, service_name]
                    else:
                        console.print(f"[yellow]Операция '{op}' не поддерживается для Docker контейнеров.[/yellow]")
                        inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
                        continue
                
                res = run_command(
                    cmd,
                    f"Executing '{op}' on {service_name}..."
                )
                if res and res.returncode == 0:
                    console.print(get_string("service_operation_success", op=op, package=service_name))
                else:
                    console.print(get_string("service_operation_fail", op=op, package=service_name))
                    if res and res.stderr:
                         console.print(Panel(res.stderr, title="[red]Error Details[/red]", border_style="red"))
                inquirer.text(message=get_string("press_enter_to_continue", lang="ru")).execute()
                # We don't break here, so the user can perform another action.
                # The status at the top will refresh.

        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break

def _parse_xui_settings(settings_text):
    """Парсит вывод x-ui settings и возвращает port, webBasePath, access_url."""
    import re
    port = None
    webpath = None
    access_url = None
    for line in settings_text.splitlines():
        if line.strip().startswith("port:"):
            port = line.split(":",1)[1].strip()
        elif line.strip().startswith("webBasePath:"):
            webpath = line.split(":",1)[1].strip().strip('/')
        elif line.strip().startswith("Access URL:"):
            access_url = line.split(":",1)[1].strip()
    return port, webpath, access_url

def _show_3xui_menu():
    while True:
        clear_console()
        # Статус сервиса
        status_res = run_command(["systemctl", "is-active", "x-ui"])
        status = status_res.stdout.strip() if status_res and status_res.returncode == 0 else "inactive"
        version_res = run_command(["x-ui", "version"])
        version = version_res.stdout.strip() if version_res and version_res.returncode == 0 else "N/A"
        # Получаем актуальные настройки
        port = "54321"
        webpath = ""
        access_url = None
        settings_res = run_command(["x-ui", "settings"])
        if settings_res and settings_res.stdout:
            p, w, a = _parse_xui_settings(settings_res.stdout)
            if p:
                port = p
            if w:
                webpath = w
            if a:
                access_url = a
        # Формируем ссылку
        if access_url:
            url = access_url
        else:
            url = f"http://<IP_вашего_сервера>:{port}"
            if webpath:
                url += f"/{webpath}"
        console.print(Panel(f"[bold]3x-ui[/bold] (Xray/WireGuard панель)\n\nСтатус: [cyan]{status}[/cyan]\nВерсия: [cyan]{version}[/cyan]\nПорт: [cyan]{port}[/cyan]", title="Статус 3x-ui", border_style="blue"))
        choices = [
            Choice("start", name="Запустить сервис 3x-ui"),
            Choice("stop", name="Остановить сервис 3x-ui"),
            Choice("restart", name="Перезапустить сервис 3x-ui"),
            Choice("xui_status", name="Показать статус (x-ui status)"),
            Choice("xui_settings", name="Показать настройки (x-ui settings)"),
            Choice("enable", name="Включить автозапуск (x-ui enable)"),
            Choice("disable", name="Отключить автозапуск (x-ui disable)"),
            Choice("log", name="Показать лог (journalctl)"),
            Choice("xui_log", name="Показать лог (x-ui log)"),
            Choice("banlog", name="Показать banlog (x-ui banlog)"),
            Choice("update", name="Обновить 3x-ui (x-ui update)"),
            Choice("reset_pass", name="Сбросить пароль администратора"),
            Choice("open", name="Показать ссылку на веб-интерфейс"),
            Choice("uninstall", name="Удалить 3x-ui"),
            Choice(None, name="Назад")
        ]
        action = inquirer.select(
            message="Выберите действие для 3x-ui:",
            choices=choices,
            vi_mode=True
        ).execute()
        if action == "start":
            run_command(["systemctl", "start", "x-ui"], spinner_message="Запуск 3x-ui...")
        elif action == "stop":
            run_command(["systemctl", "stop", "x-ui"], spinner_message="Остановка 3x-ui...")
        elif action == "restart":
            run_command(["systemctl", "restart", "x-ui"], spinner_message="Перезапуск 3x-ui...")
        elif action == "xui_status":
            res = run_command(["x-ui", "status"])
            if res and res.stdout:
                console.print(Panel(res.stdout, title="x-ui status", border_style="green"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "xui_settings":
            res = run_command(["x-ui", "settings"])
            if res and res.stdout:
                console.print(Panel(res.stdout, title="x-ui settings", border_style="green"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "enable":
            run_command(["x-ui", "enable"], spinner_message="Включение автозапуска...")
        elif action == "disable":
            run_command(["x-ui", "disable"], spinner_message="Отключение автозапуска...")
        elif action == "log":
            log_res = run_command(["journalctl", "-u", "x-ui", "-n", "40", "--no-pager"])
            if log_res and log_res.stdout:
                console.print(Panel(log_res.stdout, title="Лог 3x-ui (journalctl)", border_style="green"))
            else:
                console.print("[yellow]Лог недоступен или пуст.[/yellow]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "xui_log":
            res = run_command(["x-ui", "log"])
            if res and res.stdout:
                console.print(Panel(res.stdout, title="x-ui log", border_style="green"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "banlog":
            res = run_command(["x-ui", "banlog"])
            if res and res.stdout:
                console.print(Panel(res.stdout, title="x-ui banlog", border_style="green"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "update":
            run_command(["x-ui", "update"], spinner_message="Обновление 3x-ui...")
        elif action == "reset_pass":
            console.print("[yellow]Сброс пароля: будет установлен admin/admin[/yellow]")
            run_command(["x-ui", "reset", "--username", "admin", "--password", "admin"], spinner_message="Сброс пароля...")
            console.print("[green]Пароль сброшен: admin/admin[/green]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "open":
            # Показываем актуальную ссылку
            console.print(Panel(f"Откройте в браузере: {url}", title="Веб-интерфейс 3x-ui", border_style="cyan"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "uninstall":
            _handle_uninstall("3x-ui")
            break
        else:
            break

def _show_actions_menu(key):
    data = SUPPORTED_SOFTWARE[key]
    is_installed = _is_package_installed(key)
    
    # --- Добавим спец.меню для 3x-ui ---
    if key == "3x-ui" and is_installed:
        _show_3xui_menu()
        return
    # --- стандартное меню для остальных ---
    while True:
        try:
            clear_console()
            status_markup = get_string("status_installed") if is_installed else get_string("status_not_installed")
            status_text = strip_rich_markup(status_markup)
            title = f"{data['display_name']} - [{status_text}]"
            console.print(Panel(title, style="bold blue"))

            choices = []
            if is_installed:
                if data.get("service_name"):
                    choices.append(Choice("manage", name=get_string("action_manage_service")))
                if data.get("version_cmd"):
                    choices.append(Choice("version", name=get_string("action_check_version")))
                choices.append(Choice("uninstall", name=get_string("action_uninstall")))
            else:
                choices.append(Choice("install", name=get_string("action_install")))
            choices.append(Choice(None, name=get_string("action_back")))

            action = inquirer.select(
                message=get_string("actions_prompt", package=data['display_name']),
                choices=choices,
                vi_mode=True
            ).execute()

            if action is None:
                break
            if action == "install":
                _handle_install(key)
                break
            elif action == "uninstall":
                _handle_uninstall(key)
                break
            elif action == "version":
                _handle_version_check(key)
            elif action == "manage":
                _show_service_menu(key)
        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break

def run_software_manager():
    """Presents a menu to manage predefined software."""
    style = get_style({
        "pointer": "fg:ansiyellow bold",
    }, style_override=False)

    while True:
        try:
            choices = []
            with console.status("[bold yellow]Checking software status...[/bold yellow]"):
                for key, data in SUPPORTED_SOFTWARE.items():
                    installed = _is_package_installed(key)
                    status_markup = get_string("status_installed") if installed else get_string("status_not_installed")
                    status_text = strip_rich_markup(status_markup)
                    
                    name_text = f"{data['display_name']:<20}"
                    choice_name = f"{name_text} [{status_text}]"
                    choices.append(Choice(value=key, name=choice_name))
            
            choices.append(Choice(value=None, name=get_string("back_to_main_menu")))

            clear_console()
            console.print(Panel(get_string("manager_title"), style="bold green"))
            
            selected_key = inquirer.select(
                message=get_string("manager_prompt"),
                choices=choices,
                vi_mode=True,
                pointer="» ",
                style=style
            ).execute()

            if selected_key is None:
                break
            
            _show_actions_menu(selected_key)

        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            break
        except Exception as e:
            console.print(f"[red]An error occurred in the software manager: {e}[/red]")
            # Log the full error for debugging
            import traceback
            console.print(traceback.format_exc())
            inquirer.text(message="Press enter to exit manager").execute()
            break 

def webmin_settings_menu():
    conf_path = '/etc/webmin/miniserv.conf'
    def read_settings():
        settings = {'port': '10000', 'ssl': '1'}
        try:
            with open(conf_path, 'r') as f:
                for line in f:
                    if line.startswith('port='):
                        settings['port'] = line.strip().split('=',1)[1]
                    if line.startswith('ssl='):
                        settings['ssl'] = line.strip().split('=',1)[1]
        except Exception:
            pass
        return settings
    def write_setting(key, value):
        lines = []
        try:
            with open(conf_path, 'r') as f:
                lines = f.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f'{key}='):
                    lines[i] = f'{key}={value}\n'
                    found = True
            if not found:
                lines.append(f'{key}={value}\n')
            with open(conf_path, 'w') as f:
                f.writelines(lines)
        except Exception as e:
            return str(e)
        return None
    def restart_webmin():
        run_command(['systemctl', 'restart', 'webmin'], get_string('service_restart'))
    while True:
        settings = read_settings()
        ssl_status = get_string('webmin_ssl_on') if settings['ssl'] == '1' else get_string('webmin_ssl_off')
        port = settings['port']
        choice = inquirer.select(
            message=get_string('webmin_settings_menu'),
            choices=[
                get_string('webmin_show_settings').format(port=port, ssl=ssl_status),
                get_string('webmin_change_port'),
                get_string('webmin_toggle_ssl'),
                get_string('webmin_change_pass'),
                get_string('webmin_autostart'),
                get_string('webmin_settings_back'),
            ]).execute()
        if choice == get_string('webmin_show_settings').format(port=port, ssl=ssl_status):
            console.print(Panel(f"{get_string('webmin_current_port').format(port=port)}\n{get_string('webmin_current_ssl').format(ssl=ssl_status)}", title=get_string('webmin_settings_menu')))
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('webmin_change_port'):
            new_port = inquirer.text(message=get_string('webmin_enter_new_port')).execute()
            if re.match(r'^\d{2,5}$', new_port):
                err = write_setting('port', new_port)
                if not err:
                    console.print(get_string('webmin_port_changed').format(port=new_port))
                    restart_webmin()
                else:
                    console.print(f"[red]{err}[/red]")
            else:
                console.print("[red]Некорректный порт[/red]")
        elif choice == get_string('webmin_toggle_ssl'):
            new_ssl = '0' if settings['ssl'] == '1' else '1'
            err = write_setting('ssl', new_ssl)
            if not err:
                if new_ssl == '1':
                    console.print(get_string('webmin_ssl_enabled'))
                else:
                    console.print(get_string('webmin_ssl_disabled'))
                restart_webmin()
            else:
                console.print(f"[red]{err}[/red]")
        elif choice == get_string('webmin_change_pass'):
            new_pass = getpass.getpass(get_string('webmin_change_pass')+': ')
            if new_pass:
                res = run_command(['/usr/share/webmin/changepass.pl', '/etc/webmin', 'root', new_pass], get_string('webmin_change_pass'))
                if res and res.returncode == 0:
                    console.print(get_string('webmin_pass_changed'))
                else:
                    console.print("[red]Ошибка смены пароля[/red]")
        elif choice == get_string('webmin_autostart'):
            res = run_command(['systemctl', 'enable', 'webmin'], get_string('webmin_autostart'))
            if res and res.returncode == 0:
                console.print(get_string('webmin_autostart_on'))
            else:
                res2 = run_command(['systemctl', 'disable', 'webmin'], get_string('webmin_autostart'))
                if res2 and res2.returncode == 0:
                    console.print(get_string('webmin_autostart_off'))
        elif choice == get_string('webmin_settings_back'):
            break 

def pterodactyl_manage_menu():
    def get_panel_url():
        # По умолчанию http://<ip>/ или http://localhost/
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return f"http://{ip}/"
        except:
            return "http://localhost/"
    while True:
        choice = inquirer.select(
            message=get_string('pterodactyl_manage_menu'),
            choices=[
                get_string('service_status'),
                get_string('service_start'),
                get_string('service_stop'),
                get_string('service_restart'),
                get_string('pterodactyl_open_panel'),
                get_string('pterodactyl_add_server'),
                get_string('action_back'),
            ]).execute()
        if choice == get_string('service_status'):
            res = run_command(['systemctl', 'status', 'pterodactyl-panel'], get_string('service_status'))
            if res:
                console.print(Panel(res.stdout or res.stderr, title=get_string('service_status')))
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('service_start'):
            run_command(['systemctl', 'start', 'pterodactyl-panel'], get_string('service_start'))
        elif choice == get_string('service_stop'):
            run_command(['systemctl', 'stop', 'pterodactyl-panel'], get_string('service_stop'))
        elif choice == get_string('service_restart'):
            run_command(['systemctl', 'restart', 'pterodactyl-panel'], get_string('service_restart'))
        elif choice == get_string('pterodactyl_open_panel'):
            url = get_panel_url()
            console.print(f"[green]Открываю панель: {url}[/green]")
            try:
                webbrowser.open(url)
            except Exception:
                pass
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('pterodactyl_add_server'):
            console.print("[yellow]Добавление сервера реализуется через веб-интерфейс панели Pterodactyl![/yellow]")
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('action_back'):
            break 

def wings_manage_menu():
    from rich.panel import Panel
    from InquirerPy import inquirer
    import webbrowser
    while True:
        choice = inquirer.select(
            message=get_string('wings_manage_menu'),
            choices=[
                get_string('wings_status'),
                get_string('wings_start'),
                get_string('wings_stop'),
                get_string('wings_restart'),
                get_string('wings_open_docs'),
                get_string('wings_remove'),
                get_string('action_back'),
            ]).execute()
        if choice == get_string('wings_status'):
            res = run_command(['systemctl', 'status', 'wings'], get_string('wings_status'))
            if res:
                console.print(Panel(res.stdout or res.stderr, title=get_string('wings_status')))
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('wings_start'):
            run_command(['systemctl', 'start', 'wings'], get_string('wings_start'))
        elif choice == get_string('wings_stop'):
            run_command(['systemctl', 'stop', 'wings'], get_string('wings_stop'))
        elif choice == get_string('wings_restart'):
            run_command(['systemctl', 'restart', 'wings'], get_string('wings_restart'))
        elif choice == get_string('wings_open_docs'):
            webbrowser.open('https://pterodactyl.io/wings/1.11/installing.html')
            console.print(get_string('wings_connect_guide'))
            inquirer.text(message=get_string('press_enter_to_continue')).execute()
        elif choice == get_string('wings_remove'):
            confirm = inquirer.confirm(message=get_string('uninstall_confirm', package='Wings')).execute()
            if confirm:
                run_command(['systemctl', 'stop', 'wings'], get_string('wings_stop'))
                run_command(['systemctl', 'disable', 'wings'], get_string('wings_stop'))
                run_command(['rm', '-f', '/etc/systemd/system/wings.service', '/usr/local/bin/wings'], 'Удаление файлов Wings...')
                run_command(['systemctl', 'daemon-reload'], 'Перезагрузка systemd...')
                console.print(get_string('uninstall_success', package='Wings'))
                inquirer.text(message=get_string('press_enter_to_continue')).execute()
                break
        elif choice == get_string('action_back'):
            break

def java_diagnostics():
    from rich.panel import Panel
    paths_checked = []
    found_path = None
    # 1. Проверка через which
    java_path = shutil.which('java')
    if java_path:
        console.print(Panel(get_string('java_found_in_path').format(path=java_path), title=get_string('java_diagnostics_title'), border_style='green'))
        found_path = java_path
    else:
        # 2. Проверка стандартных путей
        std_paths = ['/usr/bin/java', '/usr/local/bin/java', '/usr/lib/jvm/java-17-openjdk-amd64/bin/java']
        for p in std_paths:
            paths_checked.append(p)
            if os.path.exists(p) and os.access(p, os.X_OK):
                console.print(Panel(get_string('java_found_in_std').format(path=p), title=get_string('java_diagnostics_title'), border_style='green'))
                found_path = p
                break
    if not found_path:
        console.print(Panel(get_string('java_not_in_path'), title=get_string('java_diagnostics_title'), border_style='red'))
        manual = inquirer.confirm(message='Указать путь к java вручную?', default=False).execute()
        if manual:
            user_path = inquirer.text(message=get_string('java_manual_path_prompt')).execute()
            if os.path.exists(user_path) and os.access(user_path, os.X_OK):
                # Проверим запуск
                try:
                    res = subprocess.run([user_path, '-version'], capture_output=True, text=True)
                    if res.returncode == 0:
                        with open(JAVA_PATH_CONFIG, 'w') as f:
                            f.write(user_path.strip())
                        console.print(get_string('java_manual_path_success').format(path=user_path))
                        found_path = user_path
                    else:
                        console.print(get_string('java_manual_path_fail'))
                except Exception:
                    console.print(get_string('java_manual_path_fail'))
            else:
                console.print(get_string('java_manual_path_fail'))
    if found_path:
        with open(JAVA_PATH_CONFIG, 'w') as f:
            f.write(found_path.strip())
    inquirer.text(message=get_string('press_enter_to_continue')).execute() 