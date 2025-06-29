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
    } 