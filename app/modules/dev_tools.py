import os
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, run_command_live
from app.translations import t

console = Console()
NVM_DIR = os.path.expanduser("~/.nvm")
NVM_SCRIPT = os.path.join(NVM_DIR, "nvm.sh")

def nvm_command(command):
    """Executes a command using nvm."""
    if not os.path.exists(NVM_SCRIPT):
        console.print(f"[red]{t('nvm_not_installed')}[/red]")
        return
    full_command = f"bash -c 'source {NVM_SCRIPT} && {command}'"
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
                nvm_command(f"nvm install {version}")
        elif action == t('nodejs_list_versions'):
            nvm_command("nvm ls")
        elif action == t('pm2_install_update'):
            nvm_command("npm install pm2@latest -g")
        
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
                t('devtools_menu_java'),
                t('devtools_menu_back')
            ]
        ).ask()

        if choice == t('devtools_menu_back') or choice is None:
            break
        elif choice == t('devtools_menu_nodejs'):
            manage_nodejs()
        elif choice == t('devtools_menu_java'):
            install_java() 