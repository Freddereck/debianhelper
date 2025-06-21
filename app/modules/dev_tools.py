import os
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, run_command_live
from app.translations import t

console = Console()

# --- User & Environment Detection ---
original_user = os.environ.get('SUDO_USER')
home_dir = os.path.expanduser(f'~{original_user}') if original_user else os.path.expanduser('~')
NVM_DIR = os.path.join(home_dir, ".nvm")
NVM_SCRIPT = os.path.join(NVM_DIR, "nvm.sh")
PYENV_ROOT = os.path.join(home_dir, ".pyenv")
PYENV_SCRIPT = os.path.join(PYENV_ROOT, "bin", "pyenv")

# --- NVM Functions ---
def nvm_command(command, live=False):
    """Executes a command using nvm."""
    if not os.path.exists(NVM_SCRIPT):
        console.print(f"[red]{t('nvm_not_installed')}[/red]")
        return
    full_command = f"bash -c 'source {NVM_SCRIPT} && {command}'"
    
    if live:
        run_command_live(full_command, "nvm_live.log")
    else:
        run_command(full_command)

def manage_nodejs():
    """Menu for managing Node.js and PM2 via nvm."""
    while True:
        console.clear()
        console.print(Panel(f"Node.js & PM2 {t('management')}", border_style="green"))

        if not os.path.exists(NVM_SCRIPT):
            action = questionary.select(t('nvm_not_found_prompt'), choices=[t('nvm_install'), t('back')]).ask()
            if action == t('nvm_install'):
                install_cmd = "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash"
                console.print(f"[yellow]{t('nvm_installing')}...[/yellow]")
                os.system(install_cmd)
                console.print(f"\n[green]{t('nvm_install_finished')}[/green]")
                console.print(t('nvm_restart_prompt'))
                questionary.press_any_key_to_continue().ask()
                continue
            elif action == t('back') or action is None:
                break
        
        choices = [
            t('nodejs_install_version'),
            t('nodejs_list_versions'),
            t('pm2_install_update'),
            t('back')
        ]
        action = questionary.select(t('what_to_do'), choices=choices).ask()

        if action == t('back') or action is None:
            break
        
        console.clear()
        if action == t('nodejs_install_version'):
            version = questionary.text(t('nodejs_prompt_version')).ask()
            if version:
                nvm_command(f"nvm install {version}", live=True)
        elif action == t('nodejs_list_versions'):
            nvm_command("nvm ls")
        elif action == t('pm2_install_update'):
            nvm_command("npm install pm2@latest -g", live=True)
        
        if action != t('back'):
            questionary.press_any_key_to_continue().ask()

# --- Pyenv Functions ---
def manage_python():
    """Menu for managing Python versions via pyenv."""
    while True:
        console.clear()
        console.print(Panel(f"Python {t('management')}", border_style="blue"))

        if not os.path.exists(PYENV_SCRIPT):
            action = questionary.select(t('pyenv_not_found_prompt'), choices=[t('pyenv_install'), t('back')]).ask()
            if action == t('pyenv_install'):
                console.print(f"[yellow]{t('pyenv_installing')}...[/yellow]")
                # Install dependencies first
                deps_cmd = "sudo apt-get update -qq && sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl"
                run_command_live(deps_cmd, "pyenv_deps_install.log")
                # Install pyenv
                install_cmd = f"curl https://pyenv.run | bash"
                # Running as the original user is crucial
                if original_user:
                    os.system(f"sudo -u {original_user} {install_cmd}")
                else:
                    os.system(install_cmd)
                console.print(f"\n[green]{t('pyenv_install_finished')}[/green]")
                console.print(t('pyenv_restart_prompt'))
                questionary.press_any_key_to_continue().ask()
                continue
            elif action == t('back') or action is None:
                break
        
        choices = [t('python_install_version'), t('python_list_versions'), t('back')]
        action = questionary.select(t('what_to_do'), choices=choices).ask()

        if action == t('back') or action is None: break
        
        console.clear()
        if action == t('python_install_version'):
            version = questionary.text(t('python_prompt_version')).ask()
            if version:
                console.print(f"[yellow]{t('python_installing_version', version=version)}[/yellow]")
                console.print(t('python_install_warning'))
                pyenv_command = f"pyenv install {version}"
                if original_user:
                    os.system(f"sudo -u {original_user} bash -c 'export PYENV_ROOT=\"$HOME/.pyenv\" && export PATH=\"$PYENV_ROOT/bin:$PATH\" && eval \"$(pyenv init --path)\" && {pyenv_command}'")
                else:
                    os.system(f"bash -c 'export PYENV_ROOT=\"$HOME/.pyenv\" && export PATH=\"$PYENV_ROOT/bin:$PATH\" && eval \"$(pyenv init --path)\" && {pyenv_command}'")
        elif action == t('python_list_versions'):
            pyenv_command = "pyenv versions"
            if original_user:
                 os.system(f"sudo -u {original_user} bash -c 'export PYENV_ROOT=\"$HOME/.pyenv\" && export PATH=\"$PYENV_ROOT/bin:$PATH\" && eval \"$(pyenv init --path)\" && {pyenv_command}'")
            else:
                 os.system(f"bash -c 'export PYENV_ROOT=\"$HOME/.pyenv\" && export PATH=\"$PYENV_ROOT/bin:$PATH\" && eval \"$(pyenv init --path)\" && {pyenv_command}'")
        
        if action != t('back'):
            questionary.press_any_key_to_continue().ask()

def install_java():
    """Handles installation of different Java versions."""
    console.print(Panel(f"[bold cyan]{t('java_installer_title')}[/bold cyan]"))
    
    versions = {
        "OpenJDK 11 (LTS)": "openjdk-11-jdk",
        "OpenJDK 17 (LTS)": "openjdk-17-jdk",
        "OpenJDK 21 (Latest LTS)": "openjdk-21-jdk",
        t('java_menu_cancel'): None
    }
    
    choice = questionary.select(t('java_prompt_which_version'), choices=list(versions.keys())).ask()
    
    package = versions.get(choice)
    if not package:
        return

    console.print(f"[yellow]{t('java_installing', choice=choice)}...[/yellow]")
    run_command_live(f"sudo apt-get update -qq && sudo apt-get install -y {package}", f"java_install.log")
    
    console.print(f"\n[green]{t('java_install_finished', choice=choice)}[/green]")
    console.print(t('java_manage_version_info'))
    console.print("[bold cyan]sudo update-alternatives --config java[/bold cyan]")
    questionary.press_any_key_to_continue().ask()

def show_dev_manager():
    """Main menu for developer tools."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('devtools_title')}[/bold blue]"))
        
        choice = questionary.select(
            t('devtools_prompt_select'),
            choices=[
                t('devtools_menu_nodejs'),
                t('devtools_menu_python'),
                t('devtools_menu_java'),
                t('devtools_menu_back')
            ]
        ).ask()

        if choice == t('devtools_menu_back') or choice is None: break
        elif choice == t('devtools_menu_nodejs'): manage_nodejs()
        elif choice == t('devtools_menu_python'): manage_python()
        elif choice == t('devtools_menu_java'): install_java() 