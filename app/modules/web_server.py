import os
import questionary
from rich.console import Console
import re

from app.translations import t
from app.utils import is_tool_installed, run_command, run_command_for_output, sudo_file_exists

console = Console()

def show_web_server_manager():
    """Displays the web server management menu."""
    console.clear()
    
    nginx_installed = is_tool_installed('nginx')
    apache_installed = is_tool_installed('apache2')

    web_server = None

    if nginx_installed and apache_installed:
        server_choice = questionary.select(
            t('select_web_server_to_manage'),
            choices=['Nginx', 'Apache', t('back_to_main_menu')]
        ).ask()
        if server_choice == 'Nginx':
            web_server = 'nginx'
        elif server_choice == 'Apache':
            web_server = 'apache'
        else:
            return
    elif nginx_installed:
        web_server = 'nginx'
    elif apache_installed:
        web_server = 'apache'
    else:
        console.print(f"[bold yellow]{t('no_web_server_installed')}[/bold yellow]")
        if questionary.confirm(t('install_nginx_prompt')).ask():
            # Defaulting to Nginx for installation
            try:
                console.print(f"[cyan]{t('installing_tool', tool='Nginx')}...[/cyan]")
                run_command("sudo apt-get update && sudo apt-get install -y nginx")
                console.print(f"[bold green]{t('tool_installed_successfully', tool='Nginx')}[/bold green]")
                web_server = 'nginx'
            except Exception as e:
                console.print(f"[bold red]{t('tool_installation_failed', tool='Nginx', error=e)}[/bold red]")
                questionary.press_any_key_to_continue().ask()
                return
        else:
            return
            
    if not web_server:
        return

    # Main menu loop
    while True:
        console.clear()
        title = t('web_server_manager_title_nginx') if web_server == 'nginx' else t('web_server_manager_title_apache')
        console.print(f"[bold blue underline]{title}[/bold blue underline]\n")

        menu_options = {
            t('web_server_create_site'): lambda: create_new_site(web_server),
            t('web_server_manage_sites'): lambda: manage_sites(web_server),
            t('web_server_manage_ssl'): manage_ssl,
            t('back_to_main_menu'): "exit"
        }

        choices = list(menu_options.keys())
        # Dynamically add framework-specific options
        if web_server == 'nginx':
            choices.insert(1, t('web_server_create_nextjs_site'))
            menu_options[t('web_server_create_nextjs_site')] = lambda: create_nginx_nextjs_site()
        
        choices.insert(1, t('web_server_create_php_site'))
        menu_options[t('web_server_create_php_site')] = lambda: create_php_site(web_server)
        
        choices.insert(0, t('web_server_create_from_git'))
        menu_options[t('web_server_create_from_git')] = lambda: create_site_from_git(web_server)

        action = questionary.select(
            t('web_server_menu_prompt'),
            choices=choices,
            pointer="👉"
        ).ask()

        if action is None or menu_options.get(action) == "exit":
            break

        selected_function = menu_options.get(action)
        if selected_function:
            selected_function()
            questionary.press_any_key_to_continue(t('press_any_key')).ask()

def create_new_site(web_server):
    """Guides the user through creating a new static site."""
    if web_server == 'nginx':
        create_nginx_static_site()
    elif web_server == 'apache':
        create_apache_static_site()

def create_nginx_static_site(domain_prefill=None, web_root_prefill=None):
    """Creates a new static site for Nginx."""
    console.print(f"\n[bold green]{t('create_static_site_title')}[/bold green]")

    domain = domain_prefill or questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    web_root = web_root_prefill or f"/var/www/{domain}"

    if not web_root_prefill:
        # Create directory and a placeholder file if not a git deployment
        console.print(t('creating_web_root', path=web_root))
        run_command(f"sudo mkdir -p {web_root}")
        run_command(f"echo '<h1>{domain} - {t('coming_soon') }</h1>' | sudo tee {web_root}/index.html")
        run_command(f"sudo chown -R www-data:www-data {web_root}")

    nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
    nginx_conf_content = f"""
# Web-Root: {web_root}
server {{
    listen 80;
    server_name {domain};
    root {web_root};
    index index.html index.htm;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""
    console.print(t('creating_nginx_config', path=nginx_conf_path))
    try:
        run_command(f"echo \"{nginx_conf_content}\" | sudo tee {nginx_conf_path}")
        run_command(f"sudo ln -s -f {nginx_conf_path} /etc/nginx/sites-enabled/") # -f to overwrite if it exists
        run_command("sudo nginx -t")
        run_command("sudo systemctl reload nginx")
        console.print(f"[bold green]{t('site_created_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'nginx')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")

def create_apache_static_site(domain_prefill=None, web_root_prefill=None):
    """Creates a new static site for Apache."""
    console.print(f"\n[bold green]{t('create_static_site_title')}[/bold green]")

    domain = domain_prefill or questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    web_root = web_root_prefill or f"/var/www/{domain}"
    
    if not web_root_prefill:
        console.print(t('creating_web_root', path=web_root))
        run_command(f"sudo mkdir -p {web_root}")
        run_command(f"echo '<h1>{domain} - {t('coming_soon') }</h1>' | sudo tee {web_root}/index.html")
        run_command(f"sudo chown -R www-data:www-data {web_root}")

    apache_conf_path = f"/etc/apache2/sites-available/{domain}.conf"
    apache_conf_content = f"""
<VirtualHost *:80>
    ServerAdmin webmaster@localhost
    ServerName {domain}
    DocumentRoot {web_root}
    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined
</VirtualHost>
"""
    console.print(t('creating_apache_config', path=apache_conf_path))
    try:
        run_command(f"echo \"{apache_conf_content}\" | sudo tee {apache_conf_path}")
        run_command(f"sudo a2ensite {domain}.conf")
        run_command("sudo systemctl reload apache2")
        console.print(f"[bold green]{t('site_created_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'apache')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_apache', error=e)}[/red]")

def create_site_from_git(web_server):
    """Creates a new site by cloning a Git repository."""
    console.print(f"\n[bold green]{t('create_from_git_title')}[/bold green]")

    if not is_tool_installed('git'):
        console.print(f"[bold red]{t('git_not_installed_error')}[/bold red]")
        if questionary.confirm(t('git_install_prompt')).ask():
            run_command("sudo apt-get update && sudo apt-get install -y git")
        else:
            return

    repo_url = questionary.text(t('git_repo_url_prompt')).ask()
    if not repo_url:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return

    # Sanitize the URL to remove branch/tree specifics
    if "/tree/" in repo_url:
        repo_url = repo_url.split("/tree/")[0]
        console.print(t('git_url_sanitized', default="[yellow]NOTE: Sanitized Git URL to:[/yellow] {url}", url=repo_url))

    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
    
    web_root = f"/var/www/{domain}"

    console.print(t('git_cloning_repo', url=repo_url, path=web_root))
    try:
        run_command(f"sudo git clone {repo_url} {web_root}")
        run_command(f"sudo chown -R www-data:www-data {web_root}")
        console.print(f"[green]{t('git_clone_success')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('git_clone_failed', error=e)}[/red]")
        return

    # --- Project Type Detection ---
    if sudo_file_exists(f"{web_root}/docker-compose.yml") or sudo_file_exists(f"{web_root}/Dockerfile"):
        # TODO: Implement Docker/Docker-compose deployment
        console.print("[yellow]Docker project detected. Deployment logic not yet implemented.[/yellow]")
        deploy_docker_project(domain, web_root, web_server)

    elif sudo_file_exists(f"{web_root}/package.json"):
        console.print("[yellow]Node.js project detected.[/yellow]")
        if web_server == 'nginx':
            # Slightly adapt the existing nextjs function
            create_nginx_nextjs_site(domain_prefill=domain, web_root_prefill=web_root)
        else:
            # TODO: Implement for Apache
            console.print("[red]Node.js deployment is currently only supported for Nginx.[/red]")

    elif sudo_file_exists(f"{web_root}/index.php"):
        console.print("[yellow]PHP project detected.[/yellow]")
        # We can reuse the existing PHP site creators
        if web_server == 'nginx':
            create_nginx_php_site(domain_prefill=domain, web_root_prefill=web_root)
        elif web_server == 'apache':
            create_apache_php_site(domain_prefill=domain, web_root_prefill=web_root)

    else:
        console.print("[yellow]Static site detected.[/yellow]")
        # We can reuse the existing static site creators
        if web_server == 'nginx':
            create_nginx_static_site(domain_prefill=domain, web_root_prefill=web_root)
        elif web_server == 'apache':
            create_apache_static_site(domain_prefill=domain, web_root_prefill=web_root)

def create_nginx_nextjs_site(domain_prefill=None, web_root_prefill=None):
    """Guides the user through creating and deploying a Next.js site with Nginx."""
    console.print(f"\n[bold green]{t('create_nextjs_site_title')}[/bold green]")
    
    # Step 1: Check for dependencies (node, npm, pm2)
    deps = ['node', 'npm', 'pm2']
    missing_deps = [dep for dep in deps if not is_tool_installed(dep)]
    
    if missing_deps:
        console.print(f"[bold yellow]{t('missing_dependencies_nextjs', deps=', '.join(missing_deps))}[/bold yellow]")
        # Here you could add logic to guide the user to install them, possibly via dev_tools
        if 'pm2' in missing_deps and questionary.confirm(t('pm2_install_prompt')).ask():
            run_command("sudo npm install pm2 -g")
        else:
            questionary.press_any_key_to_continue(t('please_install_and_retry')).ask()
            return

    # Step 2: Get project details
    project_name = None
    if web_root_prefill:
        project_name = os.path.basename(web_root_prefill)
    else:
        project_name = questionary.text(t('enter_project_name_nextjs')).ask()

    if not project_name:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    domain = domain_prefill or questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    # Find an available port, starting from 3000
    port = 3000
    while True:
        output = run_command(f"sudo lsof -i:{port}")
        if not output:
            break
        port += 1

    web_root = web_root_prefill or f"/var/www/{project_name}"

    # Step 3: Create Next.js app (if not from git) and set permissions
    if not web_root_prefill:
        console.print(f"[cyan]{t('creating_nextjs_app', path=web_root)}[/cyan]")
        
        # Get the original user who invoked sudo
        invoking_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'www-data'))

        # Create directory and chown to the invoking user so npx can write to it
        if not run_command(f"sudo mkdir -p {web_root}"):
            return
        if not run_command(f"sudo chown -R {invoking_user}:{invoking_user} {web_root}"):
            return

        # Create the Next.js app with live output
        # Running npx as the invoking user to avoid permission issues and running as root.
        console.print(f"[yellow]{t('running_create_next_app', default='Running create-next-app, this may take a moment...')}[/yellow]")
        create_command = f"sudo -u {invoking_user} npx --yes create-next-app@latest {web_root} --ts --eslint --tailwind --app --src-dir --import-alias '@/*' --use-npm"
        
        if not run_command(create_command, show_output=True):
             console.print(f"[red]{t('error_creating_nextjs_app', default='Failed to create Next.js application.')}[/red]")
             # Offer to clean up the directory
             if sudo_file_exists(f"{web_root}/package.json") and questionary.confirm(t('confirm_delete_web_root_on_fail', default='Do you want to delete the partially created directory {path}?', path=web_root)).ask():
                 run_command(f"sudo rm -rf {web_root}")
             return

        console.print(f"[green]{t('nextjs_app_created_successfully')}[/green]")

    # Change ownership to www-data before installing dependencies and running the app
    if not run_command(f"sudo chown -R www-data:www-data {web_root}"):
        return

    # Step 4: Build and start with PM2 as www-data user
    try:
        console.print(f"[cyan]{t('building_nextjs_app')}[/cyan]")
        run_command(f"sudo -u www-data bash -c 'cd {web_root} && npm install && npm run build'")
        
        console.print(f"[cyan]{t('starting_app_with_pm2')}[/cyan]")
        run_command(f"sudo -u www-data bash -c \"cd {web_root} && PORT={port} pm2 start npm --name '{project_name}' -- start\"")
        run_command("sudo -u www-data pm2 save")
        
    except Exception as e:
        console.print(f"[red]{t('error_building_or_starting_app', error=e)}[/red]")
        return

    # Step 5: Create Nginx config for reverse proxy
    nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
    nginx_conf_content = f"""
# Project-Name: {project_name}
# Web-Root: {web_root}
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://localhost:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
    console.print(t('creating_nginx_config', path=nginx_conf_path))
    try:
        # Using tee to write with sudo
        run_command(f"echo \"{nginx_conf_content}\" | sudo tee {nginx_conf_path}")
        # Enable the site
        run_command(f"sudo ln -s -f {nginx_conf_path} /etc/nginx/sites-enabled/") # Use -f to overwrite
        run_command("sudo nginx -t")
        run_command("sudo systemctl reload nginx")
        console.print(f"[bold green]{t('nginx_config_created')}[/green]")
        ask_and_install_ssl(domain, 'nginx')
    except Exception as e:
        console.print(f"[red]{t('error_creating_nginx_config', error=e)}[/red]")
        # Add cleanup logic here if needed
        return
        
    # Step 6: Test and reload Nginx
    console.print(t('testing_nginx_config'))
    try:
        run_command("sudo nginx -t")
        console.print(t('reloading_nginx'))
        run_command("sudo systemctl reload nginx")
        console.print(f"[bold green]{t('nextjs_site_deployed_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'nginx')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")

def create_apache_nextjs_site():
    """Guides the user through creating and deploying a Next.js site with Apache."""
    # This is more complex due to needing mod_proxy enabled.
    # For now, let's provide a message that it's coming soon.
    console.print(f"\n[bold yellow]{t('feature_coming_soon', feature='Apache + Next.js')}[/bold yellow]")
    return

def find_php_fpm_socket():
    """Finds the active PHP-FPM socket path."""
    try:
        # This command looks for listening unix sockets managed by systemd for php
        output = run_command_for_output("find /var/run/php/ -name '*-fpm.sock' -type s")
        sockets = output.strip().split('\\n')
        if not sockets or not sockets[0]:
            return None
        # If multiple sockets, let user choose? For now, pick the first one.
        # Often it's something like /var/run/php/php8.2-fpm.sock
        return sockets[0]
    except Exception:
        return None

def create_nginx_php_site(domain_prefill=None, web_root_prefill=None):
    """Guides the user through creating a new Nginx site for PHP."""
    console.print(f"\n[bold green]{t('create_php_site_title')}[/bold green]")
    
    # Step 1: Check for dependencies (nginx is already checked, check for php-fpm)
    php_fpm_socket = find_php_fpm_socket()

    if not is_tool_installed('php') or not php_fpm_socket:
        console.print(f"[bold yellow]{t('php_fpm_not_installed')}[/bold yellow]")
        if questionary.confirm(t('install_php_fpm_prompt')).ask():
            try:
                console.print(f"[cyan]{t('installing_tool', tool='PHP-FPM')}...[/cyan]")
                # Installs a default version of PHP and FPM
                run_command("sudo apt-get update && sudo apt-get install -y php-fpm")
                php_fpm_socket = find_php_fpm_socket()
                if not php_fpm_socket:
                    console.print(f"[bold red]{t('php_fpm_socket_not_found_after_install')}[/bold red]")
                    return
                console.print(f"[bold green]{t('tool_installed_successfully', tool='PHP-FPM')}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]{t('tool_installation_failed', tool='PHP-FPM', error=e)}[/bold red]")
                return
        else:
            return # User chose not to install

    # Step 2: Get domain
    domain = domain_prefill or questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    web_root = web_root_prefill or f"/var/www/{domain}"
    
    # Step 3: Create web root and index.php
    console.print(t('creating_web_root', path=web_root))
    try:
        run_command(f"sudo mkdir -p {web_root}")
        # Create a simple phpinfo file
        php_info_content = "<?php phpinfo(); ?>"
        run_command(f"echo '{php_info_content}' | sudo tee {web_root}/index.php")
        run_command(f"sudo chown -R www-data:www-data {web_root}")
        console.print(f"[green]{t('directory_created_successfully')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_directory', error=e)}[/red]")
        return

    # Step 4: Create Nginx config
    nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
    nginx_conf_content = f"""
# Web-Root: {web_root}
server {{
    listen 80;
    server_name {domain};
    root {web_root};

    index index.php index.html index.htm;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:{php_fpm_socket};
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
"""
    console.print(t('creating_nginx_config', path=nginx_conf_path))
    try:
        run_command(f'echo "{nginx_conf_content}" | sudo tee {nginx_conf_path}')
        run_command(f"sudo ln -s -f {nginx_conf_path} /etc/nginx/sites-enabled/")
        console.print(f"[green]{t('nginx_config_created')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_nginx_config', error=e)}[/red]")
        return
        
    # Step 5: Test and reload Nginx
    console.print(t('testing_nginx_config'))
    try:
        run_command("sudo nginx -t")
        console.print(t('reloading_nginx'))
        run_command("sudo systemctl reload nginx")
        console.print(f"[bold green]{t('php_site_created_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'nginx')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")
        if questionary.confirm(t('nginx_reload_failed_cleanup_prompt')).ask():
             run_command(f"sudo rm {nginx_conf_path}")
             run_command(f"sudo rm /etc/nginx/sites-enabled/{domain}")
             if not web_root_prefill:
                 run_command(f"sudo rm -rf {web_root}")
             console.print(t('cleanup_complete')) 

def create_apache_php_site(domain_prefill=None, web_root_prefill=None):
    """Guides the user through creating a new Apache site for PHP."""
    console.print(f"\n[bold green]{t('create_php_site_title')}[/bold green]")
    php_fpm_socket = find_php_fpm_socket()
    if not is_tool_installed('php') or not php_fpm_socket:
        # Same dependency check as nginx
        console.print(f"[bold yellow]{t('php_fpm_not_installed')}[/bold yellow]")
        # Offer to install, etc.
        return # Simplified for now

    # Check for required apache mods
    try:
        run_command_for_output("sudo a2query -m proxy_fcgi")
    except Exception:
        console.print(f"[yellow]{t('enabling_apache_mod', mod='proxy_fcgi')}...[/yellow]")
        run_command("sudo a2enmod proxy_fcgi setenvif")
        # May need a restart
        run_command("sudo systemctl restart apache2")

    domain = domain_prefill or questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
    web_root = web_root_prefill or f"/var/www/{domain}"
    try:
        run_command(f"sudo mkdir -p {web_root}")
        php_info_content = "<?php phpinfo(); ?>"
        run_command(f"echo '{php_info_content}' | sudo tee {web_root}/index.php")
        run_command(f"sudo chown -R www-data:www-data {web_root}")
        console.print(f"[green]{t('directory_created_successfully')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_directory', error=e)}[/red]")
        return
        
    apache_conf_path = f"/etc/apache2/sites-available/{domain}.conf"
    apache_conf_content = f"""
# Web-Root: {web_root}
<VirtualHost *:80>
    ServerName {domain}
    DocumentRoot {web_root}
    
    <Directory {web_root}>
        AllowOverride All
    </Directory>

    <FilesMatch \\.php$>
        SetHandler "proxy:unix:{php_fpm_socket}|fcgi://localhost/"
    </FilesMatch>
    
    ErrorLog ${{APACHE_LOG_DIR}}/error.log
    CustomLog ${{APACHE_LOG_DIR}}/access.log combined
</VirtualHost>
"""
    console.print(t('creating_apache_config', path=apache_conf_path))
    try:
        run_command(f'echo "{apache_conf_content}" | sudo tee {apache_conf_path}')
        run_command(f"sudo a2ensite {domain}.conf")
        console.print(f"[green]{t('apache_config_created')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_apache_config', error=e)}[/red]")
        return

    console.print(t('reloading_apache'))
    try:
        run_command("sudo systemctl reload apache2")
        console.print(f"[bold green]{t('php_site_created_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'apache')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_apache', error=e)}[/red]")

def ask_and_install_ssl(domain, web_server):
    """Asks the user if they want to install an SSL cert and does it."""
    if questionary.confirm(t('ask_install_ssl', domain=domain)).ask():
        if not is_tool_installed('certbot'):
            console.print(f"[yellow]{t('certbot_not_installed')}[/yellow]")
            if questionary.confirm(t('install_certbot_prompt')).ask():
                try:
                    console.print(f"[cyan]{t('installing_tool', tool='Certbot')}...[/cyan]")
                    run_command("sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx")
                    console.print(f"[bold green]{t('tool_installed_successfully', tool='Certbot')}[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]{t('tool_installation_failed', tool='Certbot', error=e)}[/bold red]")
                    return
            else:
                return # User chose not to install
        
        # Now run certbot
        console.print(f"[cyan]{t('running_certbot', domain=domain)}[/cyan]")
        try:
            # --non-interactive: run without user interaction
            # --agree-tos: agree to terms of service
            # --email: for urgent renewal and security notices
            # --nginx: use the nginx plugin to configure nginx
            # -d: domain name
            # --redirect: automatically redirect http to https
            email = questionary.text(t('enter_email_for_ssl')).ask()
            if not email:
                console.print(f"[red]{t('operation_cancelled')}[/red]")
                return

            command = f"sudo certbot --{web_server} -d {domain} --non-interactive --agree-tos --email {email} --redirect"
            run_command(command)
            console.print(f"[bold green]{t('ssl_installed_successfully', domain=domain)}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]{t('ssl_installation_failed', error=e)}[/bold red]")

def manage_ssl():
    """Provides SSL management options."""
    console.clear()
    console.print(f"[bold blue underline]{t('ssl_manager_title')}[/bold blue underline]\n")

    if not is_tool_installed('certbot'):
        console.print(f"[bold yellow]{t('certbot_required_for_ssl')}[/bold yellow]")
        questionary.press_any_key_to_continue().ask()
        return

    menu_options = {
        t('ssl_menu_list'): "list",
        t('ssl_menu_renew'): "renew",
        t('back_to_main_menu'): "exit"
    }
    
    action = questionary.select(
        t('ssl_menu_prompt'),
        choices=list(menu_options.keys())
    ).ask()

    if action is None or menu_options.get(action) == "exit":
        return

    command = menu_options.get(action)

    if command == "list":
        console.print(f"[cyan]{t('listing_certificates')}...[/cyan]")
        run_command("sudo certbot certificates")
    elif command == "renew":
        console.print(f"[cyan]{t('renewing_certificates')}...[/cyan]")
        run_command("sudo certbot renew --dry-run") # Use dry-run for safety 

def manage_sites(web_server):
    """Lists sites and provides management options like deletion."""
    console.clear()
    console.print(f"[bold blue underline]{t('manage_sites_title')}[/bold blue underline]\n")

    sites = []
    site_dir = "/etc/nginx/sites-enabled" if web_server == 'nginx' else "/etc/apache2/sites-enabled"
    
    try:
        sites = [site for site in os.listdir(site_dir) if site != 'default']
    except FileNotFoundError:
        console.print(f"[red]{t('error_listing_sites_dir_not_found', dir=site_dir)}[/red]")
        return
        
    if not sites:
        console.print(f"[yellow]{t('no_sites_found')}[/yellow]")
        return

    sites.append(t('back'))
    selected_site = questionary.select(t('select_site_to_manage'), choices=sites).ask()

    if selected_site is None or selected_site == t('back'):
        return

    # Now show options for the selected site
    action = questionary.select(
        t('what_to_do_with_site', site=selected_site),
        choices=[t('delete_site'), t('back')]
    ).ask()
    
    if action == t('delete_site'):
        delete_site(selected_site, web_server)

def delete_site(site_conf_name, web_server):
    """Deletes a website, including its web root and associated processes like PM2."""
    domain = site_conf_name.replace('.conf', '') if '.conf' in site_conf_name else site_conf_name
    
    if not questionary.confirm(t('confirm_delete_site', site=domain)).ask():
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    console.print(f"[cyan]{t('deleting_site', site=domain)}...[/cyan]")

    try:
        conf_path = f"/etc/{web_server}/{'sites-available'}/{site_conf_name}"
        
        # --- Read config to get metadata ---
        project_name = None
        doc_root = None
        try:
            with open(conf_path, 'r') as f:
                content = f.read()
                name_match = re.search(r'#\s*Project-Name:\s*(.+)', content)
                root_match = re.search(r'#\s*Web-Root:\s*(.+)', content)
                if name_match:
                    project_name = name_match.group(1).strip()
                if root_match:
                    doc_root = root_match.group(1).strip()
        except Exception as e:
            console.print(f"[yellow]{t('warning_could_not_read_config', path=conf_path, error=e)}[/yellow]")
        
        # --- Stop and delete PM2 process if it exists ---
        if project_name and is_tool_installed('pm2'):
            console.print(t('deleting_pm2_process', name=project_name))
            # Run as the user that owns the process, likely www-data
            # Use suppress_errors=True to prevent script from crashing if process not found
            run_command(f"sudo -u www-data pm2 delete {project_name}", suppress_errors=True)
            run_command("sudo -u www-data pm2 save", suppress_errors=True)


        # --- Disable and Remove Site ---
        if web_server == 'nginx':
            run_command(f"sudo rm -f /etc/nginx/sites-enabled/{site_conf_name}")
        else: # apache
            run_command(f"sudo a2dissite {site_conf_name}")
        
        run_command(f"sudo rm -f {conf_path}")
        console.print(f"[green]{t('site_disabled_and_config_removed')}[/green]")
        
        # --- Fallback for doc_root if not in config ---
        if not doc_root:
            # For Next.js projects, the project name is the folder. For others, it's the domain.
            # This is a bit of a guess for older sites.
            potential_nextjs_root = f"/var/www/{project_name}"
            potential_generic_root = f"/var/www/{domain}"
            if project_name and sudo_file_exists(potential_nextjs_root):
                doc_root = potential_nextjs_root
            elif sudo_file_exists(potential_generic_root):
                doc_root = potential_generic_root


        # --- Remove web root ---
        if doc_root and sudo_file_exists(doc_root):
            if questionary.confirm(t('confirm_delete_web_root', path=doc_root)).ask():
                run_command(f"sudo rm -rf {doc_root}")
                console.print(f"[green]{t('web_root_deleted')}[/green]")
        else:
            console.print(f"[yellow]{t('web_root_not_found_or_not_specified')}[/yellow]")


        # --- Revoke SSL ---
        if is_tool_installed('certbot'):
            if questionary.confirm(t('confirm_revoke_ssl', domain=domain)).ask():
                # Use --non-interactive to avoid prompts and suppress_errors to continue if cert not found
                run_command(f"sudo certbot delete --cert-name {domain} --non-interactive", suppress_errors=True)
                console.print(f"[green]{t('ssl_revoked')}[/green]")

        # --- Reload web server ---
        reload_cmd = "sudo systemctl reload nginx" if web_server == 'nginx' else "sudo systemctl reload apache2"
        run_command(reload_cmd)
        
        console.print(f"[bold green]{t('site_deleted_successfully', site=domain)}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]{t('error_deleting_site', error=e)}[/bold red]") 

def deploy_docker_project(domain, web_root, web_server):
    """Deploys a Docker-based project."""
    console.print(f"\n[bold green]{t('deploy_docker_title')}[/bold green]")

    # Check for docker and docker-compose
    if not is_tool_installed('docker'):
        console.print(f"[bold red]{t('dependency_not_found', tool='Docker')}[/bold red]")
        return
    
    use_compose = sudo_file_exists(f"{web_root}/docker-compose.yml")
    if use_compose and not is_tool_installed('docker-compose'):
        console.print(f"[bold red]{t('dependency_not_found', tool='docker-compose')}[/bold red]")
        return

    try:
        if use_compose:
            console.print(t('docker_compose_building'))
            run_command(f"cd {web_root} && sudo docker-compose up -d --build")
        else: # Plain Dockerfile
            console.print(t('docker_building_image'))
            image_name = domain.lower().replace('.', '-')
            run_command(f"sudo docker build -t {image_name} .", cwd=web_root)
            # We need to know the internal port to map it. Let's ask.
            internal_port = questionary.text(t('docker_ask_internal_port')).ask()
            if not internal_port: return
            
            external_port = 8000
            while True:
                output = run_command(f"sudo lsof -i:{external_port}")
                if not output: break
                external_port += 1
                
            console.print(t('docker_running_container', image=image_name, port=f"{external_port}:{internal_port}"))
            run_command(f"sudo docker run -d -p {external_port}:{internal_port} --restart always --name {image_name} {image_name}")

        console.print(f"[green]{t('docker_deploy_success')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('docker_deploy_failed', error=e)}[/red]")
        return
        
    # --- Configure Reverse Proxy ---
    # After deployment, we need to know the port to proxy to.
    # For compose, it might be defined. For Dockerfile, we just asked.
    # Let's just ask for simplicity for now.
    proxy_port = questionary.text(t('docker_ask_proxy_port')).ask()
    if not proxy_port: return

    if web_server == 'nginx':
        nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
        nginx_conf_content = f"""
# Web-Root: {web_root}
server {{
    listen 80;
    server_name {domain};
    location / {{
        proxy_pass http://localhost:{proxy_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
        console.print(t('creating_nginx_config', path=nginx_conf_path))
        try:
            run_command(f"echo \"{nginx_conf_content}\" | sudo tee {nginx_conf_path}")
            run_command(f"sudo ln -s {nginx_conf_path} /etc/nginx/sites-enabled/")
            run_command("sudo nginx -t")
            run_command("sudo systemctl reload nginx")
            console.print(f"[bold green]{t('site_created_successfully', domain=domain)}[/bold green]")
            ask_and_install_ssl(domain, web_server)
        except Exception as e:
            console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")

    else: # Apache
        # TODO: Implement Apache reverse proxy for Docker
        console.print("[red]Apache reverse proxy for Docker is not yet implemented.[/red]")

def create_php_site(web_server):
    """Guides the user through creating a new PHP site."""
    if web_server == 'nginx':
        create_nginx_php_site()
    elif web_server == 'apache':
        create_apache_php_site()

def find_php_fpm_socket():
    """Finds the PHP-FPM socket file."""
    possible_paths = [
        "/var/run/php/",
        "/run/php/"
    ]
    for path in possible_paths:
        if sudo_file_exists(path):
            # Find any listening socket in the directory
            for f in os.listdir(path):
                if f.startswith('php') and f.endswith('-fpm.sock'):
                    return os.path.join(path, f)
    # Fallback to a common default if not found
    return "/var/run/php/php-fpm.sock"