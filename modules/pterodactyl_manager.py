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

console = Console()

def pterodactyl_manage_menu():
    clear_console()
    if not os.path.exists('/var/www/pterodactyl'):
        console.print(Panel("[red]Pterodactyl не установлен![/red]\n\n[bold yellow]Для управления сначала выполните установку панели.[/bold yellow]\n\n[cyan]Документация: https://pterodactyl.io/panel/1.11/getting_started.html[/cyan]", title="Pterodactyl не установлен", border_style="red"))
        choice = inquirer.select(
            message="Выберите действие:",
            choices=[
                "Установить Pterodactyl",
                "Назад"
            ]).execute()
        if choice == "Установить Pterodactyl":
            pterodactyl_install_wizard()
        return
    # ... здесь будет обычное меню управления, если установлен ...
    # TODO: реализовать полноценное меню управления

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
    res = run_command("apt -y install software-properties-common curl ca-certificates gnupg2 sudo lsb-release", spinner_message="Установка базовых пакетов...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка установки базовых пакетов[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Базовые пакеты установлены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 3. Добавление репозитория PHP (sury.org)
    console.print(Panel("Добавление репозитория PHP (sury.org)...", title="Шаг 2", border_style="yellow"))
    res = run_command('echo "deb https://packages.sury.org/php/ $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/sury-php.list', spinner_message="Добавление репозитория sury.org...")
    res2 = run_command('curl -fsSL https://packages.sury.org/php/apt.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/sury-keyring.gpg', spinner_message="Импорт GPG ключа sury.org...")
    if (res and res.returncode != 0) or (res2 and res2.returncode != 0):
        console.print(Panel((res.stderr or '') + '\n' + (res2.stderr or ''), title="[red]Ошибка добавления репозитория PHP[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий PHP добавлен![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 4. Добавление репозитория Redis
    console.print(Panel("Добавление репозитория Redis...", title="Шаг 3", border_style="yellow"))
    res = run_command('curl -fsSL https://packages.redis.io/gpg | gpg --yes --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg', spinner_message="Импорт GPG ключа Redis...")
    res2 = run_command('echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list', spinner_message="Добавление репозитория Redis...")
    if (res and res.returncode != 0) or (res2 and res2.returncode != 0):
        console.print(Panel((res.stderr or '') + '\n' + (res2.stderr or ''), title="[red]Ошибка добавления репозитория Redis[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий Redis добавлен![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 5. MariaDB repo setup
    console.print(Panel("Добавление репозитория MariaDB...", title="Шаг 4", border_style="yellow"))
    res = run_command('curl -LsS https://r.mariadb.com/downloads/mariadb_repo_setup | sudo bash', spinner_message="MariaDB repo setup...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка MariaDB repo setup[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Репозиторий MariaDB добавлен![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 6. apt update
    console.print(Panel("Обновление списка пакетов...", title="Шаг 5", border_style="yellow"))
    res = run_command('apt update', spinner_message="apt update...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка apt update[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Список пакетов обновлён![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 7. Установка зависимостей
    console.print(Panel("Установка зависимостей: php8.3, mariadb, nginx, tar, unzip, git, redis-server...", title="Шаг 6", border_style="yellow"))
    res = run_command('apt install -y php8.3 php8.3-{common,cli,gd,mysql,mbstring,bcmath,xml,fpm,curl,zip} mariadb-server nginx tar unzip git redis-server', spinner_message="Установка зависимостей...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка установки зависимостей[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Зависимости установлены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 8. Установка Composer
    console.print(Panel("Установка Composer...", title="Шаг 7", border_style="yellow"))
    res = run_command('curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer', spinner_message="Установка Composer...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка установки Composer[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Composer установлен![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 9. Скачивание и распаковка панели
    console.print(Panel("Скачивание и распаковка Pterodactyl Panel...", title="Шаг 8", border_style="yellow"))
    run_command('mkdir -p /var/www/pterodactyl', spinner_message="Создание директории...")
    run_command('cd /var/www/pterodactyl && curl -Lo panel.tar.gz https://github.com/pterodactyl/panel/releases/latest/download/panel.tar.gz', spinner_message="Скачивание архива панели...")
    run_command('cd /var/www/pterodactyl && tar -xzvf panel.tar.gz', spinner_message="Распаковка архива...")
    run_command('cd /var/www/pterodactyl && chmod -R 755 storage/* bootstrap/cache/', spinner_message="Права на storage и cache...")
    console.print("[green]Файлы панели скачаны и распакованы![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 10. Инструкция по созданию БД
    console.print(Panel("[bold]Вам нужно создать базу данных и пользователя для Pterodactyl.[/bold]\n\nПример для MariaDB:\n\n[cyan]mariadb -u root -p[/cyan]\n\n[cyan]CREATE USER 'pterodactyl'@'127.0.0.1' IDENTIFIED BY 'yourPassword';\nCREATE DATABASE panel;\nGRANT ALL PRIVILEGES ON panel.* TO 'pterodactyl'@'127.0.0.1' WITH GRANT OPTION;\nexit[/cyan]\n\n[bold yellow]Скопируйте команды выше и выполните их в отдельном терминале![/bold yellow]", title="Шаг 9: База данных", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда база данных будет готова...").execute()

    # 11. Установка зависимостей через composer
    console.print(Panel("Установка зависимостей через composer...", title="Шаг 10", border_style="yellow"))
    res = run_command('cd /var/www/pterodactyl && COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --optimize-autoloader', spinner_message="composer install...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка composer install[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Composer зависимости установлены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 12. Генерация ключа приложения
    console.print(Panel("Генерация ключа приложения...", title="Шаг 11", border_style="yellow"))
    res = run_command('cd /var/www/pterodactyl && php artisan key:generate --force', spinner_message="artisan key:generate...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка artisan key:generate[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Ключ приложения сгенерирован![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 13. Artisan environment setup
    console.print(Panel("[bold]Теперь настройте окружение через artisan.[/bold]\n\n[cyan]cd /var/www/pterodactyl\nphp artisan p:environment:setup\nphp artisan p:environment:database\nphp artisan p:environment:mail[/cyan]\n\nСледуйте инструкциям в консоли!", title="Шаг 12: Настройка окружения", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда artisan setup будет завершён...").execute()

    # 14. Миграция и seed базы
    console.print(Panel("Миграция и seed базы...", title="Шаг 13", border_style="yellow"))
    res = run_command('cd /var/www/pterodactyl && php artisan migrate --seed --force', spinner_message="artisan migrate --seed...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка artisan migrate --seed[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Миграция и seed базы выполнены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 15. Создание первого пользователя
    console.print(Panel("Создайте первого администратора панели:\n\n[cyan]cd /var/www/pterodactyl\nphp artisan p:user:make[/cyan]\n\nСледуйте инструкциям в консоли!", title="Шаг 14: Первый пользователь", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда пользователь будет создан...").execute()

    # 16. Права на папку
    console.print(Panel("Установка прав на папку для www-data...", title="Шаг 15", border_style="yellow"))
    res = run_command('chown -R www-data:www-data /var/www/pterodactyl/*', spinner_message="chown www-data...")
    if res and res.returncode != 0:
        console.print(Panel(res.stderr or res.stdout or "Неизвестная ошибка", title="[red]Ошибка chown[/red]", border_style="red"))
        inquirer.text(message="Нажмите Enter для выхода...").execute()
        return
    console.print("[green]Права на папку установлены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 17. Инструкция по nginx
    nginx_conf = (
        '[bold]Настройте nginx для панели![/bold]\n\nПример SSL-конфига (замените <domain>):\n\n[cyan]rm /etc/nginx/sites-enabled/default\ncat > /etc/nginx/sites-available/pterodactyl.conf <<EOF\nserver {\n    listen 80;\n    server_name <domain>;\n    return 301 https://$server_name$request_uri;\n}\nserver {\n    listen 443 ssl http2;\n    server_name <domain>;\n    root /var/www/pterodactyl/public;\n    index index.php;\n    access_log /var/log/nginx/pterodactyl.app-access.log;\n    error_log  /var/log/nginx/pterodactyl.app-error.log error;\n    client_max_body_size 100m;\n    client_body_timeout 120s;\n    sendfile off;\n    ssl_certificate /etc/letsencrypt/live/<domain>/fullchain.pem;\n    ssl_certificate_key /etc/letsencrypt/live/<domain>/privkey.pem;\n    ssl_session_cache shared:SSL:10m;\n    ssl_protocols TLSv1.2 TLSv1.3;\n    ssl_ciphers '
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
        'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
        'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384'
        ';\n'
        '    ssl_prefer_server_ciphers on;\n'
        '    add_header X-Content-Type-Options nosniff;\n'
        '    add_header X-XSS-Protection "1; mode=block";\n'
        '    add_header X-Robots-Tag none;\n'
        '    add_header Content-Security-Policy "frame-ancestors \'self\'";\n'
        '    add_header X-Frame-Options DENY;\n'
        '    add_header Referrer-Policy same-origin;\n'
        '    location / {\n        try_files $uri $uri/ /index.php?$query_string;\n    }\n'
        '    location ~ \\.php$ {\n'
        '        fastcgi_split_path_info ^(.+\\.php)(/.+)$;\n'
        '        fastcgi_pass unix:/run/php/php8.3-fpm.sock;\n'
        '        fastcgi_index index.php;\n'
        '        include fastcgi_params;\n'
        '        fastcgi_param PHP_VALUE "upload_max_filesize = 100M \\n post_max_size=100M";\n'
        '        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n'
        '        fastcgi_param HTTP_PROXY "";\n'
        '        fastcgi_intercept_errors off;\n'
        '        fastcgi_buffer_size 16k;\n'
        '        fastcgi_buffers 4 16k;\n'
        '        fastcgi_connect_timeout 300;\n'
        '        fastcgi_send_timeout 300;\n'
        '        fastcgi_read_timeout 300;\n'
        '        include /etc/nginx/fastcgi_params;\n'
        '    }\n'
        '    location ~ /\\.ht {\n        deny all;\n    }\n}\nEOF\nln -s /etc/nginx/sites-available/pterodactyl.conf /etc/nginx/sites-enabled/pterodactyl.conf\nsystemctl restart nginx[/cyan]\n\n[bold yellow]Не забудьте получить SSL-сертификат через certbot или другой способ![/bold yellow]'
    )
    console.print(Panel(nginx_conf, title="Шаг 16: Nginx", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда nginx будет настроен и перезапущен...").execute()

    # 18. Инструкция по крону и systemd
    console.print(Panel("[bold]Добавьте крон и systemd unit для очереди![/bold]\n\n[cyan]crontab -e[/cyan]\n* * * * * php /var/www/pterodactyl/artisan schedule:run >> /dev/null 2>&1\n\n[cyan]cat > /etc/systemd/system/pteroq.service <<EOF\n[Unit]\nDescription=Pterodactyl Queue Worker\nAfter=redis-server.service\n[Service]\nUser=www-data\nGroup=www-data\nRestart=always\nExecStart=/usr/bin/php /var/www/pterodactyl/artisan queue:work --queue=high,standard,low --sleep=3 --tries=3\nStartLimitInterval=180\nStartLimitBurst=30\nRestartSec=5s\n[Install]\nWantedBy=multi-user.target\nEOF\nsystemctl enable --now pteroq.service[/cyan]", title="Шаг 17: Крон и systemd", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда крон и systemd unit будут настроены...").execute()

    # 19. Финальное напутствие
    console.print(Panel("[bold green]Установка Pterodactyl завершена![/bold green]\n\nПанель доступна по адресу вашего домена.\n\n[cyan]Документация: https://pterodactyl.io/panel/1.11/getting_started.html[/cyan]", title="Готово!", border_style="green"))
    inquirer.text(message="Нажмите Enter для выхода...").execute()

def pterodactyl_full_uninstall():
    clear_console()
    console.print(Panel("[bold red]Мастер полного удаления Pterodactyl[/bold red]", title="Удаление Pterodactyl", border_style="red"))
    inquirer.text(message="Нажмите Enter для старта...").execute()

    # 1. Остановка и отключение systemd unit pteroq
    console.print(Panel("Остановка и отключение systemd unit pteroq...", title="Шаг 1", border_style="yellow"))
    run_command('systemctl stop pteroq.service', spinner_message="Остановка pteroq.service...")
    run_command('systemctl disable pteroq.service', spinner_message="Отключение pteroq.service...")
    run_command('rm -f /etc/systemd/system/pteroq.service', spinner_message="Удаление systemd unit...")
    run_command('systemctl daemon-reload', spinner_message="Перезагрузка systemd...")
    console.print("[green]systemd unit pteroq удалён![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 2. Удаление крон-задачи
    console.print(Panel("Удалите крон-задачу вручную (если была добавлена):\n\n[cyan]crontab -e[/cyan]\nУдалите строку:\n[cyan]* * * * * php /var/www/pterodactyl/artisan schedule:run >> /dev/null 2>&1[/cyan]", title="Шаг 2: Крон", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда крон будет удалён...").execute()

    # 3. Удаление nginx-конфига
    console.print(Panel("Удаление nginx-конфига...", title="Шаг 3", border_style="yellow"))
    run_command('rm -f /etc/nginx/sites-available/pterodactyl.conf /etc/nginx/sites-enabled/pterodactyl.conf', spinner_message="Удаление nginx-конфига...")
    run_command('systemctl restart nginx', spinner_message="Перезапуск nginx...")
    console.print("[green]nginx-конфиг удалён и nginx перезапущен![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 4. Удаление файлов панели
    console.print(Panel("Удаление файлов панели...", title="Шаг 4", border_style="yellow"))
    run_command('rm -rf /var/www/pterodactyl', spinner_message="Удаление /var/www/pterodactyl...")
    console.print("[green]Файлы панели удалены![/green]")
    inquirer.text(message="Enter для продолжения...").execute()

    # 5. Инструкция по удалению БД и пользователя
    console.print(Panel("[bold]Удалите базу данных и пользователя вручную![/bold]\n\nПример для MariaDB:\n\n[cyan]mariadb -u root -p[/cyan]\n\n[cyan]DROP DATABASE panel;\nDROP USER 'pterodactyl'@'127.0.0.1';\nFLUSH PRIVILEGES;\nexit[/cyan]", title="Шаг 5: База данных", border_style="yellow"))
    inquirer.text(message="Нажмите Enter, когда БД и пользователь будут удалены...").execute()

    # 6. Финальное напутствие
    console.print(Panel("[bold green]Удаление Pterodactyl завершено![/bold green]", title="Готово!", border_style="green"))
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
            check = run_command(check_cmd, spinner_message=f"Проверка {desc}...")
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
                run_command('apt install -y php8.3 php8.3-{common,cli,gd,mysql,mbstring,bcmath,xml,fpm,curl,zip}', spinner_message="Установка PHP 8.3...")
            else:
                run_command(f"apt install -y {pkg}", spinner_message=f"Установка {desc}...")
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
    cron_check = run_command('crontab -l', spinner_message="Проверка крон-задач...")
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