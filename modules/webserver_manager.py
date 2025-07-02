import os
import subprocess
import shutil
from rich.console import Console
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console, run_command, is_root
from localization import get_string
import json
from rich.live import Live
import glob
import socket
import getpass

console = Console()

SUPPORTED_PROJECT_TYPES = [
    {"key": "nodejs", "name": "Node.js/Next.js/React (npm/yarn)"},
    {"key": "python", "name": "Python (FastAPI, Flask, Django)"},
    {"key": "php", "name": "PHP (Laravel, Wordpress)"},
    {"key": "static", "name": "Статический сайт (HTML/CSS/JS)"},
]

SITES_FILE = "deployed_sites.json"

def _load_sites():
    try:
        with open(SITES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_site(site):
    sites = _load_sites()
    # Если сайт с таким именем уже есть — обновить
    for i, s in enumerate(sites):
        if s.get("name") == site["name"]:
            sites[i] = site
            break
    else:
        sites.append(site)
    with open(SITES_FILE, "w") as f:
        json.dump(sites, f, indent=2)

def _install_nginx():
    if not shutil.which("nginx"):
        console.print("[yellow]nginx не найден. Устанавливаю nginx...[/yellow]")
        res = run_command(["apt-get", "update"], "Обновление списка пакетов...")
        res = run_command(["apt-get", "install", "-y", "nginx"], "Установка Nginx...")
        if res and res.returncode == 0:
            console.print("[green]Nginx успешно установлен.[/green]")
        else:
            console.print("[red]Не удалось установить Nginx.[/red]")
        return
    while True:
        clear_console()
        console.print(Panel("[bold green]Управление Nginx[/bold green]", border_style="green"))
        choices = [
            Choice("list", name="Просмотреть все сайты/конфиги"),
            Choice("delete", name="Удалить конфиг сайта"),
            Choice("test", name="Проверить валидность конфига (nginx -t)"),
            Choice("reload", name="Перезапустить nginx (reload)"),
            Choice(None, name="Назад")
        ]
        action = inquirer.select(message="Выберите действие:", choices=choices, vi_mode=True).execute()
        sites_dir = "/etc/nginx/sites-available"
        enabled_dir = "/etc/nginx/sites-enabled"
        if action == "list":
            import glob
            sites = glob.glob(sites_dir + "/*")
            if not sites:
                console.print("[yellow]Нет доступных конфигов сайтов.[/yellow]")
            else:
                info = ""
                for site in sites:
                    name = os.path.basename(site)
                    enabled = os.path.exists(os.path.join(enabled_dir, name))
                    info += f"[bold]{name}[/bold] {'[green]ENABLED[/green]' if enabled else '[red]DISABLED[/red]'}\n"
                console.print(Panel(info, title="Конфиги сайтов", border_style="cyan"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "delete":
            import glob
            sites = glob.glob(sites_dir + "/*")
            if not sites:
                console.print("[yellow]Нет доступных конфигов для удаления.[/yellow]")
                inquirer.text(message="Нажмите Enter для продолжения...").execute()
                continue
            names = [os.path.basename(s) for s in sites]
            site_name = inquirer.select(message="Выберите конфиг для удаления:", choices=names, vi_mode=True).execute()
            if site_name:
                confirm = inquirer.confirm(message=f"Удалить конфиг {site_name}?", default=False).execute()
                if confirm:
                    try:
                        os.remove(os.path.join(sites_dir, site_name))
                        if os.path.exists(os.path.join(enabled_dir, site_name)):
                            os.remove(os.path.join(enabled_dir, site_name))
                        console.print(f"[green]Конфиг {site_name} удалён.[/green]")
                        run_command(["systemctl", "reload", "nginx"], "Перезапуск nginx...")
                    except Exception as e:
                        console.print(f"[red]Ошибка удаления: {e}[/red]")
                    inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "test":
            res = run_command(["nginx", "-t"], "Проверка валидности nginx...")
            if res and res.returncode == 0:
                console.print(Panel(res.stdout or "Конфиг валиден!", title="nginx -t", border_style="green"))
            else:
                console.print(Panel(res.stderr if res else "Ошибка проверки", title="nginx -t", border_style="red"))
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "reload":
            res = run_command(["systemctl", "reload", "nginx"], "Перезапуск nginx...")
            if res and res.returncode == 0:
                console.print("[green]nginx успешно перезапущен![/green]")
            else:
                console.print("[red]Ошибка перезапуска nginx.[/red]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        else:
            break

def _install_certbot():
    if not shutil.which("certbot"):
        console.print("[yellow]Certbot не установлен. Устанавливаю certbot...[/yellow]")
        res = run_command(["apt-get", "update"], "Обновление списка пакетов...")
        res = run_command(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"], "Установка Certbot...")
        if res and res.returncode == 0:
            console.print("[green]Certbot успешно установлен.[/green]")
        else:
            console.print("[red]Не удалось установить Certbot.[/red]")
        return
    while True:
        clear_console()
        console.print(Panel("[bold green]Управление SSL-сертификатами (Certbot)[/bold green]", border_style="green"))
        choices = [
            Choice("list", name="Просмотреть все сертификаты"),
            Choice("delete", name="Удалить сертификат"),
            Choice("renew", name="Обновить сертификат"),
            Choice("new", name="Выписать новый сертификат (через деплой сайта)"),
            Choice(None, name="Назад")
        ]
        action = inquirer.select(message="Выберите действие:", choices=choices, vi_mode=True).execute()
        if action == "list":
            res = run_command(["certbot", "certificates"], "Получение списка сертификатов...")
            if res and res.stdout:
                console.print(Panel(res.stdout, title="Список сертификатов", border_style="cyan"))
            else:
                console.print("[yellow]Не удалось получить список сертификатов.[/yellow]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "delete":
            res = run_command(["certbot", "certificates"], "Получение списка сертификатов...")
            certs = []
            if res and res.stdout:
                import re
                certs = re.findall(r"Certificate Name: (.+)", res.stdout)
            if not certs:
                console.print("[yellow]Нет сертификатов для удаления.[/yellow]")
                inquirer.text(message="Нажмите Enter для продолжения...").execute()
                continue
            cert_name = inquirer.select(message="Выберите сертификат для удаления:", choices=certs, vi_mode=True).execute()
            if cert_name:
                confirm = inquirer.confirm(message=f"Удалить сертификат {cert_name}?", default=False).execute()
                if confirm:
                    res = run_command(["certbot", "delete", "--cert-name", cert_name], f"Удаление сертификата {cert_name}...")
                    if res and res.returncode == 0:
                        console.print(f"[green]Сертификат {cert_name} удалён.[/green]")
                    else:
                        console.print(f"[red]Ошибка удаления сертификата: {res.stderr if res else ''}[/red]")
                    inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "renew":
            res = run_command(["certbot", "certificates"], "Получение списка сертификатов...")
            certs = []
            if res and res.stdout:
                import re
                certs = re.findall(r"Certificate Name: (.+)", res.stdout)
            if not certs:
                console.print("[yellow]Нет сертификатов для обновления.[/yellow]")
                inquirer.text(message="Нажмите Enter для продолжения...").execute()
                continue
            cert_name = inquirer.select(message="Выберите сертификат для обновления:", choices=certs, vi_mode=True).execute()
            if cert_name:
                res = run_command(["certbot", "renew", "--cert-name", cert_name], f"Обновление сертификата {cert_name}...")
                if res and res.returncode == 0:
                    console.print(f"[green]Сертификат {cert_name} обновлён![/green]")
                else:
                    console.print(f"[red]Ошибка обновления сертификата: {res.stderr if res else ''}[/red]")
                inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "new":
            console.print("[yellow]Для создания нового сертификата используйте деплой сайта или менеджер сайтов![/yellow]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        else:
            break

def _show_github_access_menu():
    clear_console()
    console.print(Panel(get_string("webserver_github_access_title"), border_style="blue"))
    choices = [
        Choice("show_ssh", name=get_string("webserver_github_show_ssh")),
        Choice("back", name=get_string("webserver_github_back")),
    ]
    action = inquirer.select(message=get_string("webserver_github_access_prompt"), choices=choices, vi_mode=True).execute()
    if action == "show_ssh":
        ssh_path = os.path.expanduser("~/.ssh/id_rsa.pub")
        if not os.path.exists(ssh_path):
            os.makedirs(os.path.dirname(ssh_path), exist_ok=True)
            import subprocess
            subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-N", "", "-f", ssh_path[:-4]])
        with open(ssh_path) as f:
            pubkey = f.read().strip()
        console.print(Panel(pubkey, title=get_string("webserver_github_ssh_pubkey_title"), border_style="green"))
        console.print(get_string("webserver_github_ssh_instructions"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()

def _setup_nginx_proxy(project_name, project_dir, port=3000, domain=None):
    # Проверка наличия nginx
    if not os.path.exists("/etc/nginx"):
        console.print("[yellow]Похоже, nginx не установлен или не настроен. Установите nginx через меню или вручную.[/yellow]")
        return
    os.makedirs("/etc/nginx/sites-available", exist_ok=True)
    os.makedirs("/etc/nginx/sites-enabled", exist_ok=True)
    if not domain:
        domain = f"{project_name}.local"
    nginx_conf = f"""
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    conf_path = f"/etc/nginx/sites-available/{project_name}"
    with open(conf_path, "w") as f:
        f.write(nginx_conf)
    # Создаём симлинк в sites-enabled
    enabled_path = f"/etc/nginx/sites-enabled/{project_name}"
    if not os.path.exists(enabled_path):
        try:
            os.symlink(conf_path, enabled_path)
        except FileExistsError:
            pass
    # Отключаем default, если включён
    default_enabled = "/etc/nginx/sites-enabled/default"
    if os.path.exists(default_enabled):
        os.remove(default_enabled)
    # Проверяем конфиг и перезапускаем nginx
    res = run_command(["nginx", "-t"], get_string("webserver_nginx_test"))
    if res and res.returncode == 0:
        run_command(["systemctl", "reload", "nginx"], get_string("webserver_nginx_reload"))
        console.print(Panel(get_string("webserver_nginx_success", domain=domain), title="nginx", border_style="green"))
    else:
        console.print(Panel(res.stderr if res else "Ошибка проверки nginx", title="nginx error", border_style="red"))

def _setup_ssl_certbot(domain):
    if not shutil.which("certbot"):
        console.print("[yellow]Certbot не установлен. SSL не будет настроен.[/yellow]")
        return
    use_ssl = inquirer.confirm(message=get_string("webserver_ssl_certbot_prompt", domain=domain), default=True).execute()
    if not use_ssl:
        return
    # Запускаем certbot
    res = run_command(["certbot", "--nginx", "-d", domain, "--non-interactive", "--agree-tos", "-m", "admin@"+domain], get_string("webserver_ssl_certbot_run", domain=domain))
    if res and res.returncode == 0:
        console.print("[green]SSL-сертификат успешно получен и применён![/green]")
    else:
        console.print(Panel(res.stderr if res else "Ошибка certbot", title="certbot error", border_style="red"))

def _ensure_nginx_installed():
    if not shutil.which("nginx"):
        console.print("[yellow]nginx не найден. Устанавливаю nginx...[/yellow]")
        res = run_command(["apt-get", "update"], "Обновление списка пакетов...")
        res2 = run_command(["apt-get", "install", "-y", "nginx"], "Установка nginx...")
        if res2 and res2.returncode == 0:
            console.print("[green]nginx успешно установлен![/green]")
            return True
        else:
            console.print("[red]Не удалось установить nginx. Проверьте соединение с интернетом и повторите попытку.[/red]")
            return False
    return True

def _is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def _find_process_using_port(port):
    try:
        res = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)
        return res.stdout if res and res.stdout else None
    except Exception:
        return None

def _deploy_nodejs_project():
    # Проверка наличия git
    if not shutil.which("git"):
        install_git = inquirer.confirm(message=get_string("webserver_install_git_prompt"), default=True).execute()
        if install_git:
            res = run_command(["apt-get", "update"], get_string("webserver_apt_update"))
            res = run_command(["apt-get", "install", "-y", "git"], get_string("webserver_apt_install_git"))
            if not shutil.which("git"):
                console.print(get_string("webserver_git_install_fail"))
                return
            else:
                console.print(get_string("webserver_git_install_success"))
        else:
            console.print(get_string("webserver_git_required"))
            return
    # Проверка наличия nodejs и npm
    if not shutil.which("node") or not shutil.which("npm"):
        install_node = inquirer.confirm(message=get_string("webserver_install_node_prompt"), default=True).execute()
        if install_node:
            res = run_command(["apt-get", "update"], get_string("webserver_apt_update"))
            res = run_command(["apt-get", "install", "-y", "nodejs", "npm"], get_string("webserver_apt_install_node"))
            if not shutil.which("node") or not shutil.which("npm"):
                console.print(get_string("webserver_node_install_fail"))
                return
            else:
                console.print(get_string("webserver_node_install_success"))
        else:
            console.print(get_string("webserver_node_required"))
            return
    # Новый UX: только название проекта, путь по умолчанию /var/www/<project>
    project_name = inquirer.text(message=get_string("webserver_project_name_prompt")).execute()
    if not project_name or not project_name.isalnum():
        console.print(get_string("webserver_project_name_invalid"))
        return
    default_dir = f"/var/www/{project_name}"
    use_custom = inquirer.confirm(message=get_string("webserver_custom_dir_prompt", default_dir=default_dir), default=False).execute()
    if use_custom:
        project_dir = inquirer.text(message=get_string("webserver_project_dir_prompt"), default=default_dir).execute()
    else:
        project_dir = default_dir
    repo_url = inquirer.text(message=get_string("webserver_repo_url_prompt")).execute()
    if not repo_url or not project_dir:
        console.print(get_string("webserver_missing_params"))
        return
    # Клонирование или обновление
    if not os.path.exists(project_dir):
        # --- SSH: добавляем github.com в known_hosts ---
        if repo_url.startswith("git@github.com"):
            ssh_dir = os.path.expanduser("~/.ssh")
            os.makedirs(ssh_dir, exist_ok=True)
            known_hosts = os.path.join(ssh_dir, "known_hosts")
            with open(known_hosts, "a") as kh:
                subprocess.run(["ssh-keyscan", "github.com"], stdout=kh)
            env = os.environ.copy()
            env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
        else:
            env = None
        res = run_command(["git", "clone", repo_url, project_dir], get_string("webserver_cloning_repo", repo=repo_url), cwd=None, env=env)
        if not res or res.returncode != 0:
            # Показываем stderr/stdout
            err = res.stderr if res else ""
            out = res.stdout if res else ""
            console.print(Panel((err or "") + "\n" + (out or ""), title="git clone error", border_style="red"))
            # Если ошибка аутентификации — предлагаем варианты
            if err and ("Authentication failed" in err or "Permission denied" in err or "access denied" in err or "fatal: could not read Username" in err):
                auth_choice = inquirer.select(
                    message=get_string("webserver_github_auth_failed"),
                    choices=[
                        Choice("token", get_string("webserver_github_use_token")),
                        Choice("ssh", get_string("webserver_github_use_ssh")),
                        Choice(None, get_string("action_back")),
                    ],
                    vi_mode=True
                ).execute()
                if auth_choice == "token":
                    token = inquirer.text(message=get_string("webserver_github_token_prompt")).execute()
                    # Вставляем токен в url
                    if repo_url.startswith("https://"):
                        repo_url_token = repo_url.replace("https://", f"https://{token}@")
                        res2 = run_command(["git", "clone", repo_url_token, project_dir], get_string("webserver_cloning_repo", repo=repo_url_token))
                        if res2 and res2.returncode == 0:
                            console.print("[green]Клонирование с токеном успешно![/green]")
                        else:
                            console.print(Panel((res2.stderr or "") + "\n" + (res2.stdout or ""), title="git clone error", border_style="red"))
                            return
                    elif repo_url.startswith("git@github.com"):
                        # Повторяем попытку с SSH-URL и env
                        ssh_dir = os.path.expanduser("~/.ssh")
                        os.makedirs(ssh_dir, exist_ok=True)
                        known_hosts = os.path.join(ssh_dir, "known_hosts")
                        with open(known_hosts, "a") as kh:
                            subprocess.run(["ssh-keyscan", "github.com"], stdout=kh)
                        env = os.environ.copy()
                        env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
                        res2 = run_command(["git", "clone", repo_url, project_dir], get_string("webserver_cloning_repo", repo=repo_url), cwd=None, env=env)
                        if res2 and res2.returncode == 0:
                            console.print("[green]Клонирование по SSH успешно![/green]")
                        else:
                            console.print(Panel((res2.stderr or "") + "\n" + (res2.stdout or ""), title="git clone error", border_style="red"))
                            return
                    else:
                        console.print("[red]Токен можно использовать только с HTTPS-URL![/red]")
                        return
                elif auth_choice == "ssh":
                    _show_github_access_menu()
                    return
                else:
                    return
            else:
                return
    else:
        use_existing = inquirer.confirm(message="Папка уже существует. Использовать её для деплоя (без git clone)?", default=True).execute()
        if not use_existing:
            console.print("[yellow]Деплой отменён пользователем, так как папка уже существует.[/yellow]")
            return
        # Не делаем git pull, просто продолжаем деплой
    # Установка зависимостей
    if not shutil.which("npm") or not shutil.which("node"):
        console.print(Panel("[yellow]Node.js и/или npm не найдены![/yellow]", title="Установка Node.js", border_style="yellow"))
        if inquirer.confirm(message="Установить Node.js и npm через apt прямо сейчас?", default=True).execute():
            res = run_command(["apt-get", "update"], "Обновление списка пакетов...")
            res = run_command(["apt-get", "install", "-y", "nodejs", "npm"], "Установка Node.js и npm...")
        else:
            console.print(Panel("[red]Node.js и npm обязательны для деплоя Node.js-проектов! Установите их вручную: apt install nodejs npm[/red]", title="Ошибка деплоя", border_style="red"))
            return
    # Повторная проверка после установки
    if not shutil.which("npm") or not shutil.which("node"):
        console.print(Panel(f"[red]Node.js и npm всё ещё не найдены!\nPATH={os.environ.get('PATH')}\nПроверьте, что они установлены и доступны для пользователя {getpass.getuser()}.[/red]", title="Ошибка деплоя", border_style="red"))
        return
    # Проверка прав на директорию
    if not os.access(project_dir, os.W_OK):
        console.print(Panel(f"[red]Нет прав на запись в директорию {project_dir}!\nПроверьте владельца и права доступа.[/red]", title="Ошибка деплоя", border_style="red"))
        return
    node_modules_dir = os.path.join(project_dir, "node_modules")
    if os.path.exists(node_modules_dir) and not os.access(node_modules_dir, os.W_OK):
        console.print(Panel(f"[red]Нет прав на запись в {node_modules_dir}!\nПроверьте владельца и права доступа.[/red]", title="Ошибка деплоя", border_style="red"))
        return
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        res = run_command(["yarn", "install"], get_string("webserver_yarn_install"), cwd=project_dir)
    else:
        res = run_command(["npm", "install"], get_string("webserver_npm_install"), cwd=project_dir)
    if res is None:
        console.print(Panel("[red]Не удалось запустить npm install (ошибка запуска процесса)[/red]", title="npm install error", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    if res.returncode != 0:
        err = res.stderr or ""
        out = res.stdout or ""
        if not err and not out:
            console.print(Panel("[red]npm не найден или не удалось запустить процесс. Проверьте, установлен ли npm и доступен ли он в PATH.[/red]", title="npm install error", border_style="red"))
        else:
            console.print(Panel((err or "") + "\n" + (out or ""), title="npm install error", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    # Проверка наличия next (или других ключевых пакетов)
    pkg_path = os.path.join(project_dir, "package.json")
    with open(pkg_path) as f:
        pkg = json.load(f)
    dependencies = pkg.get("dependencies", {})
    dev_dependencies = pkg.get("devDependencies", {})
    need_next = False
    if "next" in dependencies or "next" in dev_dependencies or os.path.exists(os.path.join(project_dir, "next.config.js")):
        need_next = True
    if need_next and not os.path.exists(os.path.join(project_dir, "node_modules", "next")):
        console.print(Panel("[red]Пакет 'next' не установлен после npm install! Проверьте package.json и интернет-соединение.[/red]", title="Ошибка деплоя", border_style="red"))
        return
    # Сборка
    if os.path.exists(os.path.join(project_dir, "package.json")):
        res = run_command(["npm", "run", "build"], get_string("webserver_build"), cwd=project_dir)
        if not res or res.returncode != 0:
            err = res.stderr if res else ""
            out = res.stdout if res else ""
            console.print(Panel((err or "") + "\n" + (out or ""), title="npm build error", border_style="red"))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return
    # --- Проверка package.json и скриптов ---
    pkg_path = os.path.join(project_dir, "package.json")
    if not os.path.exists(pkg_path):
        console.print(Panel("[red]В проекте отсутствует package.json! Деплой невозможен.[/red]", title="Ошибка деплоя", border_style="red"))
        return
    with open(pkg_path) as f:
        pkg = json.load(f)
    scripts = pkg.get("scripts", {})
    start_script = scripts.get("start")
    alt_script = None
    for alt in ("dev", "serve", "preview"):  # альтернативные скрипты
        if scripts.get(alt):
            alt_script = alt
            break
    if not start_script and not alt_script:
        console.print(Panel("[red]В package.json отсутствует скрипт 'start', 'dev', 'serve' или 'preview'. Укажите его для автозапуска![/red]", title="Ошибка деплоя", border_style="red"))
        console.print("Пример:")
        console.print('{\n  "scripts": {\n    "start": "node index.js"\n  }\n}')
        return
    # --- Определение команды запуска ---
    if start_script:
        pm2_cmd = ["pm2", "start", "npm", "--name", project_name, "--", "start"]
        cmd_descr = "npm start"
    else:
        pm2_cmd = ["pm2", "start", "npm", "--name", project_name, "--", alt_script]
        cmd_descr = f"npm run {alt_script}"
    console.print(Panel(f"[cyan]Запуск приложения командой:[/cyan] {cmd_descr}", title="pm2", border_style="cyan"))
    # --- PM2: удалить старый процесс ---
    run_command(["pm2", "delete", project_name], spinner_message=f"Удаление старого pm2 процесса {project_name}...", cwd=project_dir)
    # --- PM2: запуск ---
    res_pm2 = run_command(pm2_cmd, spinner_message=f"Запуск pm2 для {project_name}...", cwd=project_dir)
    if not res_pm2 or res_pm2.returncode != 0:
        err = res_pm2.stderr if res_pm2 else ""
        out = res_pm2.stdout if res_pm2 else ""
        console.print(Panel((err or "") + "\n" + (out or ""), title="pm2 error", border_style="red"))
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    # --- Запрос порта ---
    default_port = 3000
    while True:
        port_str = inquirer.text(message=f"Введите порт для приложения (по умолчанию {default_port}):", default=str(default_port)).execute()
        try:
            port = int(port_str)
        except Exception:
            console.print("[red]Порт должен быть числом.[/red]")
            continue
        if _is_port_in_use(port):
            proc_info = _find_process_using_port(port)
            console.print(f"[red]Порт {port} уже занят![/red]")
            if proc_info:
                console.print(f"[yellow]Информация о процессе, занимающем порт:[/yellow]\n{proc_info}")
            action = inquirer.select(message=f"Порт {port} занят. Что сделать?", choices=[
                ("change", "Выбрать другой порт"),
                ("kill", f"Завершить процесс на порту {port}"),
                (None, "Отмена деплоя")
            ]).execute()
            if action == "change":
                continue
            elif action == "kill":
                # Попробуем завершить процесс
                import re
                pids = re.findall(r"\b(\d+)\b", proc_info)
                killed = False
                for pid in pids:
                    try:
                        os.kill(int(pid), 9)
                        console.print(f"[green]Процесс {pid} завершён.[/green]")
                        killed = True
                    except Exception as e:
                        console.print(f"[red]Не удалось завершить процесс {pid}: {e}[/red]")
                if not killed:
                    console.print("[red]Не удалось завершить ни один процесс. Попробуйте вручную.[/red]")
                continue
            else:
                return
        else:
            break
    # --- Проверка и установка nginx ---
    if not _ensure_nginx_installed():
        return
    # --- Запрос домена с валидацией ---
    while True:
        domain = inquirer.text(message=get_string("webserver_nginx_domain_prompt"), default=f"{project_name}.local").execute()
        if domain and " " not in domain:
            break
        console.print("[red]Домен не должен быть пустым и не должен содержать пробелов.[/red]")
    _setup_nginx_proxy(project_name, project_dir, port=port, domain=domain)
    # --- NPM/Yarn install ---
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        res = run_command(["yarn", "install"], get_string("webserver_yarn_install"), cwd=project_dir)
    else:
        res = run_command(["npm", "install"], get_string("webserver_npm_install"), cwd=project_dir)
    # Сборка
    if os.path.exists(os.path.join(project_dir, "package.json")):
        res = run_command(["npm", "run", "build"], get_string("webserver_build"), cwd=project_dir)
    # --- Проверка статуса pm2 ---
    try:
        status_res = subprocess.run(["pm2", "status", project_name], capture_output=True, text=True, timeout=3)
        if status_res.returncode != 0 or "online" not in status_res.stdout:
            console.print(f"[red]Приложение не запущено (pm2 status не online)![/red]\n{status_res.stdout}")
            # Показать последние строки лога
            log_res = subprocess.run(["pm2", "logs", project_name, "--lines", "10", "--nostream"], capture_output=True, text=True, timeout=3)
            if log_res and log_res.stdout:
                console.print(Panel(log_res.stdout[-1500:], title=f"pm2 logs {project_name}", border_style="red"))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
            return
    except Exception as e:
        console.print(f"[red]Ошибка при проверке статуса pm2: {e}[/red]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    # --- SSL: предложение установить certbot и настроить SSL ---
    if not shutil.which("certbot"):
        install_ssl = inquirer.confirm(
            message="Certbot не установлен. Хотите установить Certbot и настроить бесплатный SSL для вашего домена?",
            default=True
        ).execute()
        if install_ssl:
            res = run_command(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"], "Установка Certbot...")
            if res and res.returncode == 0:
                console.print("[green]Certbot успешно установлен![/green]")
                _setup_ssl_certbot(domain)
            else:
                console.print("[red]Не удалось установить Certbot. Настройте SSL вручную.[/red]")
        else:
            console.print("[yellow]SSL не настроен. Вы можете сделать это позже через меню.[/yellow]")
    else:
        setup_ssl = inquirer.confirm(
            message="Хотите сразу настроить бесплатный SSL для вашего домена через Certbot?",
            default=True
        ).execute()
        if setup_ssl:
            _setup_ssl_certbot(domain)
    # Сохраняем инфу о сайте
    site_info = {
        "name": project_name,
        "dir": project_dir,
        "repo_url": repo_url,
        "domain": domain,
        "port": port,
        "pm2_name": project_name,
        "nginx_conf": f"/etc/nginx/sites-available/{project_name}",
        "ssl": shutil.which("certbot") is not None
    }
    _save_site(site_info)
    # --- Показываем статус pm2 и последние строки лога ---
    try:
        status_res = subprocess.run(["pm2", "status", project_name], capture_output=True, text=True, timeout=3)
        console.print(Panel(status_res.stdout, title=f"pm2 status {project_name}", border_style="cyan"))
        log_res = subprocess.run(["pm2", "logs", project_name, "--lines", "10", "--nostream"], capture_output=True, text=True, timeout=3)
        if log_res and log_res.stdout:
            console.print(Panel(log_res.stdout[-1500:], title=f"pm2 logs {project_name}", border_style="green"))
    except Exception as e:
        console.print(f"[yellow]Не удалось получить статус или лог pm2: {e}[/yellow]")
    inquirer.text(message=get_string("press_enter_to_continue")).execute()

def _site_actions_menu(site):
    import subprocess
    while True:
        clear_console()
        # --- Статус сайта через pm2 ---
        pm2_status = None
        pm2_missing = False
        status_timeout = False
        try:
            with Live("[yellow]Получение статуса pm2...[/yellow]", refresh_per_second=4, transient=True):
                res = subprocess.run(["pm2", "status", site["pm2_name"]], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and site["pm2_name"] in res.stdout:
                if "online" in res.stdout:
                    pm2_status = "running"
                elif "stopped" in res.stdout or "errored" in res.stdout:
                    pm2_status = "stopped"
                elif "errored" in res.stdout:
                    pm2_status = "error"
                else:
                    pm2_status = "unknown"
            else:
                pm2_status = "stopped"
        except subprocess.TimeoutExpired:
            status_timeout = True
            pm2_status = "unknown"
        except FileNotFoundError:
            pm2_missing = True
            pm2_status = "unknown"
        # --- SSL статус ---
        ssl_hint = ""
        if not site.get("ssl"):
            ssl_hint = get_string("site_hint_ssl_missing")
        # --- Подсказки ---
        hints = []
        if pm2_missing:
            hints.append(get_string("site_hint_pm2_missing"))
        elif pm2_status == "stopped":
            hints.append(get_string("site_hint_stopped"))
        if ssl_hint:
            hints.append(ssl_hint)
        if status_timeout:
            hints.append("[yellow]pm2 status: превышено время ожидания[/yellow]")
        # --- Цветной статус ---
        if pm2_status == "running":
            status_str = get_string("site_status_running")
        elif pm2_status == "stopped":
            status_str = get_string("site_status_stopped")
        elif pm2_status == "error":
            status_str = get_string("site_status_error")
        else:
            status_str = get_string("site_status_unknown")
        # --- Мини-лог pm2 ---
        minilog = ""
        log_timeout = False
        try:
            with Live("[yellow]Загрузка последних строк лога...[/yellow]", refresh_per_second=4, transient=True):
                log_res = subprocess.run(["pm2", "logs", site["pm2_name"], "--lines", "5", "--nostream"], capture_output=True, text=True, timeout=10)
            if log_res.returncode == 0 and log_res.stdout.strip():
                minilog = log_res.stdout.strip()[-1000:]
            else:
                minilog = get_string("site_minilog_empty")
        except subprocess.TimeoutExpired:
            minilog = "[yellow]pm2 logs: превышено время ожидания[/yellow]"
            log_timeout = True
        except Exception:
            minilog = get_string("site_minilog_empty")
        # --- Панель сайта ---
        info = f"[bold]Имя:[/bold] {site['name']}\n[bold]Домен:[/bold] {site['domain']}\n[bold]Порт:[/bold] {site['port']}\n[bold]Путь:[/bold] {site['dir']}\n[bold]PM2:[/bold] {site['pm2_name']}\n[bold]nginx:[/bold] {site['nginx_conf']}\n[bold]SSL:[/bold] {'Да' if site.get('ssl') else 'Нет'}\n[bold]Статус:[/bold] {status_str}"
        panel = Panel(info, title=f"Сайт: {site['name']}", border_style="blue")
        console.print(panel)
        # --- Подсказки ---
        if hints:
            for h in hints:
                console.print(h)
        # --- Мини-лог ---
        console.print(Panel(minilog, title=get_string("site_minilog_title"), border_style="grey37"))
        # --- Меню действий ---
        choices = [
            Choice("open", name=get_string("site_action_open")),
            Choice("logs", name=get_string("site_action_logs")),
            Choice("restart", name=get_string("site_action_restart")),
            Choice("stop", name=get_string("site_action_stop")),
            Choice("start", name=get_string("site_action_start")),
            Choice("nginx", name=get_string("site_action_nginx")),
            Choice("ssl", name=get_string("site_action_ssl")),
            Choice("delete", name=get_string("site_action_delete")),
            Choice(None, name=get_string("action_back")),
        ]
        action = inquirer.select(message=get_string("site_actions_prompt", name=site['name']), choices=choices, vi_mode=True).execute()
        # --- Всплывающее уведомление ---
        def notify_success(action):
            console.print(get_string("site_action_success", action=get_string(action)))
        def notify_fail(action, error):
            console.print(get_string("site_action_fail", error=error))
        if action == "open":
            url = f"https://{site['domain']}" if site.get('ssl') else f"http://{site['domain']}"
            console.print(Panel(url, title="URL", border_style="cyan"))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "logs":
            try:
                with Live("[yellow]Загрузка лога...[/yellow]", refresh_per_second=4, transient=True):
                    res = subprocess.run(["pm2", "logs", site["pm2_name"]], capture_output=True, text=True, timeout=3)
                if res and res.stdout:
                    console.print(Panel(res.stdout[-1000:], title=f"pm2 logs {site['pm2_name']}", border_style="green"))
                    notify_success("site_action_logs")
                else:
                    notify_fail("site_action_logs", res.stderr if res else "")
            except subprocess.TimeoutExpired:
                console.print("[yellow]pm2 logs: превышено время ожидания[/yellow]")
                notify_fail("site_action_logs", "timeout")
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "restart":
            res = run_command(["pm2", "restart", site["pm2_name"]], get_string("site_action_restart"))
            if res and res.returncode == 0:
                notify_success("site_action_restart")
            else:
                notify_fail("site_action_restart", res.stderr if res else "")
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "stop":
            res = run_command(["pm2", "stop", site["pm2_name"]], get_string("site_action_stop"))
            if res and res.returncode == 0:
                notify_success("site_action_stop")
            else:
                notify_fail("site_action_stop", res.stderr if res else "")
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "start":
            res = run_command(["pm2", "start", site["pm2_name"]], get_string("site_action_start"))
            if res and res.returncode == 0:
                notify_success("site_action_start")
            else:
                notify_fail("site_action_start", res.stderr if res else "")
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "nginx":
            try:
                _setup_nginx_proxy(site['name'], site['dir'], port=site['port'], domain=site['domain'])
                notify_success("site_action_nginx")
            except Exception as e:
                notify_fail("site_action_nginx", str(e))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "ssl":
            try:
                _setup_ssl_certbot(site['domain'])
                notify_success("site_action_ssl")
            except Exception as e:
                notify_fail("site_action_ssl", str(e))
            inquirer.text(message=get_string("press_enter_to_continue")).execute()
        elif action == "delete":
            confirm = inquirer.confirm(message=get_string("site_action_delete_confirm", name=site['name']), default=False).execute()
            if confirm:
                # Удалить процесс pm2 (без ошибок, даже если не запущен)
                try:
                    run_command(["pm2", "delete", site["pm2_name"]], get_string("site_action_delete_pm2"))
                except Exception as e:
                    console.print(f"[yellow]Ошибка при удалении pm2 процесса: {e}[/yellow]")
                # Удалить nginx-конфиг
                try:
                    if os.path.exists(site["nginx_conf"]):
                        os.remove(site["nginx_conf"])
                except Exception as e:
                    console.print(f"[yellow]Ошибка при удалении nginx-конфига: {e}[/yellow]")
                enabled = f"/etc/nginx/sites-enabled/{site['name']}"
                try:
                    if os.path.exists(enabled):
                        os.remove(enabled)
                except Exception as e:
                    console.print(f"[yellow]Ошибка при удалении симлинка nginx: {e}[/yellow]")
                run_command(["systemctl", "reload", "nginx"], get_string("webserver_nginx_reload"))
                # Удалить директорию сайта (рекурсивно)
                try:
                    if os.path.exists(site["dir"]):
                        shutil.rmtree(site["dir"])
                        console.print(f"[green]Директория сайта {site['dir']} удалена.[/green]")
                except Exception as e:
                    console.print(f"[yellow]Ошибка при удалении директории сайта: {e}[/yellow]")
                # Удалить из deployed_sites.json
                sites = _load_sites()
                sites = [s for s in sites if s["name"] != site["name"]]
                with open(SITES_FILE, "w") as f:
                    json.dump(sites, f, indent=2)
                notify_success("site_action_delete")
                inquirer.text(message=get_string("press_enter_to_continue")).execute()
                break
            else:
                continue
        else:
            break

def _show_sites_manager():
    sites = _load_sites()
    if not sites:
        console.print("[yellow]Нет задеплоенных сайтов.[/yellow]")
        inquirer.text(message=get_string("press_enter_to_continue")).execute()
        return
    while True:
        clear_console()
        choices = []
        port_conflicts = {}
        for site in sites:
            port = site.get("port", 3000)
            port_status = ""
            if _is_port_in_use(port):
                proc_info = _find_process_using_port(port)
                # --- Новый блок: определяем, кто занимает порт ---
                pm2_pid = None
                pm2_pids = set()
                try:
                    import subprocess
                    pm2_name = site.get("pm2_name")
                    if pm2_name and shutil.which("pm2"):
                        res = subprocess.run(["pm2", "pid", pm2_name], capture_output=True, text=True, timeout=2)
                        if res and res.returncode == 0 and res.stdout:
                            # pm2 pid может вернуть несколько PID через запятую или пробел
                            import re
                            pm2_pids = set(int(pid) for pid in re.findall(r"\d+", res.stdout))
                except Exception:
                    pass
                # Получаем PID(ы) процесса, занимающего порт
                import re
                port_pids = set(int(pid) for pid in re.findall(r"\b(\d+)\b", proc_info) if int(pid) != port and int(pid) > 100)
                # Если среди PID есть pm2_pid — не показываем освобождение
                if pm2_pids and port_pids & pm2_pids:
                    port_status = f"[red] (порт {port} занят pm2-процессом этого сайта)"
                    # Не добавляем в port_conflicts
                else:
                    port_status = f"[red] (порт {port} занят)"
                    port_conflicts[site["name"]] = (port, proc_info)
            else:
                port_status = f"[green] (порт {port} свободен)"
            choices.append(Choice(site["name"], name=f"{site['name']} ({site['domain']}){port_status}"))
        # Добавить быстрые действия для освобождения порта
        for site_name, (port, proc_info) in port_conflicts.items():
            choices.append(Choice(f"freeport__{site_name}", name=f"Освободить порт {port} для {site_name}"))
        choices.append(Choice(None, name=get_string("action_back")))
        selected = inquirer.select(message=get_string("sites_manager_prompt"), choices=choices, vi_mode=True).execute()
        if not selected:
            break
        if selected.startswith("freeport__"):
            site_name = selected.replace("freeport__", "")
            port, proc_info = port_conflicts.get(site_name, (None, None))
            if port and proc_info:
                import re
                # Улучшенный парсинг PID: только уникальные, не равные порту, >100
                pids = set(int(pid) for pid in re.findall(r"\b(\d+)\b", proc_info) if int(pid) != port and int(pid) > 100)
                killed = False
                for pid in pids:
                    try:
                        os.kill(pid, 9)
                        console.print(f"[green]Процесс {pid} завершён для освобождения порта {port}.[/green]")
                        killed = True
                    except Exception as e:
                        console.print(f"[red]Не удалось завершить процесс {pid}: {e}[/red]")
                if not killed:
                    console.print("[red]Не удалось завершить ни один процесс. Попробуйте вручную.[/red]")
                inquirer.text(message="Нажмите Enter для обновления меню...").execute()
            continue
        site = next((s for s in sites if s["name"] == selected), None)
        if not site:
            break
        _site_actions_menu(site)

def _uninstall_nginx():
    confirm = inquirer.confirm(message="Вы уверены, что хотите полностью удалить nginx и все его конфиги?", default=False).execute()
    if not confirm:
        return
    res = run_command(["apt-get", "purge", "-y", "nginx", "nginx-common", "nginx-full"], "Удаление nginx...")
    if res and res.returncode == 0:
        console.print("[green]nginx успешно удалён![/green]")
        run_command(["rm", "-rf", "/etc/nginx"], "Удаление /etc/nginx...")
    else:
        console.print("[red]Не удалось удалить nginx.[/red]")
        if res and res.stderr:
            console.print(Panel(res.stderr, title="[red]Ошибка[/red]", border_style="red"))
    inquirer.text(message="Нажмите Enter для продолжения...").execute()

def _uninstall_certbot():
    confirm = inquirer.confirm(message="Вы уверены, что хотите полностью удалить certbot?", default=False).execute()
    if not confirm:
        return
    res = run_command(["apt-get", "purge", "-y", "certbot", "python3-certbot-nginx"], "Удаление certbot...")
    if res and res.returncode == 0:
        console.print("[green]certbot успешно удалён![/green]")
    else:
        console.print("[red]Не удалось удалить certbot.[/red]")
        if res and res.stderr:
            console.print(Panel(res.stderr, title="[red]Ошибка[/red]", border_style="red"))
    inquirer.text(message="Нажмите Enter для продолжения...").execute()

def run_webserver_manager():
    # --- Автоматическая проверка nginx ---
    if not shutil.which("nginx"):
        console.print("[yellow]nginx не найден. Установите nginx через меню или вручную![/yellow]")
        if inquirer.confirm(message="Установить nginx сейчас?", default=True).execute():
            _install_nginx()
        else:
            inquirer.text(message="Нажмите Enter для возврата в меню...").execute()
            return
    # Проверка статуса сервиса
    res = run_command(["systemctl", "is-active", "nginx"])
    if not res or res.stdout.strip() != "active":
        console.print("[yellow]nginx не запущен! Запустите его командой: systemctl start nginx[/yellow]")
        if inquirer.confirm(message="Запустить nginx сейчас?", default=True).execute():
            run_command(["systemctl", "start", "nginx"], spinner_message="Запуск nginx...")
        else:
            inquirer.text(message="Нажмите Enter для возврата в меню...").execute()
            return
    # Проверка валидности конфига
    res = run_command(["nginx", "-t"])
    if not res or res.returncode != 0:
        console.print(Panel(res.stderr if res else "nginx -t error", title="nginx error", border_style="red"))
        # --- Авто-очистка битых симлинков ---
        cleaned = False
        sites_enabled = "/etc/nginx/sites-enabled/"
        for symlink in glob.glob(sites_enabled + "*"):
            if os.path.islink(symlink):
                target = os.readlink(symlink)
                if not os.path.exists(target):
                    try:
                        os.remove(symlink)
                        cleaned = True
                        console.print(f"[yellow]Удалён битый симлинк: {symlink} -> {target}[/yellow]")
                    except Exception as e:
                        console.print(f"[red]Ошибка при удалении симлинка {symlink}: {e}[/red]")
        if cleaned:
            res = run_command(["nginx", "-t"])
            if res and res.returncode == 0:
                run_command(["systemctl", "reload", "nginx"], spinner_message="Перезапуск nginx...")
                console.print("[green]Битые симлинки удалены, nginx конфиг теперь валиден![/green]")
            else:
                console.print(Panel(res.stderr if res else "nginx -t error", title="nginx error", border_style="red"))
        # Если всё ещё ошибка — предложить пересоздать конфиги
        if not res or res.returncode != 0:
            if inquirer.confirm(message="nginx конфиг всё ещё невалиден. Пересоздать конфиги для всех сайтов?", default=True).execute():
                sites = _load_sites()
                for site in sites:
                    try:
                        _setup_nginx_proxy(site['name'], site['dir'], port=site.get('port', 3000), domain=site.get('domain'))
                        console.print(f"[green]Конфиг nginx для {site['name']} пересоздан.[/green]")
                    except Exception as e:
                        console.print(f"[red]Ошибка при пересоздании конфига для {site['name']}: {e}[/red]")
                res = run_command(["nginx", "-t"])
                if res and res.returncode == 0:
                    run_command(["systemctl", "reload", "nginx"], spinner_message="Перезапуск nginx...")
                    console.print("[green]nginx конфиг теперь валиден после пересоздания![/green]")
                else:
                    console.print(Panel(res.stderr if res else "nginx -t error", title="nginx error", border_style="red"))
                    inquirer.text(message="nginx конфиг невалиден! Исправьте ошибки вручную и повторите попытку.").execute()
                    return
            else:
                inquirer.text(message="nginx конфиг невалиден! Исправьте ошибки вручную и повторите попытку.").execute()
                return
    while True:
        clear_console()
        console.print(Panel("[bold green]Менеджер веб-сервера и деплоя[/bold green]", border_style="green"))
        choices = [
            Choice("install_nginx", name="Установить/проверить Nginx"),
            Choice("install_certbot", name="Установить/проверить Certbot (SSL)"),
        ]
        if shutil.which("nginx"):
            choices.append(Choice("uninstall_nginx", name="Удалить nginx"))
        if shutil.which("certbot"):
            choices.append(Choice("uninstall_certbot", name="Удалить certbot"))
        choices.extend([
            Choice("deploy_nodejs", name="Задеплоить Node.js/Next.js проект с GitHub"),
            Choice("deploy_existing", name="Додеплоить проект из существующей папки"),
            Choice("sites_manager", name=get_string("sites_manager_menu")),
            Choice("github_access", name=get_string("webserver_github_access_menu")),
            Choice("deploy_python", name="Задеплоить Python-проект (скоро)"),
            Choice("deploy_php", name="Задеплоить PHP-проект (скоро)"),
            Choice("deploy_static", name="Задеплоить статический сайт (скоро)"),
            Choice(None, name="Назад")
        ])
        action = inquirer.select(
            message="Выберите действие:",
            choices=choices,
            vi_mode=True
        ).execute()
        if action == "install_nginx":
            _install_nginx()
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "install_certbot":
            _install_certbot()
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action == "uninstall_nginx":
            _uninstall_nginx()
        elif action == "uninstall_certbot":
            _uninstall_certbot()
        elif action == "deploy_nodejs":
            _deploy_nodejs_project()
        elif action == "deploy_existing":
            _deploy_existing_nodejs_project()
        elif action == "sites_manager":
            _show_sites_manager()
        elif action == "github_access":
            _show_github_access_menu()
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        elif action in ("deploy_python", "deploy_php", "deploy_static"):
            console.print("[yellow]Скоро будет доступно![/yellow]")
            inquirer.text(message="Нажмите Enter для продолжения...").execute()
        else:
            break

# --- Деплой из существующей папки ---
def _deploy_existing_nodejs_project():
    project_dir = inquirer.text(message="Введите путь к существующей папке проекта:").execute()
    if not project_dir or not os.path.exists(project_dir):
        console.print("[red]Папка не найдена![/red]")
        return
    pkg_path = os.path.join(project_dir, "package.json")
    if not os.path.exists(pkg_path):
        console.print("[red]В папке не найден package.json! Это не Node.js проект.[/red]")
        return
    with open(pkg_path) as f:
        pkg = json.load(f)
    project_name = pkg.get("name") or os.path.basename(project_dir)
    if not project_name or not project_name.isalnum():
        project_name = inquirer.text(message="Введите название проекта (латиницей, без пробелов):").execute()
        if not project_name or not project_name.isalnum():
            console.print("[red]Некорректное название проекта.[/red]")
            return
    # Установка зависимостей
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        res = run_command(["yarn", "install"], get_string("webserver_yarn_install"), cwd=project_dir)
    else:
        res = run_command(["npm", "install"], get_string("webserver_npm_install"), cwd=project_dir)
    if res is None or res.returncode != 0:
        console.print("[red]Ошибка установки зависимостей![/red]")
        return
    # Сборка
    if os.path.exists(os.path.join(project_dir, "package.json")):
        res = run_command(["npm", "run", "build"], get_string("webserver_build"), cwd=project_dir)
        if not res or res.returncode != 0:
            console.print("[red]Ошибка сборки проекта![/red]")
            return
    # Определение скрипта запуска
    scripts = pkg.get("scripts", {})
    start_script = scripts.get("start")
    alt_script = None
    for alt in ("dev", "serve", "preview"):
        if scripts.get(alt):
            alt_script = alt
            break
    if not start_script and not alt_script:
        console.print("[red]В package.json отсутствует скрипт 'start', 'dev', 'serve' или 'preview'. Укажите его для автозапуска![/red]")
        return
    # Запрос порта
    default_port = 3000
    while True:
        port_str = inquirer.text(message=f"Введите порт для приложения (по умолчанию {default_port}):", default=str(default_port)).execute()
        try:
            port = int(port_str)
        except Exception:
            console.print("[red]Порт должен быть числом.[/red]")
            continue
        if _is_port_in_use(port):
            proc_info = _find_process_using_port(port)
            console.print(f"[red]Порт {port} уже занят![/red]")
            if proc_info:
                console.print(f"[yellow]Информация о процессе, занимающем порт:[/yellow]\n{proc_info}")
            action = inquirer.select(message=f"Порт {port} занят. Что сделать?", choices=[
                ("change", "Выбрать другой порт"),
                ("kill", f"Завершить процесс на порту {port}"),
                (None, "Отмена деплоя")
            ]).execute()
            if action == "change":
                continue
            elif action == "kill":
                import re
                pids = re.findall(r"\\b(\\d+)\\b", proc_info)
                killed = False
                for pid in pids:
                    try:
                        os.kill(int(pid), 9)
                        console.print(f"[green]Процесс {pid} завершён.[/green]")
                        killed = True
                    except Exception as e:
                        console.print(f"[red]Не удалось завершить процесс {pid}: {e}[/red]")
                if not killed:
                    console.print("[red]Не удалось завершить ни один процесс. Попробуйте вручную.[/red]")
                continue
            else:
                return
        else:
            break
    # Проверка и установка nginx
    if not _ensure_nginx_installed():
        return
    # Запрос домена
    while True:
        domain = inquirer.text(message=get_string("webserver_nginx_domain_prompt"), default=f"{project_name}.local").execute()
        if domain and " " not in domain:
            break
        console.print("[red]Домен не должен быть пустым и не должен содержать пробелов.[/red]")
    _setup_nginx_proxy(project_name, project_dir, port=port, domain=domain)
    # PM2 запуск
    if start_script:
        pm2_cmd = ["pm2", "start", "npm", "--name", project_name, "--", "start"]
    else:
        pm2_cmd = ["pm2", "start", "npm", "--name", project_name, "--", alt_script]
    run_command(["pm2", "delete", project_name], spinner_message=f"Удаление старого pm2 процесса {project_name}...", cwd=project_dir)
    res_pm2 = run_command(pm2_cmd, spinner_message=f"Запуск pm2 для {project_name}...", cwd=project_dir)
    if not res_pm2 or res_pm2.returncode != 0:
        console.print("[red]Ошибка запуска pm2![/red]")
        return
    # SSL
    if not shutil.which("certbot"):
        install_ssl = inquirer.confirm(
            message="Certbot не установлен. Хотите установить Certbot и настроить бесплатный SSL для вашего домена?",
            default=True
        ).execute()
        if install_ssl:
            res = run_command(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"], "Установка Certbot...")
            if res and res.returncode == 0:
                console.print("[green]Certbot успешно установлен![/green]")
                _setup_ssl_certbot(domain)
            else:
                console.print("[red]Не удалось установить Certbot. Настройте SSL вручную.[/red]")
        else:
            console.print("[yellow]SSL не настроен. Вы можете сделать это позже через меню.[/yellow]")
    else:
        setup_ssl = inquirer.confirm(
            message="Хотите сразу настроить бесплатный SSL для вашего домена через Certbot?",
            default=True
        ).execute()
        if setup_ssl:
            _setup_ssl_certbot(domain)
    # Сохраняем инфу о сайте
    site_info = {
        "name": project_name,
        "dir": project_dir,
        "repo_url": None,
        "domain": domain,
        "port": port,
        "pm2_name": project_name,
        "nginx_conf": f"/etc/nginx/sites-available/{project_name}",
        "ssl": shutil.which("certbot") is not None
    }
    _save_site(site_info)
    # Показываем статус pm2 и лог
    try:
        status_res = subprocess.run(["pm2", "status", project_name], capture_output=True, text=True, timeout=3)
        console.print(Panel(status_res.stdout, title=f"pm2 status {project_name}", border_style="cyan"))
        log_res = subprocess.run(["pm2", "logs", project_name, "--lines", "10", "--nostream"], capture_output=True, text=True, timeout=3)
        if log_res and log_res.stdout:
            console.print(Panel(log_res.stdout[-1500:], title=f"pm2 logs {project_name}", border_style="green"))
    except Exception as e:
        console.print(f"[yellow]Не удалось получить статус или лог pm2: {e}[/yellow]")
    inquirer.text(message=get_string("press_enter_to_continue")).execute() 