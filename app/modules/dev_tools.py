import os
import subprocess
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, run_command_live, is_tool_installed
from app.translations import t

console = Console()

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
                t('devtools_menu_java'),
                t('devtools_menu_back')
            ]
        ).ask()

        if choice == t('devtools_menu_back') or choice is None:
            break
        elif choice == t('devtools_menu_java'):
            install_java() 