import os
import sys
import shutil
import socket
import subprocess
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from modules.utils.db_utils import MariaDBManager
from modules.utils.logger import log
from modules.utils.pterodactyl_utils import (
    check_root, check_dependency, check_port, download_and_extract_panel,
    generate_password, update_env_file, run_artisan, setup_systemd_pteroq, setup_cron, setup_nginx,
    remove_systemd_pteroq, remove_cron, remove_nginx, remove_panel_files, remove_db_user_and_db
)

console = Console()

# TODO: main_menu(), install_pterodactyl(), uninstall_pterodactyl(), diagnose_pterodactyl()
# Весь старый код удалён. Будет реализована новая архитектура.

def main_menu():
    while True:
        choice = inquirer.select(
            message="=== Linux Helper: Менеджер Pterodactyl ===",
            choices=[
                {"name": "Установить Pterodactyl (авто)", "value": "install_auto"},
                {"name": "Удалить Pterodactyl", "value": "uninstall"},
                {"name": "Диагностика окружения", "value": "diagnose"},
                {"name": "Выход", "value": "exit"},
            ],
            pointer="> ",
            instruction="Стрелки [36m[1m↑↓[0m, Enter — выбрать"
        ).execute()
        if choice == "install_auto":
            panel_dir = "/var/www/pterodactyl"
            if os.path.exists(panel_dir):
                confirm = inquirer.confirm(
                    message="Панель уже установлена. Удалить и установить заново?",
                    default=False
                ).execute()
                if confirm:
                    uninstall_pterodactyl(console)
                    install_pterodactyl_full_auto(console)
                else:
                    continue
            else:
                install_pterodactyl_full_auto(console)
        elif choice == "uninstall":
            panel_dir = "/var/www/pterodactyl"
            if not os.path.exists(panel_dir):
                console.print(Panel("Панель уже удалена или не установлена.", title="Инфо", border_style="cyan"))
            else:
                uninstall_pterodactyl(console)
        elif choice == "diagnose":
            diagnose_pterodactyl(console)
        else:
            console.print("[bold green]Выход.[/bold green]")
            sys.exit(0)

def diagnose_pterodactyl(console):
    console.print("\n[Диагностика окружения Pterodactyl]")
    log("Старт диагностики окружения")
    check_root()
    # Проверка зависимостей
    dependencies = [
        ("php", "PHP 8.2/8.3"),
        ("composer", "Composer v2"),
        ("mariadb", "MariaDB"),
        ("nginx", "Nginx"),
        ("redis-server", "Redis"),
        ("git", "git"),
        ("curl", "curl"),
        ("unzip", "unzip"),
        ("tar", "tar")
    ]
    all_ok = True
    for cmd, name in dependencies:
        if not check_dependency(cmd, name):
            all_ok = False
    if not all_ok:
        console.print("[ОШИБКА] Установите все зависимости и повторите диагностику!")
        return
    # Проверка портов
    for port in [80, 443]:
        check_port(port)
    # Проверка директории панели
    panel_dir = "/var/www/pterodactyl"
    if os.path.exists(panel_dir):
        log(f"Директория панели {panel_dir} найдена")
        console.print(f"[OK] Директория панели {panel_dir} найдена.")
    else:
        log(f"Директория панели {panel_dir} не найдена, будет создана при установке")
        console.print(f"[INFO] Директория панели {panel_dir} будет создана при установке.")
    # Проверка systemd unit pteroq
    pteroq_unit = "/etc/systemd/system/pteroq.service"
    if os.path.exists(pteroq_unit):
        log("systemd unit pteroq.service найден")
        console.print("[OK] systemd unit pteroq.service найден.")
    else:
        log("systemd unit pteroq.service не найден")
        console.print("[INFO] systemd unit pteroq.service не найден (будет создан при установке).")
    # Проверка крон-задачи
    try:
        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if '* * * * * php /var/www/pterodactyl/artisan schedule:run' in (res.stdout or ''):
            log("Крон-задача для artisan schedule:run найдена")
            console.print("[OK] Крон-задача для artisan schedule:run найдена.")
        else:
            log("Крон-задача для artisan schedule:run не найдена")
            console.print("[INFO] Крон-задача для artisan schedule:run не найдена (будет добавлена при установке).")
    except Exception as e:
        log(f"Ошибка при проверке крон-задачи: {e}", level="ERROR")
        console.print("[ВНИМАНИЕ] Не удалось проверить крон-задачи.")
    # Проверка nginx-конфига
    nginx_conf = "/etc/nginx/sites-available/pterodactyl.conf"
    if os.path.exists(nginx_conf):
        log("nginx-конфиг найден")
        console.print("[OK] nginx-конфиг найден.")
    else:
        log("nginx-конфиг не найден")
        console.print("[INFO] nginx-конфиг не найден (будет создан при установке).")
    console.print("\n[Диагностика завершена]")
    log("Диагностика завершена")

def install_pterodactyl(console):
    console.print("\n[Установка Pterodactyl Panel]")
    log("Старт установки панели")
    check_root()
    # Проверка зависимостей
    dependencies = [
        ("php", "PHP 8.2/8.3"),
        ("composer", "Composer v2"),
        ("mariadb", "MariaDB"),
        ("nginx", "Nginx"),
        ("redis-server", "Redis"),
        ("git", "git"),
        ("curl", "curl"),
        ("unzip", "unzip"),
        ("tar", "tar")
    ]
    all_ok = True
    for cmd, name in dependencies:
        if not check_dependency(cmd, name):
            all_ok = False
    if not all_ok:
        console.print("[ОШИБКА] Установите все зависимости и повторите установку!")
        return
    # Проверка портов
    for port in [80, 443]:
        check_port(port)
    # Скачивание и распаковка панели
    panel_dir = "/var/www/pterodactyl"
    if os.path.exists(panel_dir):
        console.print(f"[INFO] Директория {panel_dir} уже существует. Пропускаю скачивание.")
        log(f"Директория {panel_dir} уже существует")
    else:
        download_and_extract_panel(panel_dir)
    # Установка composer-зависимостей
    console.print("[INFO] Установка зависимостей composer...")
    log("Установка зависимостей composer...")
    os.system(f"cd {panel_dir} && COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --optimize-autoloader")
    # Копирование .env
    env_path = os.path.join(panel_dir, ".env")
    env_example = os.path.join(panel_dir, ".env.example")
    if not os.path.exists(env_path) and os.path.exists(env_example):
        shutil.copy(env_example, env_path)
        console.print("[OK] .env создан из .env.example")
        log(".env создан из .env.example")
    # Генерация ключа приложения
    console.print("[INFO] Генерация ключа приложения...")
    log("Генерация ключа приложения...")
    os.system(f"cd {panel_dir} && php artisan key:generate --force")
    console.print("[OK] Базовая установка файлов завершена. Продолжаю...")
    log("Базовая установка файлов завершена")
    # --- Автоматизация создания БД и пользователя ---
    console.print("[INFO] Создание базы данных и пользователя...")
    db_name = "panel"
    db_user = "pterodactyl"
    db_pass = generate_password(16)
    db_host = "127.0.0.1"
    db_port = 3306
    # Попытка через root без пароля
    mariadb = MariaDBManager(db_host, "root", None, db_port)
    ok, err = mariadb.create_user_and_db(db_name, db_user, db_pass)
    if not ok and err and '1698' in str(err):
        console.print("[ОШИБКА] MariaDB не даёт доступ root через пароль (auth_socket).\n" \
              "\nРешение: создайте временного пользователя с правами root.\n" \
              "\n1. Откройте терминал и выполните:\n" \
              "   sudo mariadb\n" \
              "2. Введите команды (замените password на свой сложный пароль):\n" \
              "   CREATE USER 'tempadmin'@'127.0.0.1' IDENTIFIED BY 'password';\n" \
              "   GRANT ALL PRIVILEGES ON *.* TO 'tempadmin'@'127.0.0.1' WITH GRANT OPTION;\n" \
              "   FLUSH PRIVILEGES;\n" \
              "3. Вернитесь к установке и введите логин/пароль MariaDB ниже.\n")
        log("MariaDB требует временного пользователя с правами root (auth_socket)", level="ERROR")
        while True:
            login = input("MariaDB логин (например, tempadmin): ").strip()
            passwd = input("MariaDB пароль: ").strip()
            if not login or not passwd:
                console.print("[ОШИБКА] Логин и пароль не могут быть пустыми!")
                continue
            mariadb = MariaDBManager(db_host, login, passwd, db_port)
            ok, err = mariadb.create_user_and_db(db_name, db_user, db_pass)
            if ok:
                console.print(f"[OK] БД и пользователь созданы: {db_name}, {db_user}")
                log(f"БД и пользователь созданы: {db_name}, {db_user}")
                break
            else:
                console.print(f"[ОШИБКА] Не удалось создать БД/пользователя: {err}")
                log(f"Не удалось создать БД/пользователя: {err}", level="ERROR")
                retry = input("Попробовать снова? (y/n): ").strip().lower()
                if retry != 'y':
                    console.print("[ОШИБКА] Установка прервана. Создайте БД и пользователя вручную.")
                    return
    elif not ok:
        console.print(f"[ОШИБКА] Не удалось создать БД/пользователя: {err}")
        log(f"Не удалось создать БД/пользователя: {err}", level="ERROR")
        return
    else:
        console.print(f"[OK] БД и пользователь созданы: {db_name}, {db_user}")
        log(f"БД и пользователь созданы: {db_name}, {db_user}")
    # --- Запись параметров в .env ---
    update_env_file(env_path, {
        "DB_HOST": db_host,
        "DB_PORT": str(db_port),
        "DB_DATABASE": db_name,
        "DB_USERNAME": db_user,
        "DB_PASSWORD": db_pass
    })
    console.print("[OK] Параметры БД записаны в .env")
    log("Параметры БД записаны в .env")
    # --- Проверка подключения к БД ---
    mariadb2 = MariaDBManager(db_host, db_user, db_pass, db_port)
    ok, err = mariadb2.test_connection(db_name)
    if not ok:
        console.print(f"[ОШИБКА] Не удалось подключиться к БД: {err}")
        log(f"Не удалось подключиться к БД: {err}", level="ERROR")
        return
    console.print("[OK] Подключение к БД успешно!")
    log("Подключение к БД успешно!")
    # --- Artisan setup (окружение, база, почта) ---
    console.print("[INFO] Настройка окружения панели...")
    run_artisan(panel_dir, "p:environment:setup", [
        f"--author=admin@localhost",
        f"--url=http://localhost",
        f"--timezone=UTC",
        f"--cache=file",
        f"--session=file",
        f"--queue=redis",
        f"--redis-host=127.0.0.1",
        f"--redis-port=6379",
        f"--redis-pass=",
        f"--settings-ui=false",
        f"--telemetry=true"
    ])
    run_artisan(panel_dir, "p:environment:database", [
        f"--host={db_host}",
        f"--port={db_port}",
        f"--database={db_name}",
        f"--username={db_user}",
        f"--password={db_pass}"
    ])
    run_artisan(panel_dir, "p:environment:mail", [
        f"--driver=smtp",
        f"--email=no-reply@localhost",
        f"--from=Pterodactyl Panel",
        f"--host=localhost",
        f"--port=25",
        f"--username=",
        f"--password=",
        f"--encryption=",
    ])
    # --- Миграция и seed ---
    console.print("[INFO] Миграция и заполнение базы...")
    run_artisan(panel_dir, "migrate", ["--seed", "--force"])
    # --- Создание первого администратора ---
    console.print("[INFO] Создание администратора...")
    admin_email = f"admin@localhost"
    admin_user = "admin"
    admin_pass = generate_password(12)
    run_artisan(panel_dir, "p:user:make", [
        f"--email={admin_email}",
        f"--username={admin_user}",
        f"--name-first=Admin",
        f"--name-last=Admin",
        f"--password={admin_pass}",
        f"--admin=1"
    ])
    console.print(f"[OK] Администратор создан: {admin_email} / {admin_pass}")
    log(f"Администратор создан: {admin_email}")
    # --- Права на папки ---
    console.print("[INFO] Установка прав на папки...")
    os.system(f"chown -R www-data:www-data {panel_dir}")
    # --- Systemd unit pteroq ---
    setup_systemd_pteroq(panel_dir)
    # --- Крон ---
    setup_cron(panel_dir)
    # --- Nginx ---
    setup_nginx(panel_dir)
    console.print("\n[Установка завершена!]")
    console.print(f"Панель доступна по адресу: http://localhost (или ваш домен)")
    console.print(f"Логин: {admin_email}")
    console.print(f"Пароль: {admin_pass}")
    console.print("Рекомендуется сменить пароль и email администратора после первого входа!")
    log("Установка панели завершена успешно")

def install_pterodactyl_full_auto(console):
    console.print(Panel("[bold cyan]Автоматическая установка Pterodactyl[/bold cyan]", title="Старт", border_style="cyan"))
    check_root()
    # 1. apt update и установка зависимостей
    pkgs = [
        "software-properties-common", "curl", "apt-transport-https", "ca-certificates", "gnupg",
        "php8.3", "php8.3-common", "php8.3-cli", "php8.3-gd", "php8.3-mysql", "php8.3-mbstring", "php8.3-bcmath", "php8.3-xml", "php8.3-fpm", "php8.3-curl", "php8.3-zip",
        "mariadb-server", "nginx", "tar", "unzip", "git", "redis-server"
    ]
    console.print("[cyan]Обновление apt и установка зависимостей...[/cyan]")
    subprocess.run(["apt", "update"], check=True)
    subprocess.run(["apt", "install", "-y"] + pkgs, check=True)
    # Composer
    if not shutil.which("composer"):
        console.print("[cyan]Установка composer...[/cyan]")
        subprocess.run("curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer", shell=True, check=True)
    # 2. MariaDB: tempadmin если нужно
    console.print("[cyan]Проверка MariaDB и создание пользователя...[/cyan]")
    # Проверяем auth_socket
    auth_socket = False
    try:
        out = subprocess.check_output(["sudo", "mariadb", "-e", "SELECT plugin FROM mysql.user WHERE User='root';"]).decode()
        if "auth_socket" in out:
            auth_socket = True
    except Exception:
        pass
    db_name = "panel"
    db_user = "pterodactyl"
    db_pass = generate_password(16)
    db_host = "127.0.0.1"
    db_port = 3306
    tempadmin = False
    tempadmin_user = "tempadmin"
    tempadmin_pass = generate_password(16)
    if auth_socket:
        console.print("[yellow]MariaDB использует auth_socket. Создаю временного пользователя tempadmin...[/yellow]")
        sql = f"CREATE USER IF NOT EXISTS '{tempadmin_user}'@'127.0.0.1' IDENTIFIED BY '{tempadmin_pass}'; GRANT ALL PRIVILEGES ON *.* TO '{tempadmin_user}'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;"
        subprocess.run(["sudo", "mariadb", "-e", sql], check=True)
        tempadmin = True
    # Создаём пользователя и базу для панели
    sql = f"CREATE USER IF NOT EXISTS '{db_user}'@'127.0.0.1' IDENTIFIED BY '{db_pass}'; CREATE DATABASE IF NOT EXISTS {db_name}; GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'127.0.0.1' WITH GRANT OPTION; FLUSH PRIVILEGES;"
    if tempadmin:
        subprocess.run(["mariadb", "-u", tempadmin_user, f"-p{tempadmin_pass}", "-e", sql], check=True)
    else:
        subprocess.run(["sudo", "mariadb", "-e", sql], check=True)
    console.print(Panel(f"БД и пользователь созданы: [green]{db_name}[/green] / [green]{db_user}[/green]", title="MariaDB", border_style="green"))
    # 3. Скачивание и распаковка панели
    panel_dir = "/var/www/pterodactyl"
    if not os.path.exists(panel_dir):
        os.makedirs(panel_dir, exist_ok=True)
    console.print("[cyan]Скачивание и распаковка панели...[/cyan]")
    subprocess.run(["curl", "-Lo", f"{panel_dir}/panel.tar.gz", "https://github.com/pterodactyl/panel/releases/latest/download/panel.tar.gz"], check=True)
    subprocess.run(["tar", "-xzvf", f"{panel_dir}/panel.tar.gz", "-C", panel_dir], check=True)
    subprocess.run(["chmod", "-R", "755", f"{panel_dir}/storage", f"{panel_dir}/bootstrap/cache/"], check=True)
    # 4. Composer install
    subprocess.run(["composer", "install", "--no-dev", "--optimize-autoloader"], cwd=panel_dir, check=True)
    # 5. .env и ключ
    env_path = os.path.join(panel_dir, ".env")
    env_example = os.path.join(panel_dir, ".env.example")
    if not os.path.exists(env_path) and os.path.exists(env_example):
        shutil.copy(env_example, env_path)
    # Записываем параметры БД
    update_env_file(env_path, {
        "DB_HOST": db_host,
        "DB_PORT": str(db_port),
        "DB_DATABASE": db_name,
        "DB_USERNAME": db_user,
        "DB_PASSWORD": db_pass
    })
    subprocess.run(["php", "artisan", "key:generate", "--force"], cwd=panel_dir, check=True)
    # 6. Artisan setup
    subprocess.run(["php", "artisan", "p:environment:setup", "--author=admin@localhost", "--url=http://localhost", "--timezone=UTC", "--cache=file", "--session=file", "--queue=redis", "--redis-host=127.0.0.1", "--redis-port=6379", "--redis-pass=", "--settings-ui=false", "--telemetry=true"], cwd=panel_dir, check=True)
    subprocess.run(["php", "artisan", "p:environment:database", f"--host={db_host}", f"--port={db_port}", f"--database={db_name}", f"--username={db_user}", f"--password={db_pass}"], cwd=panel_dir, check=True)
    subprocess.run(["php", "artisan", "p:environment:mail", "--driver=smtp", "--email=no-reply@localhost", "--from=Pterodactyl Panel", "--host=localhost", "--port=25", "--username=", "--password=", "--encryption="], cwd=panel_dir, check=True)
    # 7. Миграция и админ
    subprocess.run(["php", "artisan", "migrate", "--seed", "--force"], cwd=panel_dir, check=True)
    admin_email = "admin@localhost"
    admin_user = "admin"
    admin_pass = generate_password(12)
    subprocess.run(["php", "artisan", "p:user:make", f"--email={admin_email}", f"--username={admin_user}", f"--name-first=Admin", f"--name-last=Admin", f"--password={admin_pass}", f"--admin=1"], cwd=panel_dir, check=True)
    # 8. Права
    subprocess.run(["chown", "-R", "www-data:www-data", panel_dir], check=True)
    # 9. Systemd unit
    setup_systemd_pteroq(panel_dir)
    # 10. Крон
    setup_cron(panel_dir)
    # 11. Nginx
    setup_nginx(panel_dir)
    # 12. Финал
    console.print(Panel(f"[bold green]Установка завершена![/bold green]\nПанель: http://localhost (или ваш домен)\nЛогин: {admin_email}\nПароль: {admin_pass}", title="Готово!", border_style="green"))
    log("Автоматическая установка панели завершена успешно")

def uninstall_pterodactyl(console):
    console.print("\n[Удаление Pterodactyl Panel]")
    log("Старт удаления панели")
    check_root()
    panel_dir = "/var/www/pterodactyl"
    env_path = os.path.join(panel_dir, ".env")
    # 1. Остановить и удалить systemd unit pteroq
    remove_systemd_pteroq()
    # 2. Удалить крон-задачу
    remove_cron(panel_dir)
    # 3. Удалить nginx-конфиг
    remove_nginx()
    # 4. Удалить базу данных и пользователя
    if os.path.exists(env_path):
        from modules.utils.pterodactyl_utils import get_db_params_from_env
        db_params = get_db_params_from_env(env_path)
        if db_params:
            remove_db_user_and_db(**db_params)
    # 5. Удалить файлы панели
    remove_panel_files(panel_dir)
    console.print("[OK] Удаление завершено. Все компоненты панели удалены.")
    log("Удаление панели завершено успешно")

if __name__ == "__main__":
    main_menu()