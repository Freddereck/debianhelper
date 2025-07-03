def get_strings():
    return {
        # Main Menu
        "manager_title": "Software Manager",
        "manager_prompt": "Select software to manage",
        "status_installed": "[green]Installed[/green]",
        "status_not_installed": "[red]Not Installed[/red]",
        "back_to_main_menu": "Back to Main Menu",

        # Actions Sub-menu
        "actions_prompt": "Action for {package}",
        "action_install": "Install",
        "action_manage_service": "Manage Service (systemctl)",
        "action_uninstall": "Uninstall",
        "action_check_version": "Check Version",
        "action_back": "Back",

        # Service Management Sub-menu
        "service_actions_prompt": "Service actions for {package}:",
        "service_start": "Start",
        "service_stop": "Stop",
        "service_restart": "Restart",
        "service_status": "Status",

        # Action Status Messages
        "installing": "Installing {package}...",
        "install_success": "[green]{package} installed successfully.[/green]",
        "install_fail": "[red]Failed to install {package}.[/red]",
        "uninstalling": "Uninstalling {package}...",
        "uninstall_confirm": "Are you sure you want to completely uninstall {package}? This will remove its data and configuration.",
        "uninstall_success": "[green]{package} uninstalled successfully.[/green]",
        "uninstall_fail": "[red]Failed to uninstall {package}.[/red]",
        "version_info": "Version for {package}:",
        "version_not_found": "[yellow]Could not determine version.[/yellow]",
        "service_operation_success": "[green]Operation '{op}' for {package} successful.[/green]",
        "service_operation_fail": "[red]Operation '{op}' for {package} failed.[/red]",
        "need_root_warning": "[bold yellow]Warning:[/bold yellow] This action requires root privileges. Please run the script with 'sudo'.",
        "java_display_name": "Java (OpenJDK)",

        # Webmin settings
        "webmin_settings_menu": "Webmin Settings",
        "webmin_show_settings": "Show current settings (port: {port}, SSL: {ssl})",
        "webmin_change_port": "Change Webmin port",
        "webmin_toggle_ssl": "Enable/disable SSL",
        "webmin_change_pass": "Change admin password",
        "webmin_autostart": "Enable/disable autostart",
        "webmin_current_port": "Current Webmin port: {port}",
        "webmin_current_ssl": "SSL: {ssl}",
        "webmin_ssl_on": "enabled",
        "webmin_ssl_off": "disabled",
        "webmin_enter_new_port": "Enter new port for Webmin (e.g., 10000):",
        "webmin_port_changed": "Webmin port changed to {port}. Restarting...",
        "webmin_ssl_enabled": "SSL enabled. Restarting...",
        "webmin_ssl_disabled": "SSL disabled. Restarting...",
        "webmin_pass_changed": "Webmin admin password changed successfully!",
        "webmin_autostart_on": "Webmin autostart enabled.",
        "webmin_autostart_off": "Webmin autostart disabled.",
        "webmin_restart_required": "[yellow]Restart Webmin to apply changes![/yellow]",
        "webmin_settings_back": "Back to Webmin",

        # Java diagnostics
        "java_not_found": "Java not found in the system!",
        "java_found_in_path": "Java found in PATH: {path}",
        "java_found_in_std": "Java found at: {path}",
        "java_not_in_path": "Java not found in standard locations. Please install Java or specify the path manually.",
        "java_manual_path_prompt": "Enter the full path to the java executable:",
        "java_manual_path_success": "Java path saved: {path}",
        "java_manual_path_fail": "[red]Could not find or run java at the specified path.[/red]",
        "java_diagnostics_title": "Java Diagnostics",
    } 