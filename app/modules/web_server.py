import os
import questionary
from rich.console import Console

from app.translations import t
from app.utils import is_tool_installed, run_command

console = Console()

def show_web_server_manager():
    """Displays the web server management menu."""
    console.clear()
    
    # First, check for Nginx, as it's our primary target
    if not is_tool_installed('nginx'):
        console.print(f"[bold yellow]{t('nginx_not_installed')}[/bold yellow]")
        if questionary.confirm(t('install_nginx_prompt')).ask():
            try:
                # Attempt to install nginx
                console.print(f"[cyan]{t('installing_tool', tool='Nginx')}...[/cyan]")
                run_command("sudo apt-get update && sudo apt-get install -y nginx")
                console.print(f"[bold green]{t('tool_installed_successfully', tool='Nginx')}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]{t('tool_installation_failed', tool='Nginx', error=e)}[/bold red]")
                questionary.press_any_key_to_continue().ask()
                return
        else:
            return # User chose not to install

    # Main menu loop
    while True:
        console.clear()
        console.print(f"[bold blue underline]{t('web_server_manager_title')}[/bold blue underline]\n")

        menu_options = {
            t('web_server_create_site'): create_new_site,
            t('back_to_main_menu'): "exit"
        }

        action = questionary.select(
            t('web_server_menu_prompt'),
            choices=list(menu_options.keys()),
            pointer="👉"
        ).ask()

        if action is None or menu_options.get(action) == "exit":
            break

        selected_function = menu_options.get(action)
        if selected_function:
            selected_function()
            questionary.press_any_key_to_continue(t('press_any_key')).ask()

def create_new_site():
    """Guides the user through creating a new Nginx site."""
    console.print(f"\n[bold green]{t('create_new_site_title')}[/bold green]")
    
    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    web_root = f"/var/www/{domain}"
    
    console.print(t('creating_web_root', path=web_root))
    try:
        run_command(f"sudo mkdir -p {web_root}")
        # Create a simple index file
        run_command(f"echo '<h1>Welcome to {domain}</h1>' | sudo tee {web_root}/index.html")
        # Set permissions
        run_command(f"sudo chown -R www-data:www-data {web_root}")
        console.print(f"[green]{t('directory_created_successfully')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_directory', error=e)}[/red]")
        return

    # Create Nginx config
    nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
    nginx_conf_content = f"""
server {{
    listen 80;
    server_name {domain};
    root {web_root};
    index index.html;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""
    console.print(t('creating_nginx_config', path=nginx_conf_path))
    try:
        # Using tee to write with sudo
        run_command(f"echo \"{nginx_conf_content}\" | sudo tee {nginx_conf_path}")
        # Enable the site
        run_command(f"sudo ln -s {nginx_conf_path} /etc/nginx/sites-enabled/")
        console.print(f"[green]{t('nginx_config_created')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_nginx_config', error=e)}[/red]")
        return
        
    # Test and reload Nginx
    console.print(t('testing_nginx_config'))
    try:
        run_command("sudo nginx -t")
        console.print(t('reloading_nginx'))
        run_command("sudo systemctl reload nginx")
        console.print(f"[bold green]{t('site_created_successfully', domain=domain)}[/bold green]")
    except Exception as e:
        console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")
        # Offer to clean up
        if questionary.confirm(t('nginx_reload_failed_cleanup_prompt')).ask():
             run_command(f"sudo rm {nginx_conf_path}")
             run_command(f"sudo rm /etc/nginx/sites-enabled/{domain}")
             run_command(f"sudo rm -rf {web_root}")
             console.print(t('cleanup_complete')) 