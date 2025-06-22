import os
import questionary
from rich.console import Console

from app.translations import t
from app.utils import is_tool_installed, run_command, run_command_for_output

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
            t('web_server_create_nextjs_site'): lambda: create_nextjs_site(web_server),
            t('web_server_create_php_site'): lambda: create_php_site(web_server),
            t('web_server_manage_ssl'): manage_ssl,
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

def create_new_site(web_server):
    """Guides the user through creating a new static site."""
    if web_server == 'nginx':
        create_nginx_static_site()
    elif web_server == 'apache':
        create_apache_static_site()

def create_nextjs_site(web_server):
    """Guides the user through creating a new Next.js site."""
    if web_server == 'nginx':
        create_nginx_nextjs_site()
    elif web_server == 'apache':
        create_apache_nextjs_site()
        
def create_php_site(web_server):
    """Guides the user through creating a new PHP site."""
    if web_server == 'nginx':
        create_nginx_php_site()
    elif web_server == 'apache':
        create_apache_php_site()

def create_nginx_static_site():
    """Creates a static site for Nginx."""
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
        ask_and_install_ssl(domain, 'nginx')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_nginx', error=e)}[/red]")
        # Offer to clean up
        if questionary.confirm(t('nginx_reload_failed_cleanup_prompt')).ask():
             run_command(f"sudo rm {nginx_conf_path}")
             run_command(f"sudo rm /etc/nginx/sites-enabled/{domain}")
             run_command(f"sudo rm -rf {web_root}")
             console.print(t('cleanup_complete'))

def create_apache_static_site():
    """Creates a static site for Apache."""
    console.print(f"\n[bold green]{t('create_new_site_title')}[/bold green]")
    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
    web_root = f"/var/www/{domain}"
    console.print(t('creating_web_root', path=web_root))
    try:
        run_command(f"sudo mkdir -p {web_root}")
        run_command(f"echo '<h1>Welcome to {domain} on Apache!</h1>' | sudo tee {web_root}/index.html")
        run_command(f"sudo chown -R www-data:www-data {web_root}")
        console.print(f"[green]{t('directory_created_successfully')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_directory', error=e)}[/red]")
        return

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
        run_command(f'echo "{apache_conf_content}" | sudo tee {apache_conf_path}')
        run_command(f"sudo a2ensite {domain}.conf")
        console.print(f"[green]{t('apache_config_created')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_apache_config', error=e)}[/red]")
        return

    console.print(t('reloading_apache'))
    try:
        run_command("sudo systemctl reload apache2")
        console.print(f"[bold green]{t('site_created_successfully', domain=domain)}[/bold green]")
        ask_and_install_ssl(domain, 'apache')
    except Exception as e:
        console.print(f"[red]{t('error_reloading_apache', error=e)}[/red]")

def create_nginx_nextjs_site():
    """Guides the user through creating and deploying a Next.js site with Nginx."""
    console.print(f"\n[bold green]{t('create_nextjs_site_title')}[/bold green]")
    
    # Step 1: Check for dependencies (node, npm, pm2)
    deps = ['node', 'npm', 'pm2']
    missing_deps = [dep for dep in deps if not is_tool_installed(dep)]
    
    if missing_deps:
        console.print(f"[bold yellow]{t('missing_dependencies_nextjs', deps=', '.join(missing_deps))}[/bold yellow]")
        # Here you could add logic to guide the user to install them, possibly via dev_tools
        questionary.press_any_key_to_continue(t('please_install_and_retry')).ask()
        return

    # Step 2: Get project details
    project_name = questionary.text(t('enter_project_name_nextjs')).ask()
    if not project_name:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    port = questionary.text(t('enter_port_nextjs'), default='3000').ask()
    if not port:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return

    web_root = f"/var/www/{project_name}"

    # Step 3: Create Next.js app
    console.print(f"[cyan]{t('creating_nextjs_app', path=web_root)}[/cyan]")
    try:
        # Use npx to create the app non-interactively
        # Note: This assumes user is running script with a user that has write permissions to /var/www or is using sudo
        # A better approach would be to create in user's home dir and then move with sudo.
        # For now, let's assume /var/www is prepared.
        run_command(f"sudo mkdir -p {web_root}")
        run_command(f"sudo chown -R $USER:$USER {web_root}") # Temporarily own to create app
        run_command(f"npx create-next-app@latest {web_root} --ts --eslint --tailwind --app --src-dir --import-alias '@/*' --use-npm")
        console.print(f"[green]{t('nextjs_app_created_successfully')}[/green]")
    except Exception as e:
        console.print(f"[red]{t('error_creating_nextjs_app', error=e)}[/red]")
        return

    # Step 4: Build and start with PM2
    try:
        console.print(f"[cyan]{t('building_nextjs_app')}[/cyan]")
        run_command(f"cd {web_root} && npm install && npm run build")
        
        console.print(f"[cyan]{t('starting_app_with_pm2')}[/cyan]")
        run_command(f"cd {web_root} && pm2 start npm --name '{project_name}' -- start -p {port}")
        run_command("pm2 save")
        
        # Set permissions back to www-data for web server access
        run_command(f"sudo chown -R www-data:www-data {web_root}")

    except Exception as e:
        console.print(f"[red]{t('error_building_or_starting_app', error=e)}[/red]")
        return

    # Step 5: Create Nginx config for reverse proxy
    nginx_conf_path = f"/etc/nginx/sites-available/{domain}"
    nginx_conf_content = f"""
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
        run_command(f"sudo ln -s {nginx_conf_path} /etc/nginx/sites-enabled/")
        console.print(f"[green]{t('nginx_config_created')}[/green]")
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
        return 

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

def create_nginx_php_site():
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
    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
        
    web_root = f"/var/www/{domain}"
    
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
        run_command(f"sudo ln -s {nginx_conf_path} /etc/nginx/sites-enabled/")
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
             run_command(f"sudo rm -rf {web_root}")
             console.print(t('cleanup_complete')) 

def create_apache_php_site():
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

    domain = questionary.text(t('enter_domain_name')).ask()
    if not domain:
        console.print(f"[red]{t('operation_cancelled')}[/red]")
        return
    web_root = f"/var/www/{domain}"
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