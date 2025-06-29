import os
import shutil
import subprocess
import socket
import time
import platform
import webbrowser
from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from localization import get_string
from modules.panel_utils import clear_console, run_command
import re
# --- Автоматическая установка pymysql ---
try:
    import pymysql
except ImportError:
    import sys
    import subprocess
    print("[yellow]pymysql не найден, пробую установить...[/yellow]")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pymysql'])
        import pymysql
        print("[green]pymysql успешно установлен![/green]")
    except Exception as e:
        print(f"[red]Не удалось установить pymysql: {e}[/red]")
        raise

console = Console()

def _get_pterodactyl_info():
    db_path = '/var/www/pterodactyl/.env'
    # Статус nginx
    nginx_status = run_command_with_dpkg_fix('systemctl is-active nginx')
    nginx_status_str = nginx_status.stdout.strip() if nginx_status and nginx_status.returncode == 0 else 'unknown'
    # Статус pteroq
    pteroq_status = run_command_with_dpkg_fix('systemctl is-active pteroq.service')
    pteroq_status_str = pteroq_status.stdout.strip() if pteroq_status and pteroq_status.returncode == 0 else 'unknown'
    # Определение URL панели
    url = None
    port = None
    ssl = False
    domain = None
    nginx_conf = '/etc/nginx/sites-available/pterodactyl.conf'
    if os.path.exists(nginx_conf):
        with open(nginx_conf, 'r') as f:
            conf = f.read()
            m = re.search(r'server_name\s+([^;\s]+)', conf)
            if m:
                domain = m.group(1).replace('"', '').replace("'", "")
            m2 = re.search(r'listen\s+(\d+)(?:\s+ssl)?', conf)
            if m2:
                port = m2.group(1)
            # ssl_certificate должен быть в конфиге И nginx реально слушает 443
            if 'ssl_certificate' in conf:
                # Проверяем, слушает ли nginx 443
                import subprocess
                try:
                    res = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
                    if res.returncode == 0 and ':443' in res.stdout:
                        ssl = True
                except Exception:
                    pass
    # Получить IP сервера
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = '127.0.0.1'
    # Сформировать URL
    if domain:
        domain = domain.replace('"', '').replace("'", "")
        url = f"{'https' if ssl else 'http'}://{domain}"
        if port and port not in ('80', '443'):
            url += f":{port}"
    else:
        url = f"{'https' if ssl else 'http'}://{ip}"
        if port and port not in ('80', '443'):
            url += f":{port}"
    # Проверка APP_URL в .env
    app_url = None
    if os.path.exists(db_path):
        with open(db_path) as f:
            env = f.read()
            m = re.search(r'APP_URL=(.*)', env)
            if m:
                app_url = m.group(1).strip()
    # Если ssl=True, а APP_URL не https — автоматически исправить
    if ssl and app_url and not app_url.startswith('https://'):
        # Автоматическая правка .env
        with open(db_path, 'r') as f:
            lines = f.readlines()
        with open(db_path, 'w') as f:
            for line in lines:
                if line.startswith('APP_URL='):
                    f.write(f'APP_URL=https://{domain}\n')
                else:
                    f.write(line)
        console.print(Panel(f"[green]APP_URL в .env автоматически исправлен на https://{domain}!\nПерезапускаю nginx и php-fpm...[/green]", title="APP_URL исправлен", border_style="green"))
        # Перезапуск сервисов
        import subprocess
        subprocess.run(['systemctl', 'restart', 'nginx'])
        subprocess.run(['systemctl', 'restart', 'php8.3-fpm'])
        # Обновить app_url для дальнейшего использования
        app_url = f'https://{domain}'
    # Если ssl=True, а APP_URL не https — предупреждение
    if ssl and app_url and not app_url.startswith('https://'):
        console.print(Panel(f"[yellow]Внимание: SSL включён, но APP_URL в .env не начинается с https!\nТекущий APP_URL: {app_url}\nРекомендуется исправить на https://{domain} и перезапустить nginx и php-fpm.[/yellow]", title="APP_URL и SSL", border_style="yellow"))
    # Данные БД (если есть)
    db_info = None
    if os.path.exists(db_path):
        with open(db_path) as f:
            env = f.read()
            db_user = re.search(r'DB_USERNAME=(.*)', env)
            db_pass = re.search(r'DB_PASSWORD=(.*)', env)
            db_name = re.search(r'DB_DATABASE=(.*)', env)
            if db_user and db_pass and db_name:
                db_info = f"{db_name.group(1)} / {db_user.group(1)} / {db_pass.group(1)}"
    # Данные админа (если создавались автоматически — можно хранить в отдельном файле)
    admin_info = None # (можно реализовать сохранение при автоматическом создании)
    return {
        'nginx': nginx_status_str,
        'pteroq': pteroq_status_str,
        'url': url,
        'port': port,
        'ssl': ssl,
        'db': db_info,
        'admin': admin_info
    }

def pterodactyl_manage_menu():
    clear_console()
    if not os.path.exists('/var/www/pterodactyl'):
        console.print(Panel("[red]Pterodactyl не установлен![/red]\n\n[bold yellow]Для управления сначала выполните установку панели.[/bold yellow]\n\n[cyan]Документация: https://pterodactyl.io/panel/1.11/getting_started.html[/cyan]", title="Pterodactyl не установлен", border_style="red"))
        choice = inquirer.select(
            message=get_string("pterodactyl_manage_menu_choice"),
            choices=[
                "Установить Pterodactyl",
                "Назад"
            ]).execute()
        if choice == "Установить Pterodactyl":
            pterodactyl_install_wizard()
        return
    while True:
        clear_console()
        info = _get_pterodactyl_info()
        status_panel = f"[bold]Статус nginx:[/bold] [cyan]{info['nginx']}[/cyan]  |  [bold]pteroq:[/bold] [cyan]{info['pteroq']}[/cyan]\n"
        status_panel += f"[bold]URL панели:[/bold] [green]{info['url']}[/green]  |  [bold]Порт:[/bold] [cyan]{info['port'] or '80/443'}[/cyan]  |  [bold]SSL:[/bold] [cyan]{'да' if info['ssl'] else 'нет'}[/cyan]\n"
        if info['db']:
            status_panel += f"[bold]БД:[/bold] [magenta]{info['db']}[/magenta]\n"
        if info['admin']:
            status_panel += f"[bold]Админ:[/bold] [magenta]{info['admin']}[/magenta]\n"
        console.print(Panel(status_panel, title="Pterodactyl Panel", border_style="cyan"))
        choices = [
            "Открыть веб-панель",
            "Artisan-команды",
            "Статус/перезапуск pteroq (systemd)",
            "Просмотр логов панели",
            "Просмотр логов pteroq",
            "Проверить версию панели",
            "Удалить Pterodactyl",
            "Назад"
        ]
        action = inquirer.select(message=get_string("pterodactyl_manage_menu_action"), choices=choices).execute()
        if action == "Открыть веб-панель":
            url = info['url'] or inquirer.text(message="Введите URL панели (например, https://your-domain):", default="https://127.0.0.1").execute()
            import webbrowser
            webbrowser.open(url)
            console.print(f"[green]Открыто в браузере: {url}[/green]")
            inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Artisan-команды":
            artisan_choices = [
                "php artisan p:environment:setup",
                "php artisan p:environment:database",
                "php artisan p:environment:mail",
                "php artisan migrate --seed --force",
                "php artisan cache:clear",
                "php artisan config:clear",
                "php artisan queue:restart",
                "php artisan p:user:make",
                "php artisan --version",
                "Назад"
            ]
            artisan_cmd = inquirer.select(message=get_string("pterodactyl_manage_menu_artisan_cmd"), choices=artisan_choices).execute()
            if artisan_cmd != "Назад":
                res = run_command_with_dpkg_fix(f'cd /var/www/pterodactyl && {artisan_cmd}', spinner_message=f"{artisan_cmd} ...")
                if res and res.returncode == 0:
                    console.print(Panel(res.stdout or "[green]Команда выполнена успешно![/green]", title="Artisan output", border_style="green"))
                else:
                    console.print(Panel((res.stderr or res.stdout or "[red]Ошибка artisan[/red]"), title="Artisan error", border_style="red"))
                inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Статус/перезапуск pteroq (systemd)":
            sys_choices = [
                "systemctl status pteroq.service",
                "systemctl restart pteroq.service",
                "systemctl stop pteroq.service",
                "systemctl start pteroq.service",
            ]
            if not _pteroq_unit_exists():
                sys_choices.insert(0, "Создать systemd unit pteroq")
            sys_choices.append("Назад")
            sys_cmd = inquirer.select(message=get_string("pterodactyl_manage_menu_pteroq_status"), choices=sys_choices).execute()
            if sys_cmd == "Создать systemd unit pteroq":
                _create_pteroq_unit()
                inquirer.text(message="Нажмите Enter для возврата...").execute()
                continue
            if sys_cmd != "Назад":
                res = run_command_with_dpkg_fix(sys_cmd, spinner_message=f"{sys_cmd} ...")
                if res and res.returncode == 0:
                    console.print(Panel(res.stdout or "[green]Операция выполнена![green]", title="systemd output", border_style="green"))
                else:
                    if res and 'not found' in (res.stderr or ''):
                        console.print(Panel("[red]systemd unit pteroq.service не найден![/red]\nВы можете создать его автоматически.", title="systemd error", border_style="red"))
                    else:
                        console.print(Panel((res.stderr or res.stdout or "[red]Ошибка systemd[red]"), title="systemd error", border_style="red"))
                inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Просмотр логов панели":
            res = run_command_with_dpkg_fix('journalctl -u nginx -n 50 --no-pager', spinner_message="Логи nginx...")
            res2 = run_command_with_dpkg_fix('tail -n 50 /var/www/pterodactyl/storage/logs/laravel.log', spinner_message="Логи laravel...")
            console.print(Panel((res.stdout or "") + "\n" + (res2.stdout or ""), title="Последние логи панели", border_style="cyan"))
            inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Просмотр логов pteroq":
            res = run_command_with_dpkg_fix('journalctl -u pteroq.service -n 50 --no-pager', spinner_message="Логи pteroq...")
            console.print(Panel(res.stdout or "[yellow]Лог пуст или недоступен[/yellow]", title="Логи pteroq", border_style="cyan"))
            inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Проверить версию панели":
            res = run_command_with_dpkg_fix('cd /var/www/pterodactyl && php artisan --version', spinner_message="Проверка версии...")
            if res and res.returncode == 0:
                console.print(Panel(res.stdout or "[green]Версия получена![/green]", title="Версия панели", border_style="green"))
            else:
                console.print(Panel((res.stderr or res.stdout or "[red]Ошибка версии[/red]"), title="Ошибка", border_style="red"))
            inquirer.text(message="Enter для возврата в меню...").execute()
        elif action == "Удалить Pterodactyl":
            confirm = inquirer.confirm(message=get_string("pterodactyl_manage_menu_delete_confirm"), default=False).execute()
            if confirm:
                pterodactyl_full_uninstall()
                break
        elif action == "Назад":
            break

def _ensure_nginx_pterodactyl(domain=None, ssl=False):
    import subprocess
    nginx_conf_path = '/etc/nginx/sites-available/pterodactyl.conf'
    nginx_enabled_path = '/etc/nginx/sites-enabled/pterodactyl.conf'
    if not domain:
        # Попробовать получить из .env
        env_path = '/var/www/pterodactyl/.env'
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith('APP_URL='):
                        domain = line.strip().split('=',1)[1].replace('https://','').replace('http://','').split(':')[0]
                        break
    if not domain:
        domain = inquirer.text(message="Введите домен для панели (или IP):", default="panel.example.com").execute()
        domain = domain.replace('"', '').replace("'", "")
    # Определяем актуальный php-fpm сокет
    php_fpm_sock = get_installed_php_fpm_sock()
    # Генерируем конфиг
    conf = f'''
server {{
    listen 80;
    server_name {domain};
    root /var/www/pterodactyl/public;
    index index.php index.html index.htm;
    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}
    location ~ \\.(php|phar)(/|$) {{
        fastcgi_split_path_info ^(.+?\\.ph(?:p|ar))(/.*)$;
        fastcgi_pass unix:{php_fpm_sock};
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param PATH_INFO $fastcgi_path_info;
        fastcgi_param HTTP_PROXY "";
        internal;
    }}
    location ~ /\\.ht {{
        deny all;
    }}
    client_max_body_size 100m;
    sendfile off;
}}
'''
    with open(nginx_conf_path, 'w') as f:
        f.write(conf)
    # Симлинк
    if not os.path.exists(nginx_enabled_path):
        os.symlink(nginx_conf_path, nginx_enabled_path)
    # Проверка nginx -t
    result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    if result.returncode != 0:
        console.print(Panel(f"[red]Ошибка в конфиге nginx:[/red]\n{result.stderr}", title="nginx -t error", border_style="red"))
        raise Exception("nginx config error")
    # Перезапуск nginx
    subprocess.run(['systemctl', 'reload', 'nginx'])
    console.print(Panel(f"[green]nginx сконфигурирован для панели {domain} и перезапущен![green]", title="nginx", border_style="green"))

def pterodactyl_install_wizard():
    import distro
    clear_console()
    console.print(Panel("[bold cyan]Pterodactyl: мастер установки для Debian 11/12[/bold cyan]", title="Pterodactyl Install Wizard", border_style="cyan"))
    inquirer.text(message="Нажмите Enter для старта...").execute()

    # 1. Проверка root
    if os.geteuid() != 0:
        console.print(Panel("[red]Установку можно выполнять только от root![/red]", title="Ошибка", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return

    # 2. Установка базовых пакетов
    console.print(Panel("Установка базовых пакетов (curl, ca-certificates, gnupg2, sudo, lsb-release)...", title="Шаг 1", border_style="yellow"))
    res = run_command_with_dpkg_fix("apt -y install software-properties-common curl ca-certificates gnupg2 sudo lsb-release", spinner_message="Установка базовых пакетов...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка установки базовых пакетов[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Базовые пакеты установлены![/green]")

    # 3. Добавление репозитория PHP (sury.org)
    console.print(Panel("Добавление репозитория PHP (sury.org)...", title="Шаг 2", border_style="yellow"))
    res = run_command_with_dpkg_fix('echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/sury-php.list', spinner_message="Добавление репозитория sury.org...")
    res2 = run_command_with_dpkg_fix('curl -fsSL https://packages.sury.org/php/apt.gpg | gpg --yes --dearmor -o /etc/apt/trusted.gpg.d/sury-keyring.gpg', spinner_message="Импорт GPG ключа sury.org...")
    if (res and res.returncode != 0) or (res2 and res2.returncode != 0):
        console.print(Panel((res.stderr or '') + '\n' + (res2.stderr or ''), title="[red]Ошибка добавления репозитория PHP[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий PHP добавлен![/green]")

    # 4. Добавление репозитория Redis
    console.print(Panel("Добавление репозитория Redis...", title="Шаг 3", border_style="yellow"))
    res = run_command_with_dpkg_fix('curl -fsSL https://packages.redis.io/gpg | gpg --yes --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg', spinner_message="Импорт GPG ключа Redis...")
    res2 = run_command_with_dpkg_fix('echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list', spinner_message="Добавление репозитория Redis...")
    if (res and res.returncode != 0) or (res2 and res2.returncode != 0):
        console.print(Panel((res.stderr or '') + '\n' + (res2.stderr or ''), title="[red]Ошибка добавления репозитория Redis[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий Redis добавлен![/green]")

    # 5. MariaDB repo setup
    console.print(Panel("Добавление репозитория MariaDB...", title="Шаг 4", border_style="yellow"))
    res = run_command_with_dpkg_fix('curl -LsS https://r.mariadb.com/downloads/mariadb_repo_setup | sudo bash', spinner_message="MariaDB repo setup...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка MariaDB repo setup[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий MariaDB добавлен![/green]")

    # 6. apt update
    console.print(Panel("Обновление списка пакетов...", title="Шаг 5", border_style="yellow"))
    res = run_command_with_dpkg_fix('apt update', spinner_message="apt update...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка apt update[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Список пакетов обновлён![/green]")

    # 7. Установка зависимостей
    dependencies_list = [
        "php8.3", "php8.3-common", "php8.3-cli", "php8.3-gd", "php8.3-mysql", "php8.3-mbstring", "php8.3-bcmath", "php8.3-xml", "php8.3-fpm", "php8.3-curl", "php8.3-zip",
        "mariadb-server", "nginx", "tar", "unzip", "git", "redis-server"
    ]
    console.print(Panel(
        "[bold yellow]Установка зависимостей (примерно 2-5 минут, зависит от скорости сети и системы)...[/bold yellow]\n"
        "Пакеты: [cyan]" + ", ".join(dependencies_list) + "[cyan]",
        title="Шаг 6: Установка зависимостей", border_style="yellow"))
    installed = []
    already = []
    failed = []
    for pkg in dependencies_list:
        console.print(f"[cyan]Устанавливается: {pkg} ...[/cyan]")
        check = run_command_with_dpkg_fix(f"dpkg -s {pkg}", spinner_message=f"Проверка {pkg}...")
        if check and check.returncode == 0:
            console.print(f"[yellow]{pkg} уже установлен.[/yellow]")
            already.append(pkg)
            continue
        res = run_command_with_dpkg_fix(f"apt install -y {pkg}", spinner_message=f"Установка {pkg}...")
        if res and res.returncode == 0:
            console.print(f"[green]{pkg} успешно установлен![green]")
            installed.append(pkg)
        else:
            console.print(f"[red]Ошибка при установке {pkg}![red]")
            if res:
                if res.stderr:
                    console.print(Panel(res.stderr, title=f"[red]apt-get stderr для {pkg}[red]", border_style="red"))
                if res.stdout:
                    console.print(Panel(res.stdout, title=f"[yellow]apt-get stdout для {pkg}[yellow]", border_style="yellow"))
            console.print("[bold]Возможные причины:[/bold] Нет интернета, проблемы с репозиториями, конфликт пакетов, недостаточно места, dpkg/apt заблокирован.")
            failed.append(pkg)
    summary = ""
    if installed:
        summary += "[green]Установлены:[green] " + ", ".join(installed) + "\n"
    if already:
        summary += "[yellow]Уже были:[yellow] " + ", ".join(already) + "\n"
    if failed:
        summary += "[red]Не удалось установить:[red] " + ", ".join(failed) + "\n"
    if not failed:
        summary += "[bold green]Все зависимости установлены![bold green]"
    else:
        summary += "[bold red]Есть ошибки! Проверьте вывод выше и устраните проблемы вручную.[bold red]"
    console.print(Panel(summary, title="Итог установки зависимостей", border_style="green" if not failed else "red"))

    # 8. Установка Composer
    console.print(Panel("Установка Composer...", title="Шаг 7", border_style="yellow"))
    res = run_command_with_dpkg_fix('curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer', spinner_message="Установка Composer...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка установки Composer[red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Composer установлен![green]")

    # 9. Скачивание и распаковка панели
    console.print(Panel("Скачивание и распаковка Pterodactyl Panel...", title="Шаг 8", border_style="yellow"))
    run_command_with_dpkg_fix('mkdir -p /var/www/pterodactyl', spinner_message="Создание директории...")
    run_command_with_dpkg_fix('cd /var/www/pterodactyl && curl -Lo panel.tar.gz https://github.com/pterodactyl/panel/releases/latest/download/panel.tar.gz', spinner_message="Скачивание архива панели...")
    run_command_with_dpkg_fix('cd /var/www/pterodactyl && tar -xzvf panel.tar.gz', spinner_message="Распаковка архива...")
    run_command_with_dpkg_fix('cd /var/www/pterodactyl && chmod -R 755 storage/* bootstrap/cache/', spinner_message="Права на storage и cache...")
    console.print("[green]Файлы панели скачаны и распакованы![green]")

    # 10. Инструкция/автоматизация по созданию БД
    console.print(Panel(get_string("pterodactyl_db_step_panel"), title="Шаг 9: База данных", border_style="yellow"))
    auto_db = inquirer.confirm(message=get_string("pterodactyl_manage_menu_db_auto"), default=True).execute()
    if auto_db:
        import secrets
        import string
        db_user = "pterodactyl"
        db_name = "panel"
        db_pass = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        console.print(f"[cyan]Имя БД:[/cyan] {db_name}\n[cyan]Пользователь:[/cyan] {db_user}\n[cyan]Пароль:[/cyan] {db_pass}")
        console.print(Panel(get_string("pterodactyl_manage_menu_db_socket_help"), title="Подсказка", border_style="cyan"))
        use_socket = inquirer.confirm(message=get_string("pterodactyl_manage_menu_db_socket"), default=True).execute()
        sql = f"CREATE USER IF NOT EXISTS '{db_user}'@'127.0.0.1' IDENTIFIED BY '{db_pass}'; CREATE DATABASE IF NOT EXISTS {db_name}; GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;"
        if use_socket:
            cmd = f"mariadb -u root --execute=\"{sql}\""
        else:
            root_pass = inquirer.text(message="Введите пароль root MariaDB:").execute()
            cmd = f"mariadb -u root -p{root_pass} --execute=\"{sql}\""
        res = run_command_with_dpkg_fix(cmd, spinner_message="Создание БД и пользователя...")
        if res and res.returncode == 0:
            # Прописываем DB_HOST=127.0.0.1 в .env
            env_path = '/var/www/pterodactyl/.env'
            if os.path.exists(env_path):
                lines = []
                with open(env_path) as f:
                    for line in f:
                        if line.startswith('DB_HOST='):
                            lines.append('DB_HOST=127.0.0.1\n')
                        elif line.startswith('DB_PASSWORD='):
                            lines.append(f'DB_PASSWORD={db_pass}\n')
                        elif line.startswith('DB_USERNAME='):
                            lines.append(f'DB_USERNAME={db_user}\n')
                        elif line.startswith('DB_DATABASE='):
                            lines.append(f'DB_DATABASE={db_name}\n')
                        else:
                            lines.append(line)
                with open(env_path, 'w') as f:
                    f.writelines(lines)
            console.print(Panel(f"[green]База данных и пользователь успешно созданы![green]\n\n[cyan]Имя БД:[/cyan] {db_name}\n[cyan]Пользователь:[/cyan] {db_user}\n[cyan]Пароль:[/cyan] {db_pass}\n\n[bold yellow]Сохраните эти параметры![bold yellow]", title="БД создана", border_style="green"))
        else:
            console.print(Panel(f"[red]Ошибка автоматического создания БД![red]\n\nПопробуйте выполнить шаг вручную.\n\n[bold]Пример для MariaDB:[/bold]\n\n[cyan]mariadb -u root -p[cyan]\n\n[cyan]CREATE USER '{db_user}'@'127.0.0.1' IDENTIFIED BY '{db_pass}';\nCREATE DATABASE {db_name};\nGRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'127.0.0.1' WITH GRANT OPTION;\nFLUSH PRIVILEGES;\nexit[cyan]", title="Ошибка создания БД", border_style="red"))
            inquirer.text(message="Нажмите Enter, когда база данных будет готова...").execute()
    else:
        console.print(Panel("[bold]Пример для MariaDB:[/bold]\n\n[cyan]mariadb -u root -p[cyan]\n\n[cyan]CREATE USER 'pterodactyl'@'127.0.0.1' IDENTIFIED BY 'yourPassword';\nCREATE DATABASE panel;\nGRANT ALL PRIVILEGES ON panel.* TO 'pterodactyl'@'127.0.0.1' WITH GRANT OPTION;\nFLUSH PRIVILEGES;\nexit[cyan]\n\n[bold yellow]Скопируйте команды выше и выполните их в отдельном терминале![bold yellow]", title="Ручное создание БД", border_style="yellow"))
        inquirer.text(message="Нажмите Enter, когда база данных будет готова...").execute()

    # 11. Установка зависимостей через composer
    console.print(Panel("Установка зависимостей через composer...", title="Шаг 10", border_style="yellow"))
    res = run_command_with_dpkg_fix('cd /var/www/pterodactyl && COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --optimize-autoloader', spinner_message="composer install...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка composer install[red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Composer зависимости установлены![green]")

    # 12. Генерация ключа приложения
    console.print(Panel("Генерация ключа приложения...", title="Шаг 11", border_style="yellow"))
    env_path = '/var/www/pterodactyl/.env'
    env_example_path = '/var/www/pterodactyl/.env.example'
    if not os.path.exists(env_path):
        if os.path.exists(env_example_path):
            res_cp = run_command_with_dpkg_fix(f'cp {env_example_path} {env_path}', spinner_message="Копирование .env.example -> .env ...")
            if res_cp and res_cp.returncode != 0:
                console.print(Panel(res_cp.stderr or res_cp.stdout or "Не удалось скопировать .env.example", title="[red]Ошибка копирования .env[red]", border_style="red"))
                inquirer.text(message="Нажмите Enter для выхода...").execute()
                return
        else:
            console.print(Panel("[red].env.example не найден! Не могу создать .env[red]", title="Ошибка .env", border_style="red"))
            inquirer.text(message="Нажмите Enter для выхода...").execute()
            return
    res = run_command_with_dpkg_fix('cd /var/www/pterodactyl && php artisan key:generate --force', spinner_message="artisan key:generate...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка artisan key:generate[red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Ключ приложения сгенерирован![green]")

    # 13. Автоматизация artisan environment setup с дефолтами и возможностью меню
    # Определяем domain ДО defaults
    def get_default_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    env_path = '/var/www/pterodactyl/.env'
    domain = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('APP_URL='):
                    domain = line.strip().split('=',1)[1].replace('https://','').replace('http://','').split(':')[0]
                    break
    if not domain or domain in ("localhost", "127.0.0.1"):
        domain = get_default_ip()
    def get_env_value(key, default=None):
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith(key + '='):
                        return line.strip().split('=',1)[1]
        return default
    # Дефолты
    defaults = {
        'author': get_env_value('APP_SERVICE_AUTHOR', 'admin@' + domain),
        'url': f'https://{domain}',
        'timezone': get_env_value('APP_TIMEZONE', 'UTC'),
        'cache': get_env_value('CACHE_DRIVER', 'redis'),
        'session': get_env_value('SESSION_DRIVER', 'redis'),
        'queue': get_env_value('QUEUE_CONNECTION', 'redis'),
        'redis_host': get_env_value('REDIS_HOST', '127.0.0.1'),
        'redis_port': get_env_value('REDIS_PORT', '6379'),
        'redis_pass': get_env_value('REDIS_PASSWORD', ''),
        'settings_ui': get_env_value('APP_ENVIRONMENT_ONLY', 'false'),
        'telemetry': get_env_value('PTERODACTYL_TELEMETRY_ENABLED', 'true'),
        'db_host': get_env_value('DB_HOST', '127.0.0.1'),
        'db_port': get_env_value('DB_PORT', '3306'),
        'db_name': get_env_value('DB_DATABASE', 'panel'),
        'db_user': get_env_value('DB_USERNAME', 'pterodactyl'),
        'db_pass': get_env_value('DB_PASSWORD', ''),
        'mail_driver': get_env_value('MAIL_DRIVER', 'smtp'),
        'mail_from': get_env_value('MAIL_FROM_ADDRESS', 'admin@' + domain),
        'mail_name': get_env_value('MAIL_FROM_NAME', 'Pterodactyl'),
        'mail_host': get_env_value('MAIL_HOST', 'localhost'),
        'mail_port': get_env_value('MAIL_PORT', '25'),
        'mail_user': get_env_value('MAIL_USERNAME', ''),
        'mail_pass': get_env_value('MAIL_PASSWORD', ''),
        'mail_encryption': get_env_value('MAIL_ENCRYPTION', ''),
    }
    use_menu = inquirer.confirm(message=get_string("pterodactyl_manage_menu_settings"), default=False).execute()
    if use_menu:
        console.print(Panel(get_string("pterodactyl_manage_menu_settings_help"), title="Подсказка", border_style="cyan"))
        defaults['author'] = inquirer.text(message=get_string("pterodactyl_manage_menu_egg_author_email"), default=defaults['author']).execute()
        url_choices = [
            f"Текущий: {defaults['url']}",
            f"Использовать IP сервера ({get_default_ip()})",
            "Ввести вручную..."
        ]
        url_choice = inquirer.select(message=get_string("pterodactyl_manage_menu_url_choice"), choices=url_choices, default=url_choices[0]).execute()
        if url_choice.startswith("Использовать IP сервера"):
            defaults['url'] = f"https://{get_default_ip()}"
        elif url_choice == "Ввести вручную...":
            defaults['url'] = inquirer.text(message="Введите URL панели (https://...):", default=defaults['url']).execute()
        defaults['timezone'] = inquirer.text(message="Часовой пояс (например, UTC):", default=defaults['timezone']).execute()
        defaults['cache'] = inquirer.select(message=get_string("pterodactyl_manage_menu_cache_driver"), choices=['redis','memcached','file'], default=defaults['cache']).execute()
        defaults['session'] = inquirer.select(message=get_string("pterodactyl_manage_menu_session_driver"), choices=['redis','memcached','database','file','cookie'], default=defaults['session']).execute()
        defaults['queue'] = inquirer.select(message=get_string("pterodactyl_manage_menu_queue_driver"), choices=['redis','database','sync'], default=defaults['queue']).execute()
        defaults['redis_host'] = inquirer.text(message="Redis host:", default=defaults['redis_host']).execute()
        defaults['redis_port'] = inquirer.text(message="Redis port:", default=defaults['redis_port']).execute()
        defaults['redis_pass'] = inquirer.text(message="Redis password (оставьте пустым если нет):", default=defaults['redis_pass']).execute()
        defaults['settings_ui'] = inquirer.confirm(message=get_string("pterodactyl_manage_menu_settings_ui"), default=defaults['settings_ui']=='false').execute()
        defaults['telemetry'] = inquirer.confirm(message=get_string("pterodactyl_manage_menu_telemetry"), default=defaults['telemetry']=='true').execute()
        defaults['db_host'] = inquirer.text(message="DB host:", default=defaults['db_host']).execute()
        defaults['db_port'] = inquirer.text(message="DB port:", default=defaults['db_port']).execute()
        defaults['db_name'] = inquirer.text(message="DB name:", default=defaults['db_name']).execute()
        defaults['db_user'] = inquirer.text(message="DB user:", default=defaults['db_user']).execute()
        db_pass_input = inquirer.text(message=f"DB password (Enter для автозаполнения):", default="").execute()
        if not db_pass_input and defaults['db_pass']:
            console.print(f"[yellow]Используется сгенерированный пароль для БД: {defaults['db_pass']}[/yellow]")
        else:
            defaults['db_pass'] = db_pass_input
        defaults['mail_driver'] = inquirer.select(message="Mail driver:", choices=['smtp','sendmail','mailgun','mandrill','postmark'], default=defaults['mail_driver']).execute()
        defaults['mail_from'] = inquirer.text(message="Email отправителя (MAIL_FROM_ADDRESS):", default=defaults['mail_from']).execute()
        defaults['mail_name'] = inquirer.text(message="Имя отправителя (MAIL_FROM_NAME):", default=defaults['mail_name']).execute()
        defaults['mail_host'] = inquirer.text(message="SMTP host:", default=defaults['mail_host']).execute()
        defaults['mail_port'] = inquirer.text(message="SMTP port:", default=defaults['mail_port']).execute()
        defaults['mail_user'] = inquirer.text(message="SMTP user:", default=defaults['mail_user']).execute()
        defaults['mail_pass'] = inquirer.text(message="SMTP password:", default=defaults['mail_pass']).execute()
        defaults['mail_encryption'] = inquirer.select(message="SMTP encryption:", choices=['tls','ssl',''], default=defaults['mail_encryption']).execute()
    # Формируем параметры для artisan
    setup_args = [
        f"--author={defaults['author']}",
        f"--url={defaults['url']}",
        f"--timezone={defaults['timezone']}",
        f"--cache={defaults['cache']}",
        f"--session={defaults['session']}",
        f"--queue={defaults['queue']}",
        f"--redis-host={defaults['redis_host']}",
        f"--redis-port={defaults['redis_port']}",
        f"--redis-pass={defaults['redis_pass']}",
        f"--settings-ui={'true' if defaults['settings_ui'] in (True,'true') else 'false'}",
        f"--telemetry={'true' if defaults['telemetry'] in (True,'true') else 'false'}",
    ]
    # --- Исправление: не запускать artisan с пустым паролем ---
    if not defaults['db_pass']:
        console.print("[red]Пароль для БД не может быть пустым! Введите пароль для пользователя БД.[/red]")
        while not defaults['db_pass']:
            db_pass_input = inquirer.text(message=f"DB password (Enter для автозаполнения):", default="").execute()
            if db_pass_input:
                defaults['db_pass'] = db_pass_input
            else:
                console.print("[red]Пароль не может быть пустым![/red]")
        # После ввода — обновить .env
        env_path = '/var/www/pterodactyl/.env'
        if os.path.exists(env_path):
            lines = []
            with open(env_path) as f:
                for line in f:
                    if line.startswith('DB_PASSWORD='):
                        lines.append(f'DB_PASSWORD={defaults["db_pass"]}\n')
                    else:
                        lines.append(line)
            with open(env_path, 'w') as f:
                f.writelines(lines)
    db_args = [
        f"--host={defaults['db_host']}",
        f"--port={defaults['db_port']}",
        f"--database={defaults['db_name']}",
        f"--username={defaults['db_user']}",
        f"--password={defaults['db_pass']}"
    ]
    mail_args = [
        f"--driver={defaults['mail_driver']}",
        f"--email={defaults['mail_from']}",
        f"--from={defaults['mail_name']}",
        f"--host={defaults['mail_host']}",
        f"--port={defaults['mail_port']}",
        f"--username={defaults['mail_user']}",
        f"--password={defaults['mail_pass']}",
        f"--encryption={defaults['mail_encryption']}",
    ]
    # После создания пользователя и БД, перед artisan:
    while True:
        test_result = test_db_connection(defaults['db_host'], defaults['db_user'], defaults['db_pass'], defaults['db_name'], defaults['db_port'])
        if test_result is True:
            break
        console.print(Panel(f"[red]Не удалось подключиться к MariaDB:[/red]\n{test_result}", title="Ошибка подключения к БД", border_style="red"))
        console.print(Panel("Проверьте, что база данных и пользователь существуют, пароль указан верно, и доступ разрешён. Если пароль пустой — задайте его вручную или используйте сгенерированный!", title="Совет", border_style="yellow"))
        retry = inquirer.confirm(message="Ввести параметры БД вручную?", default=True).execute()
        if not retry:
            console.print("[yellow]Будет повторена попытка с текущими параметрами.[/yellow]")
            continue
        # Меню ручного ввода
        defaults['db_host'] = inquirer.text(message="DB host:", default=defaults['db_host']).execute()
        defaults['db_port'] = inquirer.text(message="DB port:", default=defaults['db_port']).execute()
        defaults['db_name'] = inquirer.text(message="DB name:", default=defaults['db_name']).execute()
        defaults['db_user'] = inquirer.text(message="DB user:", default=defaults['db_user']).execute()
        db_pass_input = inquirer.text(message=f"DB password (Enter для автозаполнения):", default=defaults['db_pass']).execute()
        if not db_pass_input and defaults['db_pass']:
            console.print(f"[yellow]Используется сгенерированный/текущий пароль для БД: {defaults['db_pass']}[/yellow]")
        elif not db_pass_input:
            console.print("[red]Пароль не может быть пустым![/red] Введите пароль для пользователя БД.")
            continue
        else:
            defaults['db_pass'] = db_pass_input
    # После успешного теста — обновляем .env
    env_path = '/var/www/pterodactyl/.env'
    if os.path.exists(env_path):
        lines = []
        with open(env_path) as f:
            for line in f:
                if line.startswith('DB_HOST='):
                    lines.append(f'DB_HOST={defaults["db_host"]}\n')
                elif line.startswith('DB_PORT='):
                    lines.append(f'DB_PORT={defaults["db_port"]}\n')
                elif line.startswith('DB_DATABASE='):
                    lines.append(f'DB_DATABASE={defaults["db_name"]}\n')
                elif line.startswith('DB_USERNAME='):
                    lines.append(f'DB_USERNAME={defaults["db_user"]}\n')
                elif line.startswith('DB_PASSWORD='):
                    lines.append(f'DB_PASSWORD={defaults["db_pass"]}\n')
                else:
                    lines.append(line)
        with open(env_path, 'w') as f:
            f.writelines(lines)
    # artisan будет вызван с этими параметрами
    # Запуск команд
    for cmd, args, title in [
        ('php artisan p:environment:setup', setup_args, 'App Settings'),
        ('php artisan p:environment:database', db_args, 'Database Settings'),
        ('php artisan p:environment:mail', mail_args, 'Mail Settings'),
    ]:
        res = run_command_with_dpkg_fix(f"cd /var/www/pterodactyl && {cmd} {' '.join(args)} --no-interaction", spinner_message=title)
        if res and res.returncode == 0:
            console.print(Panel(res.stdout or f"[green]{title} выполнено![/green]", title=title, border_style="green"))
            # Явное подтверждение и короткая пауза
            if title == 'Database Settings':
                console.print("[green]Настройка базы данных завершена успешно![/green]")
            elif title == 'Mail Settings':
                console.print("[green]Почтовые параметры сохранены![/green]")
            # Переход к следующему шагу без лишнего Enter
        else:
            console.print(Panel((res.stderr or res.stdout or f"[red]Ошибка {title}[/red]"), title=f"Ошибка {title}", border_style="red"))
            if title == 'Database Settings':
                console.print(Panel("[yellow]Если процесс завис — проверьте соединение с MariaDB, параметры доступа и повторите установку.\nВозможно, требуется задать пароль пользователя БД или разрешить root-доступ по socket.[/yellow]", title="Database Settings завис", border_style="yellow"))
            inquirer.text(message=f"{title} требует ручного ввода. Нажмите Enter после завершения...").execute()
            break

    # 14. Миграция и seed базы
    console.print(Panel("Миграция и seed базы...", title="Шаг 13", border_style="yellow"))
    res = run_command_with_dpkg_fix('cd /var/www/pterodactyl && php artisan migrate --seed --force', spinner_message="artisan migrate --seed...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка artisan migrate --seed[red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Миграция и seed базы выполнены![green]")

    # 15. Автоматизация создания первого пользователя
    import secrets
    import string
    admin_email = f"admin@{domain if 'domain' in locals() else 'localhost'}"
    admin_name = "admin"
    admin_pass = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    # Проверка валидности email и username
    import re
    def is_valid_email(email):
        return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)
    def is_valid_username(username):
        return re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]$", username)
    while not is_valid_email(admin_email):
        admin_email = inquirer.text(message="Введите валидный email для администратора:", default=admin_email).execute()
    while not is_valid_username(admin_name):
        admin_name = inquirer.text(message="Введите username (латиница, цифры, -, _, .):", default=admin_name).execute()
    user_cmd = (
        f"cd /var/www/pterodactyl && php artisan p:user:make "
        f"--email={admin_email} --username={admin_name} --name-first={admin_name} "
        f"--name-last={admin_name} --password={admin_pass} --admin=1"
    )
    res = run_command_with_dpkg_fix(user_cmd, spinner_message="Создание администратора панели...")
    if res and res.returncode == 0 and ('User Created' in (res.stdout or '') or 'UUID' in (res.stdout or '')):
        console.print(Panel(f"[green]Администратор создан автоматически![/green]\n\n[cyan]Email:[/cyan] {admin_email}\n[cyan]Имя:[/cyan] {admin_name}\n[cyan]Пароль:[/cyan] {admin_pass}", title="Админ создан", border_style="green"))
    else:
        console.print(Panel(f"[yellow]Не удалось создать администратора автоматически. Запустите вручную:[/yellow]\n\n[cyan]cd /var/www/pterodactyl\nphp artisan p:user:make --email={admin_email} --username={admin_name} --name-first={admin_name} --name-last={admin_name} --password={admin_pass} --admin=1[cyan]", title="Ручное создание админа", border_style="yellow"))
        inquirer.text(message="Нажмите Enter, когда пользователь будет создан...").execute()

    # 16. Права на папку
    console.print(Panel("Установка прав на папку для www-data...", title="Шаг 15", border_style="yellow"))
    res = run_command_with_dpkg_fix('chown -R www-data:www-data /var/www/pterodactyl/*', spinner_message="chown www-data...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка chown[red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Права на папку установлены![green]")

    # 17. Инструкция по nginx (до этого шага должен быть определён domain)
    # domain определяем заранее
    def get_default_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    # Определяем домен или IP
    env_path = '/var/www/pterodactyl/.env'
    domain = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('APP_URL='):
                    domain = line.strip().split('=',1)[1].replace('https://','').replace('http://','').split(':')[0]
                    break
    if not domain or domain in ("localhost", "127.0.0.1"):
        domain = get_default_ip()
    # Предложить сменить/установить домен
    change_domain = inquirer.confirm(message=f"Текущий домен/IP панели: {domain}. Хотите изменить/установить свой домен?", default=False).execute()
    if change_domain:
        domain = inquirer.text(message="Введите домен для панели (например, panel.example.com):", default=domain).execute()
        domain = domain.replace('"', '').replace("'", "")
        # Сохраняем в .env
        if os.path.exists(env_path):
            lines = []
            with open(env_path) as f:
                for line in f:
                    if line.startswith('APP_URL='):
                        lines.append(f'APP_URL=https://{domain}\n')
                    else:
                        lines.append(line)
            with open(env_path, 'w') as f:
                f.writelines(lines)
    _ensure_nginx_pterodactyl(domain)
    # --- Автоматическая установка Let's Encrypt SSL для домена ---
    if domain and not (domain == get_default_ip() or re.match(r'^\d+\.\d+\.\d+\.\d+$', domain)):
        admin_email = defaults.get('author', f'admin@{domain}')
        console.print(Panel(f"[bold]Попытка автоматической установки SSL-сертификата Let's Encrypt для домена {domain}...[/bold]\n\nEmail для регистрации: {admin_email}", title="SSL для домена", border_style="yellow"))
        import shutil
        import subprocess
        # Проверка наличия certbot-nginx
        def has_certbot_nginx():
            try:
                out = subprocess.check_output(['certbot', 'plugins'], encoding='utf-8')
                return 'nginx' in out
            except Exception:
                return False
        if not has_certbot_nginx():
            console.print("[yellow]Устанавливается плагин certbot-nginx...[/yellow]")
            run_command_with_dpkg_fix("apt-get update && apt-get install -y python3-certbot-nginx || apt-get install -y certbot-nginx", spinner_message="Установка certbot-nginx")
        # Теперь certbot-nginx точно есть
        certbot_cmd = f"certbot --nginx --non-interactive --agree-tos -m {admin_email} -d {domain} --redirect"
        res = run_command_with_dpkg_fix(certbot_cmd, spinner_message="Получение SSL-сертификата Let's Encrypt")
        if res and res.returncode == 0:
            console.print(Panel(f"[green]SSL-сертификат успешно установлен![/green]\nПанель будет доступна по адресу: https://{domain}", title="Let's Encrypt SSL", border_style="green"))
            run_command_with_dpkg_fix("systemctl restart nginx", spinner_message="Перезапуск nginx")
        else:
            console.print(Panel(f"[red]Не удалось получить SSL-сертификат для {domain}![/red]\n\nПроверьте DNS, порт 80, nginx-конфиг и повторите попытку вручную:\n[bold]sudo certbot --nginx -d {domain} --non-interactive --agree-tos -m {admin_email} --redirect[/bold]", title="Ошибка Let's Encrypt", border_style="red"))

    # 18. Автоматизация крон и systemd unit для очереди
    # Крон
    import subprocess
    cron_line = '* * * * * php /var/www/pterodactyl/artisan schedule:run >> /dev/null 2>&1'
    try:
        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        lines = res.stdout.splitlines() if res.returncode == 0 else []
        if cron_line not in lines:
            lines.append(cron_line)
            new_cron = '\n'.join(lines) + '\n'
            subprocess.run(['crontab', '-'], input=new_cron, text=True)
            console.print('[green]Крон-задача добавлена![/green]')
        else:
            console.print('[yellow]Крон-задача уже была добавлена.[/yellow]')
    except Exception as e:
        console.print(f'[red]Ошибка при добавлении крон-задачи: {e}[/red]')
    # Systemd unit
    pteroq_unit = '''[Unit]
Description=Pterodactyl Queue Worker
After=redis-server.service
[Service]
User=www-data
Group=www-data
Restart=always
ExecStart=/usr/bin/php /var/www/pterodactyl/artisan queue:work --queue=high,standard,low --sleep=3 --tries=3
StartLimitInterval=180
StartLimitBurst=30
RestartSec=5s
[Install]
WantedBy=multi-user.target
'''
    unit_path = '/etc/systemd/system/pteroq.service'
    try:
        with open(unit_path, 'w') as f:
            f.write(pteroq_unit)
        subprocess.run(['systemctl', 'daemon-reload'])
        subprocess.run(['systemctl', 'enable', '--now', 'pteroq.service'])
        console.print('[green]systemd unit pteroq создан и запущен![/green]')
    except Exception as e:
        console.print(f'[red]Ошибка при создании systemd unit: {e}[/red]')

    # 19. Финальное напутствие
    url = f'https://{domain}'
    console.print(Panel(f"[bold green]Установка Pterodactyl завершена![/bold green]\n\nПанель доступна по адресу: [cyan]{url}[/cyan]\n\n[bold]ВАЖНО:[/bold] Для входа используйте только [bold]https[/bold]! Если используете self-signed сертификат — браузер покажет предупреждение, выберите 'Продолжить' или 'Advanced -> Proceed'.\n\nЕсли видите ошибку [red]CSRF token mismatch[/red]:\n- Проверьте, что APP_URL в .env совпадает с адресом в браузере и начинается с https://\n- Перезапустите nginx и php-fpm после изменения .env\n- Очистите cookies в браузере\n\n[bold]Документация:[/bold] https://pterodactyl.io/panel/1.11/getting_started.html\n\n[bold yellow]Рекомендуется сразу сменить пароль администратора и настроить рабочий SMTP для почты![/bold yellow]", title="Готово!", border_style="green"))
    if domain and (domain == get_default_ip() or re.match(r'^\d+\.\d+\.\d+\.\d+$', domain)):
        console.print(Panel("[yellow]Вы используете self-signed SSL сертификат для IP. Браузер покажет предупреждение о безопасности — выберите 'Продолжить' или 'Advanced -> Proceed'. Для production используйте домен и Let's Encrypt!\n\n[bold]Проверьте, что nginx слушает порт 443 на этот IP, и APP_URL в .env совпадает с https://[IP]. Если видите 404 — проверьте конфиг nginx и настройки облачного прокси (Azure, Cloudflare и др.).[/bold]", title="Self-signed SSL", border_style="yellow"))
    inquirer.text(message="Нажмите Enter для выхода...").execute()

    # После установки файлов панели и .env:
    _ensure_nginx_pterodactyl()

def _remove_pterodactyl_cron():
    import subprocess
    try:
        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout:
            console.print("[yellow]Крон-задач не найдено или crontab пуст.[/yellow]")
            return
        lines = res.stdout.splitlines()
        new_lines = [l for l in lines if 'php /var/www/pterodactyl/artisan schedule:run' not in l]
        if len(new_lines) == len(lines):
            console.print("[yellow]Крон-задача Pterodactyl не найдена.[/yellow]")
            return
        new_cron = '\n'.join(new_lines) + '\n' if new_lines else ''
        p = subprocess.run(['crontab', '-'], input=new_cron, text=True)
        if p.returncode == 0:
            console.print("[green]Крон-задача Pterodactyl удалена![/green]")
        else:
            console.print("[red]Ошибка при удалении крон-задачи![/red]")
    except Exception as e:
        console.print(f"[red]Ошибка при работе с crontab: {e}[/red]")

def _remove_pterodactyl_db():
    import subprocess
    import re
    db_user = 'pterodactyl'
    db_name = 'panel'
    # Попробовать получить пароль из .env
    env_path = '/var/www/pterodactyl/.env'
    db_pass = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            env = f.read()
            m = re.search(r'DB_PASSWORD=(.*)', env)
            if m:
                db_pass = m.group(1).strip()
            m2 = re.search(r'DB_DATABASE=(.*)', env)
            if m2:
                db_name = m2.group(1).strip()
            m3 = re.search(r'DB_USERNAME=(.*)', env)
            if m3:
                db_user = m3.group(1).strip()
    # Пробуем через socket
    sql = f"DROP DATABASE IF EXISTS {db_name}; DROP USER IF EXISTS '{db_user}'@'127.0.0.1'; FLUSH PRIVILEGES;"
    res = subprocess.run(['mariadb', '-u', 'root', '--execute', sql], capture_output=True, text=True)
    if res.returncode == 0:
        console.print(f"[green]База данных и пользователь {db_name}/{db_user} удалены![/green]")
        return
    # Если не получилось — спросить пароль
    root_pass = inquirer.text(message="MariaDB root-пароль (оставьте пустым для пропуска):").execute()
    if not root_pass:
        console.print("[yellow]Пропущено удаление БД: не удалось подключиться к MariaDB.[/yellow]")
        return
    res2 = subprocess.run(['mariadb', '-u', 'root', f'-p{root_pass}', '--execute', sql], capture_output=True, text=True)
    if res2.returncode == 0:
        console.print(f"[green]База данных и пользователь {db_name}/{db_user} удалены![/green]")
    else:
        console.print(f"[yellow]Не удалось удалить БД автоматически. Проверьте вручную![/yellow]")

def pterodactyl_full_uninstall():
    clear_console()
    console.print(Panel("[red]Удаление Pterodactyl...[/red]", title="Удаление Pterodactyl", border_style="red"))
    # 1. Остановка и удаление pteroq
    console.print(Panel("Остановка и отключение systemd unit pteroq...", title="Шаг 1", border_style="yellow"))
    run_command_with_dpkg_fix('systemctl stop pteroq.service', spinner_message="Остановка pteroq.service...")
    run_command_with_dpkg_fix('systemctl disable pteroq.service', spinner_message="Отключение pteroq.service...")
    run_command_with_dpkg_fix('rm -f /etc/systemd/system/pteroq.service', spinner_message="Удаление systemd unit...")
    run_command_with_dpkg_fix('systemctl daemon-reload', spinner_message="Перезагрузка systemd...")
    console.print("[green]systemd unit pteroq удалён![...]")
    # 2. Удаление крон-задачи
    console.print(Panel("Удаление крон-задачи...", title="Шаг 2: Крон", border_style="yellow"))
    _remove_pterodactyl_cron()
    # 3. Удаление nginx-конфига
    console.print(Panel("Удаление nginx-конфига...", title="Шаг 3", border_style="yellow"))
    run_command_with_dpkg_fix('rm -f /etc/nginx/sites-available/pterodactyl.conf /etc/nginx/sites-enabled/pterodactyl.conf', spinner_message="Удаление nginx-конфига...")
    run_command_with_dpkg_fix('systemctl restart nginx', spinner_message="Перезапуск nginx...")
    console.print("[green]nginx-конфиг удалён и nginx перезапущен![...]")
    # 4. Удаление SSL-сертификата Let's Encrypt
    import shutil
    import subprocess
    domain = None
    try:
        # Попробовать найти домен из nginx-конфига
        conf_path = "/etc/nginx/sites-available/pterodactyl.conf"
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                import re
                for line in f:
                    m = re.search(r'server_name\s+([^;\s]+)', line)
                    if m:
                        domain = m.group(1)
                        break
    except Exception:
        pass
    if domain and shutil.which('certbot'):
        console.print(Panel(f"Попытка удалить SSL-сертификат Let's Encrypt для домена: {domain}", title="Удаление SSL", border_style="yellow"))
        try:
            res = subprocess.run(["certbot", "delete", "--cert-name", domain, "--non-interactive"], capture_output=True, text=True)
            if res.returncode == 0:
                console.print(f"[green]SSL-сертификат для {domain} удалён![/green]")
            else:
                console.print(f"[yellow]Не удалось удалить сертификат автоматически. Проверьте вручную!\n{res.stderr or res.stdout}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Ошибка при удалении сертификата: {e}[/yellow]")
    # 5. Удаление файлов панели
    console.print(Panel("Удаление файлов панели...", title="Шаг 4", border_style="yellow"))
    run_command_with_dpkg_fix('rm -rf /var/www/pterodactyl', spinner_message="Удаление /var/www/pterodactyl...")
    console.print("[green]Файлы панели удалены![/green]")
    # 6. Удаление базы данных
    console.print(Panel("Удаление базы данных и пользователя...", title="Шаг 5: База данных", border_style="yellow"))
    _remove_pterodactyl_db()
    # Финальное подтверждение
    inquirer.text(message="Нажмите Enter для выхода...").execute()

def pterodactyl_diagnose_and_install():
    import shutil
    import distro
    clear_console()
    console.print(Panel("[bold cyan]Диагностика и автоустановка Pterodactyl[/bold cyan]", title="Pterodactyl Diagnose & Auto-Install", border_style="cyan"))
    inquirer.text(message="Нажмите Enter для старта...").execute()

    # 1. Проверка root
    if os.geteuid() != 0:
        console.print(Panel("[red]Диагностику можно выполнять только от root![/red]", title="Ошибка", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return

    # 2. Проверка основных зависимостей
    dependencies = [
        ("php", "php8.3", "php -v", "PHP 8.2 или 8.3"),
        ("composer", "composer", "composer --version", "Composer v2"),
        ("mariadb", "mariadb-server", "mariadb --version", "MariaDB 10.2+"),
        ("nginx", "nginx", "nginx -v", "Nginx"),
        ("redis", "redis-server", "redis-server --version", "Redis"),
        ("git", "git", "git --version", "git"),
        ("curl", "curl", "curl --version", "curl"),
        ("unzip", "unzip", "unzip -v", "unzip"),
        ("tar", "tar", "tar --version", "tar"),
        ("nodejs", "nodejs", "node -v", "Node.js 16+"),
        ("yarn", "yarn", "yarn --version", "Yarn"),
        ("docker", "docker", "docker --version", "Docker"),
    ]
    missing = []
    for key, pkg, check_cmd, desc in dependencies:
        console.print(Panel(f"Проверка: {desc} ({pkg})", title=f"{desc}", border_style="yellow"))
        res = shutil.which(pkg.split()[0]) if pkg not in ("php8.3", "mariadb-server", "redis-server") else shutil.which(key)
        if not res:
            # Попробуем через команду
            check = run_command_with_dpkg_fix(check_cmd, spinner_message=f"Проверка {desc}...")
            if not check or check.returncode != 0:
                console.print(f"[red]{desc} не найден![/red]")
                missing.append((key, pkg, desc))
            else:
                console.print(f"[green]{desc} найден![/green]")
        else:
            console.print(f"[green]{desc} найден![/green]")
        inquirer.text(message="Enter для продолжения...").execute()

    # 3. Автоустановка недостающих
    if missing:
        console.print(Panel("[yellow]Обнаружены отсутствующие зависимости:[/yellow]\n" + "\n".join(f"- {desc}" for _, _, desc in missing), title="Автоустановка", border_style="yellow"))
        for key, pkg, desc in missing:
            if key == "php":
                # Для php — ставим через sury.org
                run_command_with_dpkg_fix('apt install -y php8.3 php8.3-{common,cli,gd,mysql,mbstring,bcmath,xml,fpm,curl,zip}', spinner_message="Установка PHP 8.3...")
            else:
                run_command_with_dpkg_fix(f"apt install -y {pkg}", spinner_message=f"Установка {desc}...")
        console.print("[green]Попытка автоустановки завершена![/green]")
        inquirer.text(message="Enter для продолжения...").execute()
    else:
        console.print(Panel("[green]Все зависимости установлены![/green]", title="ОК", border_style="green"))
        inquirer.text(message="Enter для продолжения...").execute()

    # 4. Проверка /var/www/pterodactyl
    if os.path.exists('/var/www/pterodactyl'):
        console.print(Panel("[green]/var/www/pterodactyl найден! Панель уже установлена или частично установлена.[/green]", title="Папка панели", border_style="green"))
    else:
        console.print(Panel("[yellow]/var/www/pterodactyl не найден. Готово к установке![/yellow]", title="Папка панели", border_style="yellow"))
    inquirer.text(message="Enter для продолжения...").execute()

    # 5. Проверка systemd unit pteroq
    if os.path.exists('/etc/systemd/system/pteroq.service'):
        console.print(Panel("[green]systemd unit pteroq.service найден![/green]", title="systemd", border_style="green"))
    else:
        console.print(Panel("[yellow]systemd unit pteroq.service не найден.[/yellow]", title="systemd", border_style="yellow"))
    inquirer.text(message="Enter для продолжения...").execute()

    # 6. Проверка крон-задачи
    cron_check = run_command_with_dpkg_fix('crontab -l', spinner_message="Проверка крон-задач...")
    if cron_check and '* * * * * php /var/www/pterodactyl/artisan schedule:run' in (cron_check.stdout or ''):
        console.print(Panel("[green]Крон-задача для artisan schedule:run найдена![/green]", title="Крон", border_style="green"))
    else:
        console.print(Panel("[yellow]Крон-задача для artisan schedule:run не найдена.[/yellow]", title="Крон", border_style="yellow"))
    inquirer.text(message="Enter для продолжения...").execute()

    # 7. Проверка nginx-конфига
    if os.path.exists('/etc/nginx/sites-available/pterodactyl.conf'):
        console.print(Panel("[green]nginx-конфиг найден![/green]", title="nginx", border_style="green"))
    else:
        console.print(Panel("[yellow]nginx-конфиг не найден.[/yellow]", title="nginx", border_style="yellow"))
    inquirer.text(message="Enter для продолжения...").execute()

    # 8. Проверка портов 80/443
    def check_port(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
            s.bind(("0.0.0.0", port))
            s.close()
            return True
        except OSError:
            return False
    ports = {80: "HTTP (80)", 443: "HTTPS (443)"}
    for port, desc in ports.items():
        if check_port(port):
            console.print(f"[green]Порт {desc} свободен![/green]")
        else:
            console.print(f"[red]Порт {desc} занят![/red] Возможно, уже работает nginx или другой сервис.")
    inquirer.text(message="Enter для продолжения...").execute()

    # 9. Финальный совет
    console.print(Panel("[bold green]Диагностика завершена![/bold green]\n\nЕсли все зависимости установлены и порты свободны — переходите к мастеру установки панели!\n\n[cyan]Документация: https://pterodactyl.io/panel/1.11/getting_started.html[/cyan]", title="Готово!", border_style="green"))
    inquirer.text(message="Нажмите Enter для выхода...").execute()

# --- Wings Management ---
def wings_manage_menu():
    # Меню управления Wings: установка, удаление, статус, логи
    pass  # TODO: реализовать

# --- Вспомогательные функции ---
# (Проверка статуса, ручные/manual_steps, doc_links, инструкции, локализация)
# TODO: реализовать вспомогательные функции по необходимости 

def run_command_with_dpkg_fix(cmd, spinner_message=None, cwd=None):
    res = run_command(cmd, spinner_message=spinner_message, cwd=cwd)
    # Проверка на dpkg was interrupted
    err_out = (res.stderr or '') + '\n' + (res.stdout or '') if res else ''
    if 'dpkg was interrupted' in err_out:
        console.print(Panel("[yellow]Обнаружена проблема с dpkg![/yellow]\n[cyan]Выполняется автоматическое восстановление: dpkg --configure -a[/cyan]", title="dpkg auto-fix", border_style="yellow"))
        fix = run_command('dpkg --configure -a', spinner_message="dpkg --configure -a ...", cwd=cwd)
        if fix and fix.returncode == 0:
            console.print("[green]dpkg --configure -a выполнено успешно! Повтор команды...[/green]")
            res = run_command(cmd, spinner_message=spinner_message, cwd=cwd)
        else:
            console.print(Panel((fix.stderr or fix.stdout or "Не удалось выполнить dpkg --configure -a"), title="[red]Ошибка dpkg --configure -a[/red]", border_style="red"))
    # Проверка на Unmet dependencies
    err_out = (res.stderr or '') + '\n' + (res.stdout or '') if res else ''
    if "Unmet dependencies" in err_out and "apt --fix-broken install" in err_out:
        console.print(Panel("[yellow]Обнаружены битые зависимости![/yellow]\n[cyan]Выполняется автоматическое восстановление: apt --fix-broken install -y[/cyan]", title="apt fix-broken auto-fix", border_style="yellow"))
        fix = run_command('apt --fix-broken install -y', spinner_message="apt --fix-broken install ...", cwd=cwd)
        if fix and fix.returncode == 0:
            console.print("[green]apt --fix-broken install выполнено успешно! Повтор команды...[/green]")
            res = run_command(cmd, spinner_message=spinner_message, cwd=cwd)
        else:
            console.print(Panel((fix.stderr or fix.stdout or "Не удалось выполнить apt --fix-broken install"), title="[red]Ошибка apt --fix-broken install[/red]", border_style="red"))
    return res 

def _pteroq_unit_exists():
    return os.path.exists('/etc/systemd/system/pteroq.service')

def _create_pteroq_unit():
    pteroq_unit = '''[Unit]
Description=Pterodactyl Queue Worker
After=redis-server.service
[Service]
User=www-data
Group=www-data
Restart=always
ExecStart=/usr/bin/php /var/www/pterodactyl/artisan queue:work --queue=high,standard,low --sleep=3 --tries=3
StartLimitInterval=180
StartLimitBurst=30
RestartSec=5s
[Install]
WantedBy=multi-user.target
'''
    unit_path = '/etc/systemd/system/pteroq.service'
    with open(unit_path, 'w') as f:
        f.write(pteroq_unit)
    subprocess.run(['systemctl', 'daemon-reload'])
    subprocess.run(['systemctl', 'enable', '--now', 'pteroq.service'])
    console.print('[green]systemd unit pteroq создан и запущен![/green]') 

def test_db_connection(host, user, password, db, port=3306):
    try:
        conn = pymysql.connect(host=host, user=user, password=password, database=db, port=int(port), connect_timeout=3)
        conn.close()
        return True
    except Exception as e:
        return str(e) 

def get_installed_php_fpm_sock():
    # Проверяем наличие сокетов php-fpm
    for v in ['8.3', '8.2', '8.1', '8.0', '7.4']:
        sock = f'/run/php/php{v}-fpm.sock'
        if os.path.exists(sock):
            return sock
    # Фоллбек
    return '/run/php/php8.3-fpm.sock'

# --- ДОБАВИТЬ функцию проверки порта ---
def _is_port_free(port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", port))
        s.close()
        return True
    except OSError:
        return False

    # Проверка APP_TIMEZONE в .env
    timezone = None
    if os.path.exists(db_path):
        with open(db_path) as f:
            env = f.read()
            m = re.search(r'APP_TIMEZONE=(.*)', env)
            if m:
                timezone = m.group(1).strip()
    # Список валидных таймзон (сокращённый, можно расширить)
    valid_timezones = [
        'UTC', 'Europe/Moscow', 'Asia/Novosibirsk', 'Asia/Krasnoyarsk', 'Asia/Yekaterinburg',
        'Europe/Samara', 'Europe/Kaliningrad', 'Asia/Vladivostok', 'Asia/Irkutsk', 'Asia/Omsk',
        'Asia/Barnaul', 'Asia/Tomsk', 'Asia/Chita', 'Asia/Sakhalin', 'Asia/Magadan', 'Asia/Kamchatka',
        'Asia/Srednekolymsk', 'Asia/Ust-Nera', 'Asia/Anadyr', 'Asia/Yakutsk', 'Asia/Krasnoyarsk',
        'Asia/Novokuznetsk', 'Asia/Khandyga', 'Asia/Chita', 'Asia/Irkutsk', 'Asia/Ulaanbaatar',
        'Asia/Hong_Kong', 'Asia/Bangkok', 'Asia/Singapore', 'Asia/Shanghai', 'Asia/Tokyo',
        'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Rome', 'Europe/Madrid',
        'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
        'Etc/GMT-3', 'Etc/GMT-4', 'Etc/GMT-5', 'Etc/GMT-6', 'Etc/GMT-7', 'Etc/GMT-8', 'Etc/GMT-9',
    ]
    def is_valid_timezone(tz):
        if not tz:
            return False
        if tz in valid_timezones:
            return True
        # Проверка на Etc/GMT±N
        import re
        if re.match(r'^Etc/GMT[+-]\d+$', tz):
            return True
        # Проверка на Europe/..., Asia/..., America/... и т.д.
        if re.match(r'^[A-Za-z]+/[A-Za-z_\-]+$', tz):
            return True
        return False
    if timezone and not is_valid_timezone(timezone):
        console.print(Panel(f"[yellow]Внимание: В .env указана невалидная таймзона: {timezone}\nРекомендуется выбрать корректную таймзону из списка PHP: https://www.php.net/manual/en/timezones.php[/yellow]", title="APP_TIMEZONE невалидна", border_style="yellow"))
        # Предложить выбрать из списка
        tz_choice = inquirer.select(
            message="Выберите корректную таймзону для панели:",
            choices=valid_timezones + ["Ввести вручную"]
        ).execute()
        if tz_choice == "Ввести вручную":
            tz_choice = inquirer.text(message="Введите корректную таймзону (например, Europe/Moscow):").execute()
        # Исправить .env
        with open(db_path, 'r') as f:
            lines = f.readlines()
        with open(db_path, 'w') as f:
            for line in lines:
                if line.startswith('APP_TIMEZONE='):
                    f.write(f'APP_TIMEZONE={tz_choice}\n')
                else:
                    f.write(line)
        console.print(Panel(f"[green]APP_TIMEZONE в .env автоматически исправлен на {tz_choice}!\nПерезапускаю nginx и php-fpm...[/green]", title="APP_TIMEZONE исправлен", border_style="green"))
        import subprocess
        subprocess.run(['systemctl', 'restart', 'nginx'])
        subprocess.run(['systemctl', 'restart', 'php8.3-fpm'])