import os
import sys
import shutil
import socket
import secrets
import string
from modules.utils.logger import log

def check_root():
    if os.geteuid() != 0:
        log("Скрипт должен запускаться от root!", level="ERROR")
        print("[ОШИБКА] Запустите скрипт от root!")
        sys.exit(1)

def check_dependency(cmd, name):
    res = shutil.which(cmd)
    if not res:
        log(f"Не найдена зависимость: {name}", level="ERROR")
        print(f"[ОШИБКА] Не найдена зависимость: {name} ({cmd})")
        return False
    log(f"Найдена зависимость: {name}")
    return True

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        log(f"Порт {port} свободен")
        return True
    except OSError:
        log(f"Порт {port} занят", level="ERROR")
        print(f"[ВНИМАНИЕ] Порт {port} занят! Возможно, уже работает nginx или другой сервис.")
        return False

def download_and_extract_panel(panel_dir):
    url = "https://github.com/pterodactyl/panel/releases/latest/download/panel.tar.gz"
    archive = os.path.join("/tmp", "panel.tar.gz")
    log(f"Скачивание панели из {url}")
    print(f"[INFO] Скачивание панели...")
    os.system(f"curl -Lo {archive} {url}")
    if not os.path.exists(panel_dir):
        os.makedirs(panel_dir, exist_ok=True)
    log(f"Распаковка архива в {panel_dir}")
    print(f"[INFO] Распаковка архива...")
    os.system(f"tar -xzvf {archive} -C {panel_dir}")
    # Права на storage и bootstrap/cache
    os.system(f"chmod -R 755 {panel_dir}/storage/* {panel_dir}/bootstrap/cache/")
    log(f"Панель скачана и распакована в {panel_dir}")
    print(f"[OK] Панель скачана и распакована.")

def generate_password(length=16):
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    log("Сгенерирован пароль для БД/админа")
    return password

def update_env_file(env_path, updates: dict):
    if not os.path.exists(env_path):
        log(f".env не найден по пути {env_path}", level="ERROR")
        return
    with open(env_path, 'r') as f:
        lines = f.readlines()
    keys = set(updates.keys())
    new_lines = []
    for line in lines:
        key = line.split('=', 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            keys.remove(key)
        else:
            new_lines.append(line)
    for key in keys:
        new_lines.append(f"{key}={updates[key]}\n")
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    log(f"Обновлены переменные в .env: {', '.join(updates.keys())}")

def run_artisan(panel_dir, command, args=None):
    args = args or []
    cmd = f"cd {panel_dir} && php artisan {command} {' '.join(args)}"
    log(f"Выполнение artisan: {cmd}")
    res = os.system(cmd)
    if res != 0:
        print(f"[ОШИБКА] Artisan-команда завершилась с ошибкой: {command}")
        log(f"Artisan-команда завершилась с ошибкой: {command}", level="ERROR")
    else:
        print(f"[OK] Artisan {command} выполнен.")
        log(f"Artisan {command} выполнен.")

def setup_systemd_pteroq(panel_dir):
    unit = '''[Unit]
Description=Pterodactyl Queue Worker
After=redis-server.service

[Service]
User=www-data
Group=www-data
Restart=always
ExecStart=/usr/bin/php {panel_dir}/artisan queue:work --queue=high,standard,low --sleep=3 --tries=3
StartLimitInterval=180
StartLimitBurst=30
RestartSec=5s

[Install]
WantedBy=multi-user.target
'''.replace('{panel_dir}', panel_dir)
    path = "/etc/systemd/system/pteroq.service"
    with open(path, 'w') as f:
        f.write(unit)
    os.system("systemctl daemon-reload")
    os.system("systemctl enable --now pteroq.service")
    print("[OK] systemd unit pteroq создан и запущен.")
    log("systemd unit pteroq создан и запущен.")

def setup_cron(panel_dir):
    cron_line = f"* * * * * php {panel_dir}/artisan schedule:run >> /dev/null 2>&1"
    os.system(f'(crontab -l 2>/dev/null; echo "{cron_line}") | sort | uniq | crontab -')
    print("[OK] Крон-задача добавлена.")
    log("Крон-задача добавлена.")

def setup_nginx(panel_dir):
    conf = f'''
server {{
    listen 80;
    server_name localhost;
    root {panel_dir}/public;
    index index.php;
    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}
    location ~ \.php$ {{
        fastcgi_split_path_info ^(.+\.php)(/.+)$;
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        fastcgi_param HTTP_PROXY "";
        internal;
    }}
    location ~ /\.ht {{
        deny all;
    }}
    client_max_body_size 100m;
    sendfile off;
}}
'''
    conf_path = "/etc/nginx/sites-available/pterodactyl.conf"
    with open(conf_path, 'w') as f:
        f.write(conf)
    enabled_path = "/etc/nginx/sites-enabled/pterodactyl.conf"
    if not os.path.exists(enabled_path):
        os.symlink(conf_path, enabled_path)
    os.system("systemctl restart nginx")
    print("[OK] Nginx сконфигурирован и перезапущен.")
    log("Nginx сконфигурирован и перезапущен.")

def remove_systemd_pteroq():
    os.system("systemctl stop pteroq.service")
    os.system("systemctl disable pteroq.service")
    unit_path = "/etc/systemd/system/pteroq.service"
    if os.path.exists(unit_path):
        os.remove(unit_path)
    os.system("systemctl daemon-reload")
    print("[OK] systemd unit pteroq удалён.")
    log("systemd unit pteroq удалён.")

def remove_cron(panel_dir):
    cron_line = f"* * * * * php {panel_dir}/artisan schedule:run >> /dev/null 2>&1"
    import subprocess
    try:
        res = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        lines = res.stdout.splitlines()
        new_lines = [l for l in lines if cron_line.strip() not in l.strip()]
        tmp = '/tmp/cron.tmp'
        with open(tmp, 'w') as f:
            f.write('\n'.join(new_lines) + '\n')
        os.system(f'crontab {tmp}')
        os.remove(tmp)
        print("[OK] Крон-задача удалена.")
        log("Крон-задача удалена.")
    except Exception as e:
        print("[INFO] Не удалось удалить крон-задачу (возможно, её не было).")
        log(f"Не удалось удалить крон-задачу: {e}")

def remove_nginx():
    conf_path = "/etc/nginx/sites-available/pterodactyl.conf"
    enabled_path = "/etc/nginx/sites-enabled/pterodactyl.conf"
    if os.path.exists(enabled_path):
        os.remove(enabled_path)
    if os.path.exists(conf_path):
        os.remove(conf_path)
    os.system("systemctl restart nginx")
    print("[OK] Nginx-конфиг панели удалён и nginx перезапущен.")
    log("Nginx-конфиг панели удалён и nginx перезапущен.")

def remove_panel_files(panel_dir):
    if os.path.exists(panel_dir):
        shutil.rmtree(panel_dir)
        print(f"[OK] Файлы панели {panel_dir} удалены.")
        log(f"Файлы панели {panel_dir} удалены.")
    else:
        print(f"[INFO] Директория {panel_dir} уже удалена.")
        log(f"Директория {panel_dir} уже удалена.")

def get_db_params_from_env(env_path):
    params = {}
    if not os.path.exists(env_path):
        return None
    with open(env_path) as f:
        for line in f:
            if line.startswith('DB_HOST='):
                params['host'] = line.strip().split('=',1)[1]
            elif line.startswith('DB_PORT='):
                params['port'] = int(line.strip().split('=',1)[1])
            elif line.startswith('DB_DATABASE='):
                params['db_name'] = line.strip().split('=',1)[1]
            elif line.startswith('DB_USERNAME='):
                params['db_user'] = line.strip().split('=',1)[1]
            elif line.startswith('DB_PASSWORD='):
                params['db_pass'] = line.strip().split('=',1)[1]
    if all(k in params for k in ['host','port','db_name','db_user','db_pass']):
        return params
    return None

def remove_db_user_and_db(host, port, db_name, db_user, db_pass):
    from modules.utils.db_utils import MariaDBManager
    # Пробуем удалить через root без пароля
    root_mgr = MariaDBManager(host, 'root', None, port)
    ok, err = root_mgr.drop_db_and_user(db_name, db_user)
    if ok:
        print("[OK] База данных и пользователь удалены (root без пароля).")
        log("База данных и пользователь удалены (root без пароля).")
        return
    # Пробуем через root с паролем
    root_pass = input("Введите пароль root MariaDB для удаления БД (или Enter для пропуска): ")
    if root_pass:
        root_mgr = MariaDBManager(host, 'root', root_pass, port)
        ok, err = root_mgr.drop_db_and_user(db_name, db_user)
        if ok:
            print("[OK] База данных и пользователь удалены (root с паролем).")
            log("База данных и пользователь удалены (root с паролем).")
            return
    # Пробуем через пользователя панели
    user_mgr = MariaDBManager(host, db_user, db_pass, port)
    ok, err = user_mgr.drop_db_and_user(db_name, db_user)
    if ok:
        print("[OK] База данных и пользователь удалены (через пользователя панели).")
        log("База данных и пользователь удалены (через пользователя панели).")
        return
    print(f"[ВНИМАНИЕ] Не удалось автоматически удалить базу и пользователя: {err}")
    log(f"Не удалось автоматически удалить базу и пользователя: {err}", level="ERROR") 