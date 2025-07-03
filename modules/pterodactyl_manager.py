import os
import sys
import shutil
import socket
from modules.utils.db_utils import MariaDBManager
from modules.utils.logger import log
from modules.utils.pterodactyl_utils import (
    check_root, check_dependency, check_port, download_and_extract_panel,
    generate_password, update_env_file, run_artisan, setup_systemd_pteroq, setup_cron, setup_nginx,
    remove_systemd_pteroq, remove_cron, remove_nginx, remove_panel_files, remove_db_user_and_db
)

# TODO: main_menu(), install_pterodactyl(), uninstall_pterodactyl(), diagnose_pterodactyl()
# Весь старый код удалён. Будет реализована новая архитектура.

def main_menu():
    print("\n=== Linux Helper: Менеджер Pterodactyl ===\n")
    print("1. Установить Pterodactyl")
    print("2. Удалить Pterodactyl")
    print("3. Диагностика окружения")
    print("4. Выход")
    choice = input("Выберите действие: ").strip()
    if choice == '1':
        install_pterodactyl()
    elif choice == '2':
        uninstall_pterodactyl()
    elif choice == '3':
        diagnose_pterodactyl()
    else:
        print("Выход.")
        sys.exit(0)

def diagnose_pterodactyl():
    print("\n[Диагностика окружения Pterodactyl]")
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
        print("[ОШИБКА] Установите все зависимости и повторите диагностику!")
        return
    # Проверка портов
    for port in [80, 443]:
        check_port(port)
    # Проверка директории панели
    panel_dir = "/var/www/pterodactyl"
    if os.path.exists(panel_dir):
        log(f"Директория панели {panel_dir} найдена")
        print(f"[OK] Директория панели {panel_dir} найдена.")
    else:
        log(f"Директория панели {panel_dir} не найдена, будет создана при установке")
        print(f"[INFO] Директория панели {panel_dir} будет создана при установке.")
    # Проверка systemd unit pteroq
    pteroq_unit = "/etc/systemd/system/pteroq.service"
    if os.path.exists(pteroq_unit):
        log("systemd unit pteroq.service найден")
        print("[OK] systemd unit pteroq.service найден.")
    else:
        log("systemd unit pteroq.service не найден")
        print("[INFO] systemd unit pteroq.service не найден (будет создан при установке).")
    # Проверка крон-задачи
    try:
        import subprocess
        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if '* * * * * php /var/www/pterodactyl/artisan schedule:run' in (res.stdout or ''):
            log("Крон-задача для artisan schedule:run найдена")
            print("[OK] Крон-задача для artisan schedule:run найдена.")
        else:
            log("Крон-задача для artisan schedule:run не найдена")
            print("[INFO] Крон-задача для artisan schedule:run не найдена (будет добавлена при установке).")
    except Exception as e:
        log(f"Ошибка при проверке крон-задачи: {e}", level="ERROR")
        print("[ВНИМАНИЕ] Не удалось проверить крон-задачи.")
    # Проверка nginx-конфига
    nginx_conf = "/etc/nginx/sites-available/pterodactyl.conf"
    if os.path.exists(nginx_conf):
        log("nginx-конфиг найден")
        print("[OK] nginx-конфиг найден.")
    else:
        log("nginx-конфиг не найден")
        print("[INFO] nginx-конфиг не найден (будет создан при установке).")
    print("\n[Диагностика завершена]")
    log("Диагностика завершена")

def install_pterodactyl():
    print("\n[Установка Pterodactyl Panel]")
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
        print("[ОШИБКА] Установите все зависимости и повторите установку!")
        return
    # Проверка портов
    for port in [80, 443]:
        check_port(port)
    # Скачивание и распаковка панели
    panel_dir = "/var/www/pterodactyl"
    if os.path.exists(panel_dir):
        print(f"[INFO] Директория {panel_dir} уже существует. Пропускаю скачивание.")
        log(f"Директория {panel_dir} уже существует")
    else:
        download_and_extract_panel(panel_dir)
    # Установка composer-зависимостей
    print("[INFO] Установка зависимостей composer...")
    log("Установка зависимостей composer...")
    os.system(f"cd {panel_dir} && COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --optimize-autoloader")
    # Копирование .env
    env_path = os.path.join(panel_dir, ".env")
    env_example = os.path.join(panel_dir, ".env.example")
    if not os.path.exists(env_path) and os.path.exists(env_example):
        shutil.copy(env_example, env_path)
        print("[OK] .env создан из .env.example")
        log(".env создан из .env.example")
    # Генерация ключа приложения
    print("[INFO] Генерация ключа приложения...")
    log("Генерация ключа приложения...")
    os.system(f"cd {panel_dir} && php artisan key:generate --force")
    print("[OK] Базовая установка файлов завершена. Продолжаю...")
    log("Базовая установка файлов завершена")
    # --- Автоматизация создания БД и пользователя ---
    print("[INFO] Создание базы данных и пользователя...")
    db_name = "panel"
    db_user = "pterodactyl"
    db_pass = generate_password(16)
    db_host = "127.0.0.1"
    db_port = 3306
    mariadb = MariaDBManager(db_host, "root", None, db_port)
    ok, err = mariadb.create_user_and_db(db_name, db_user, db_pass)
    if not ok:
        print(f"[ОШИБКА] Не удалось создать БД/пользователя: {err}")
        log(f"Не удалось создать БД/пользователя: {err}", level="ERROR")
        return
    print(f"[OK] БД и пользователь созданы: {db_name}, {db_user}")
    log(f"БД и пользователь созданы: {db_name}, {db_user}")
    # --- Запись параметров в .env ---
    update_env_file(env_path, {
        "DB_HOST": db_host,
        "DB_PORT": str(db_port),
        "DB_DATABASE": db_name,
        "DB_USERNAME": db_user,
        "DB_PASSWORD": db_pass
    })
    print("[OK] Параметры БД записаны в .env")
    log("Параметры БД записаны в .env")
    # --- Проверка подключения к БД ---
    mariadb2 = MariaDBManager(db_host, db_user, db_pass, db_port)
    ok, err = mariadb2.test_connection(db_name)
    if not ok:
        print(f"[ОШИБКА] Не удалось подключиться к БД: {err}")
        log(f"Не удалось подключиться к БД: {err}", level="ERROR")
        return
    print("[OK] Подключение к БД успешно!")
    log("Подключение к БД успешно!")
    # --- Artisan setup (окружение, база, почта) ---
    print("[INFO] Настройка окружения панели...")
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
    print("[INFO] Миграция и заполнение базы...")
    run_artisan(panel_dir, "migrate", ["--seed", "--force"])
    # --- Создание первого администратора ---
    print("[INFO] Создание администратора...")
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
    print(f"[OK] Администратор создан: {admin_email} / {admin_pass}")
    log(f"Администратор создан: {admin_email}")
    # --- Права на папки ---
    print("[INFO] Установка прав на папки...")
    os.system(f"chown -R www-data:www-data {panel_dir}")
    # --- Systemd unit pteroq ---
    setup_systemd_pteroq(panel_dir)
    # --- Крон ---
    setup_cron(panel_dir)
    # --- Nginx ---
    setup_nginx(panel_dir)
    print("\n[Установка завершена!]")
    print(f"Панель доступна по адресу: http://localhost (или ваш домен)")
    print(f"Логин: {admin_email}")
    print(f"Пароль: {admin_pass}")
    print("Рекомендуется сменить пароль и email администратора после первого входа!")
    log("Установка панели завершена успешно")

def uninstall_pterodactyl():
    print("\n[Удаление Pterodactyl Panel]")
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
    print("[OK] Удаление завершено. Все компоненты панели удалены.")
    log("Удаление панели завершено успешно")

if __name__ == "__main__":
    main_menu()