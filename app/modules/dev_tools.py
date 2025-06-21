import os
import subprocess
import time
import questionary
from rich.console import Console
from rich.panel import Panel
from app.utils import run_command, run_command_live
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

def install_phpmyadmin():
    """A guided installer for PHPMyAdmin for Nginx."""
    console.print(Panel(f"[bold magenta]{t('pma_installer_title')}[/bold magenta]"))

    # 1. Check dependencies
    nginx_ok = bool(run_command("which nginx"))
    php_fpm_ok = bool(run_command("which php-fpm"))
    
    if not (nginx_ok and php_fpm_ok):
        console.print(f"[bold red]{t('pma_error_deps_met')}[/bold red]")
        if not nginx_ok:
            console.print(t('pma_error_no_nginx'))
        if not php_fpm_ok:
            console.print(t('pma_error_no_php'))
        console.print(f"\n{t('pma_error_deps_instructions')}")
        questionary.press_any_key_to_continue().ask()
        return

    # 2. Confirm installation
    if not questionary.confirm(t('pma_prompt_confirm_install')).ask():
        return

    # 3. Install packages
    php_deps = "php-fpm php-mysql php-mbstring php-zip php-gd php-json php-curl"
    console.print(f"[yellow]{t('pma_installing', php_deps=php_deps)}[/yellow]")
    run_command_live(f"sudo apt-get update -qq && sudo apt-get install -y phpmyadmin {php_deps}", "pma_install.log")

    # 4. Post-install instructions
    pma_path = "/usr/share/phpmyadmin"
    web_root = "/var/www/html"
    symlink_path = f"{web_root}/phpmyadmin"

    console.print(f"\n[green]{t('pma_install_finished')}[/green]")
    console.print(t('pma_info_configure_nginx'))
    
    # Create symlink
    if not os.path.exists(symlink_path):
        symlink_command = f"sudo ln -s {pma_path} {symlink_path}"
        console.print(f"\n{t('pma_info_creating_symlink', pma_path=pma_path, symlink_path=symlink_path)}")
        run_command(symlink_command)

    console.print(f"\n[bold yellow]{t('pma_info_action_required')}[/bold yellow]")
    nginx_config_snippet = f"""
    location /phpmyadmin {{
        root {web_root};
        index index.php index.html index.htm;
        
        location ~ ^/phpmyadmin(.+\\.php)$ {{
            try_files $uri =404;
            root {web_root};
            fastcgi_pass unix:/run/php/php-fpm.sock; # Verify your PHP-FPM socket path!
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
            include fastcgi_params;
        }}
        
        location ~* ^/phpmyadmin(.+\\.(jpg|jpeg|gif|css|png|js|ico|html|xml|txt))$ {{
            root {web_root};
        }}
    }}
    """
    console.print(Panel(nginx_config_snippet, title=t('pma_nginx_config_title'), border_style="magenta"))
    console.print(t('pma_info_reload_nginx'))
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
                t('devtools_menu_phpmyadmin'),
                t('devtools_menu_back')
            ]
        ).ask()

        if choice == t('devtools_menu_back') or choice is None:
            break
        elif choice == t('devtools_menu_java'):
            install_java()
        elif choice == t('devtools_menu_phpmyadmin'):
            install_phpmyadmin() 