import subprocess
import re
import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from rich.panel import Panel
import datetime

from localization import get_string

console = Console()

# --- Пояснения к параметрам SSH ---
SSH_PARAM_EXPLANATIONS = {
    "PermitRootLogin": get_string("ssh_param_explain_permitroot"),
    "PasswordAuthentication": get_string("ssh_param_explain_passwordauth"),
    "Protocol": get_string("ssh_param_explain_protocol"),
    "X11Forwarding": get_string("ssh_param_explain_x11"),
}

CHKROOTKIT_LOG_PATH = "/var/log/chkrootkit.log"
LYNIS_LOG_PATH = "/var/log/lynis.log"

def _check_and_install_utility(utility_name, package_name):
    """Checks if a utility is installed and prompts to install it if not."""
    if shutil.which(utility_name) is not None:
        return True

    console.print(get_string("chkrootkit_not_found", package=utility_name))
    wants_install = inquirer.confirm(
        message=get_string("install_prompt"),
        default=False
    ).execute()

    if wants_install:
        if os.geteuid() != 0:
            console.print(get_string("need_root_warning"))
            return False
        
        try:
            console.print(get_string("installing_package", package=package_name))
            # First, update package list
            subprocess.run(['apt-get', 'update'], check=True, capture_output=True, text=True)
            # Then, install the package
            subprocess.run(['apt-get', 'install', '-y', package_name], check=True, capture_output=True, text=True)
            console.print(get_string("install_success", package=package_name))
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(get_string("install_fail", package=package_name))
            console.print(e.stderr or e)
            return False
    return False

def check_open_ports():
    """Checks for open TCP and UDP ports and the processes using them."""
    console.print(f"\n[bold cyan]{get_string('port_scan_option')}[/bold cyan]")

    if os.geteuid() != 0:
        console.print(get_string("need_root_warning"))
        # We can still run ss without sudo, just won't get process info
        cmd = ['ss', '-tuln']
    else:
        cmd = ['ss', '-tulnp']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            console.print(get_string("no_ports_msg"))
            return

        table = Table(title=get_string("open_ports_title"))
        table.add_column(get_string("protocol_col"), justify="left", style="cyan", no_wrap=True)
        table.add_column(get_string("address_col"), justify="left", style="magenta")
        table.add_column(get_string("process_col"), justify="left", style="green")

        for line in lines[1:]: # Skip header
            parts = line.split()
            proto = parts[0]
            address = parts[4]
            process_info = "N/A"
            if len(parts) > 6 and 'users:' in line:
                # Extracts process name from users:(("systemd",pid=1,fd=41))
                match = re.search(r'users:\(\("([^"]+)"', line)
                if match:
                    process_info = match.group(1)
            
            table.add_row(proto, address, process_info)

        if table.rows:
            console.print(table)
        else:
            console.print(get_string("no_ports_msg"))

    except FileNotFoundError:
        console.print(get_string("ss_not_found_err"))
    except subprocess.CalledProcessError as e:
        console.print(get_string("ss_exec_err", e=e))

def check_system_updates():
    """Checks for available package updates using apt."""
    console.print(f"\n[bold cyan]{get_string('system_updates_option')}[/bold cyan]")
    try:
        # Inform user about apt update
        # result = subprocess.run(['apt', 'update'], capture_output=True, text=True)
        result = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True, text=True, check=False)
        lines = result.stdout.strip().split('\n')

        if "WARNING" in result.stderr or len(lines) <= 1 or "Listing... Done" in lines[0] and len(lines) == 1:
            console.print(get_string("no_updates_msg"))
            return

        table = Table(title=get_string("updates_title"))
        table.add_column(get_string("package_col"), justify="left", style="cyan")
        table.add_column(get_string("version_col"), justify="left", style="magenta")

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            package_name = parts[0].split('/')[0]
            new_version = parts[1]
            table.add_row(package_name, new_version)
        
        if table.rows:
            console.print(table)
            console.print(get_string("updates_found_msg"))
        else:
            console.print(get_string("no_updates_msg"))

    except FileNotFoundError:
        console.print(get_string("apt_not_found_err"))
    except Exception as e:
        console.print(get_string("generic_err", e=e))

def _check_ssh_param(config_text, param_regex, good_values, recommendation_key):
    """A helper to check a specific parameter in sshd_config."""
    match = re.search(param_regex, config_text, re.MULTILINE | re.IGNORECASE)
    status = get_string("param_check_bad")
    
    if match:
        value = match.group(1)
        if value.lower() in good_values:
            status = get_string("param_check_ok")
    # If the parameter is commented out, it's often using a default that might be bad.
    # We treat it as info, as it's not explicitly insecure.
    elif re.search(r"^\s*#" + param_regex.lstrip(r"^\s*"), config_text, re.MULTILINE | re.IGNORECASE):
        status = get_string("param_check_info")
    
    return status, get_string(recommendation_key)

def check_ssh_config():
    """Checks for insecure SSH configurations and provides hardening advice."""
    console.print(f"\n[bold cyan]{get_string('ssh_config_option')}[/bold cyan]")
    ssh_config_path_str = get_string("ssh_config_path")
    ssh_config_path = Path(ssh_config_path_str)
    
    if not ssh_config_path.exists():
        console.print(get_string("ssh_not_found", path=ssh_config_path_str))
        return

    try:
        with open(ssh_config_path, 'r') as f:
            config = f.read()

        table = Table(title=get_string("ssh_advice_title"))
        table.add_column("Status", justify="center")
        table.add_column("Recommendation", justify="left")

        # Для сбора уязвимостей
        vulnerabilities = []
        param_names = ["PermitRootLogin", "PasswordAuthentication", "Protocol", "X11Forwarding"]
        param_keys = [
            (r"^\s*PermitRootLogin\s+(yes|no|prohibit-password)", ['no', 'prohibit-password'], "param_permit_root_login", "PermitRootLogin"),
            (r"^\s*PasswordAuthentication\s+(yes|no)", ['no'], "param_password_auth", "PasswordAuthentication"),
            (r"^\s*Protocol\s+([12,]+)", ['2'], "param_protocol_2", "Protocol"),
            (r"^\s*X11Forwarding\s+(yes|no)", ['no'], "param_x11_forwarding", "X11Forwarding"),
        ]
        for param_regex, good_values, recommendation_key, param_name in param_keys:
            status, rec = _check_ssh_param(config, param_regex, good_values, recommendation_key)
            # Явное выделение уязвимости
            if status.strip().lower() in ("[bold red]плохо[/bold red]", "[bold red]bad[/bold red]"):
                status = "[bold red]ОПАСНО[/bold red]"
                vulnerabilities.append(param_name)
            table.add_row(status, rec)

        console.print(table)

        # Если есть уязвимости — показать отдельный блок
        if vulnerabilities:
            vuln_list = "\n".join(f"- [red]{p}[/red]: {SSH_PARAM_EXPLANATIONS.get(p, '')}" for p in vulnerabilities)
            console.print(f"\n[bold red]Обнаружены критические уязвимости в настройках SSH:[/bold red]\n{vuln_list}")
        else:
            console.print("[green]Критических уязвимостей SSH не обнаружено![/green]")

        # Пояснения ко всем параметрам
        console.print("\n[bold]Пояснения к параметрам:[/bold]")
        for p, expl in SSH_PARAM_EXPLANATIONS.items():
            console.print(f"[cyan]{p}[/cyan]: {expl}")

    except PermissionError:
        console.print(get_string("ssh_permission_err", path=ssh_config_path_str))
    except Exception as e:
        console.print(get_string("ssh_read_err", e=e))

def check_for_rootkits():
    """Checks for rootkits using chkrootkit."""
    console.print(f"\n[bold cyan]{get_string('rootkit_check_option')}[/bold cyan]")
    if not _check_and_install_utility("chkrootkit", "chkrootkit"):
        return
    
    if os.geteuid() != 0:
        console.print(get_string("need_root_warning"))
        return

    try:
        console.print(get_string("running_chkrootkit"))
        result = subprocess.run(['chkrootkit'], capture_output=True, text=True, check=True)
        output = result.stdout
        # Сохраняем лог
        with open(CHKROOTKIT_LOG_PATH, 'w') as f:
            f.write(output)
        # Анализируем вывод
        infected = []
        suspicious = []
        for line in output.splitlines():
            if "INFECTED" in line or "Possible rootkit" in line:
                infected.append(line)
            elif any(w in line for w in ["suspicious", "Suspicious", "Warning"]):
                suspicious.append(line)
        if infected:
            console.print(f"[bold red]{get_string('chkrootkit_found_threats')}[/bold red]")
            for l in infected:
                console.print(f"[red]{l}[/red]")
        elif suspicious:
            console.print(f"[yellow]{get_string('chkrootkit_found_suspicious')}[/yellow]")
            for l in suspicious:
                console.print(f"[yellow]{l}[/yellow]")
        else:
            console.print(f"[green]{get_string('chkrootkit_no_threats')}[/green]")
        console.print(f"[grey]{get_string('chkrootkit_log_saved', path=CHKROOTKIT_LOG_PATH)}[/grey]")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(get_string("chkrootkit_error", e=e))

# --- Просмотр логов chkrootkit и lynis ---
def show_chkrootkit_log():
    if not os.path.exists(CHKROOTKIT_LOG_PATH):
        console.print("[yellow]Лог chkrootkit не найден.[/yellow]")
        return
    with open(CHKROOTKIT_LOG_PATH) as f:
        log = f.read()
    console.print(Panel(log, title="chkrootkit.log", border_style="grey37"))
    inquirer.text(message=get_string("press_enter_to_continue")).execute()

def show_lynis_log():
    if not os.path.exists(LYNIS_LOG_PATH):
        console.print("[yellow]Лог Lynis не найден.[/yellow]")
        return
    with open(LYNIS_LOG_PATH) as f:
        log = f.read()
    console.print(Panel(log, title="lynis.log", border_style="grey37"))
    inquirer.text(message=get_string("press_enter_to_continue")).execute()

# --- Локализация и понятный вывод для Lynis ---
LYNIS_SUGGESTION_LOCALIZED = {
    "SSH-7408": {
        "title": get_string("lynis_suggestion_SSH-7408_title"),
        "what": get_string("lynis_suggestion_SSH-7408_what"),
        "action": get_string("lynis_suggestion_SSH-7408_action"),
        "risk": get_string("lynis_suggestion_SSH-7408_risk"),
    },
    "DEB-0880": {
        "title": get_string("lynis_suggestion_DEB-0880_title"),
        "what": get_string("lynis_suggestion_DEB-0880_what"),
        "action": get_string("lynis_suggestion_DEB-0880_action"),
        "risk": get_string("lynis_suggestion_DEB-0880_risk"),
    },
    # ... добавить другие популярные ID ...
}

def run_lynis_audit():
    """Runs a comprehensive system audit using Lynis and displays a structured summary."""
    console.print(f"\n[bold cyan]{get_string('lynis_audit_option')}[/bold cyan]")
    if not _check_and_install_utility("lynis", "lynis"):
        return

    if os.geteuid() != 0:
        console.print(get_string("need_root_warning"))
        return

    report_path = Path(LYNIS_LOG_PATH)
    try:
        with console.status(get_string("running_lynis")):
            process = subprocess.run(
                ['lynis', 'audit', 'system', '--quiet', '--report-file', str(report_path)],
                capture_output=True, text=True
            )
        if process.returncode != 0 and not report_path.exists():
             console.print("[red]Lynis failed to run. Details:[/red]")
             console.print(process.stderr)
             return
        if not report_path.exists():
            console.print(f"[red]Lynis report file not found at {report_path}[/red]")
            return
        report_data = {}
        with open(report_path, 'r') as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split('=', 1)
                    if key.endswith('[]'):
                        key_name = key.rstrip('[]')
                        if key_name not in report_data:
                            report_data[key_name] = []
                        report_data[key_name].append(value)
                    else:
                        report_data[key] = value
        warnings_count = len(report_data.get('warning', []))
        suggestions_count = len(report_data.get('suggestion', []))
        summary_table = Table(title=get_string("lynis_summary_title"))
        summary_table.add_column("Metric", style="magenta")
        summary_table.add_column("Value", style="bold")
        summary_table.add_row(get_string("lynis_hardening_index"), report_data.get("hardening_index", "N/A"))
        summary_table.add_row(get_string("lynis_tests_done"), report_data.get("tests_done", "N/A"))
        summary_table.add_row(get_string("lynis_warnings"), f"[yellow]{warnings_count}[/yellow]")
        summary_table.add_row(get_string("lynis_suggestions"), f"[cyan]{suggestions_count}[/cyan]")
        summary_table.add_row(get_string("lynis_report_file"), str(report_path))
        console.print(summary_table)
        # --- Локализованный и понятный вывод предложений ---
        suggestions = report_data.get('suggestion', [])
        if suggestions:
            console.print(f"\n[bold cyan]{get_string('lynis_suggestions_title')}[/bold cyan]")
            for sug in suggestions:
                parts = sug.split('|')
                if len(parts) >= 4:
                    sug_id, details, _, action = parts[0], parts[1], parts[2], parts[3]
                    loc = LYNIS_SUGGESTION_LOCALIZED.get(sug_id)
                    if loc:
                        console.print(f"[red]{loc['title']}[/red]")
                        console.print(f"  - {get_string('lynis_what')}: {loc['what']}")
                        console.print(f"  - {get_string('lynis_action')}: {loc['action']}")
                        console.print(f"  - {get_string('lynis_risk')}: {loc['risk']}")
                    else:
                        console.print(f"[yellow]{sug_id}: {details}[/yellow]")
                        console.print(f"  - {get_string('lynis_action')}: {action}")
                        console.print(f"  - {get_string('lynis_no_localization')}")
        else:
            console.print("[green]Нет предложений по усилению безопасности![/green]")
        console.print(f"[grey]{get_string('lynis_log_saved', path=str(report_path))}[/grey]")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        console.print(get_string("lynis_error", e=e))

def run_security_analysis():
    """Displays the security analysis sub-menu and runs the selected tool."""
    if os.geteuid() != 0:
        console.print(get_string("need_root_warning"))
    while True:
        choice = inquirer.select(
            message=get_string("security_menu_prompt"),
            choices=[
                Choice(value="ports", name=get_string("port_scan_option")),
                Choice(value="ssh", name=get_string("ssh_config_option")),
                Choice(value="updates", name=get_string("system_updates_option")),
                Choice(value="rootkit", name=get_string("rootkit_check_option")),
                Choice(value="chkrootkit_log", name=get_string("chkrootkit_log_menu")),
                Choice(value="lynis", name=get_string("lynis_audit_option")),
                Choice(value="lynis_log", name=get_string("lynis_log_menu")),
                Separator(),
                Choice(value="back", name=get_string("back_to_main_menu")),
            ],
            vi_mode=True,
            pointer="» ",
            instruction=" ",
        ).execute()
        if choice == "back" or choice is None:
            break
        try:
            if choice == "ports":
                check_open_ports()
            elif choice == "ssh":
                check_ssh_config()
            elif choice == "updates":
                check_system_updates()
            elif choice == "rootkit":
                check_for_rootkits()
            elif choice == "chkrootkit_log":
                show_chkrootkit_log()
            elif choice == "lynis":
                run_lynis_audit()
            elif choice == "lynis_log":
                show_lynis_log()
            inquirer.text(message="\n" + get_string("press_enter_to_continue"), vi_mode=True).execute()
        except KeyboardInterrupt:
            console.print(f'\n{get_string("operation_cancelled")}')
            pass 