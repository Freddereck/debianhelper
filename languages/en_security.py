def get_strings():
    return {
        # Security Sub-menu
        "security_menu_title": "Security Analysis Menu",
        "security_menu_prompt": "Select a tool to run",
        "port_scan_option": "Port Scanner (ss)",
        "ssh_config_option": "SSH Configuration Analysis",
        "system_updates_option": "Check for System Updates",
        "rootkit_check_option": "Rootkit Scanner (chkrootkit)",
        "lynis_audit_option": "Comprehensive Audit (Lynis)",
        "back_to_main_menu": "Back to Main Menu",

        # check_open_ports
        "open_ports_title": "Open Ports (TCP/UDP)",
        "protocol_col": "Protocol",
        "address_col": "Local Address:Port",
        "process_col": "Process",
        "no_ports_msg": "[green]No open ports found.[/green]",
        "ss_not_found_err": "[red]Error: 'ss' command not found. Make sure iproute2 utilities are installed.[/red]",
        "ss_exec_err": "[red]Error executing 'ss': {e}[/red]",
        
        # run_security_analysis
        "start_security_analysis": "\n[bold cyan]=== Starting Security Analysis ===[/bold cyan]",

        # check_system_updates
        "checking_updates": "\n[bold]Checking for available updates...[/bold]",
        "updates_title": "Available Package Updates",
        "package_col": "Package",
        "version_col": "New Version",
        "no_updates_msg": "[green]Congratulations! Your system is up to date.[/green]",
        "updates_found_msg": "[yellow]Updates found. It is recommended to run 'sudo apt update && sudo apt upgrade'.[/yellow]",
        "apt_not_found_err": "[red]Failed to check for updates. Make sure 'apt' is installed and available.[/red]",
        "generic_err": "[red]An error occurred: {e}[/red]",

        # check_ssh_config
        "checking_ssh_config": "\n[bold]Checking SSH configuration...[/bold]",
        "ssh_config_path": "/etc/ssh/sshd_config",
        "ssh_not_found": "[yellow]SSH config file ({path}) not found. SSH server is likely not installed.[/yellow]",
        "ssh_root_ok": "[green]Root login via SSH is disabled. This is good.[/green]",
        "ssh_root_bad": "[bold red]Insecure configuration found: 'PermitRootLogin yes'. It is recommended to disable it.[/bold red]",
        "ssh_default_case": "[yellow]The 'PermitRootLogin' parameter is not explicitly set. The default may allow it. It's recommended to set 'PermitRootLogin no'.[/yellow]",
        "ssh_permission_err": "[red]Could not read {path}. Try running with sudo.[/red]",
        "ssh_read_err": "[red]An error occurred while reading SSH config: {e}[/red]",
        "ssh_undetermined_status": "[yellow]Could not determine the 'PermitRootLogin' status precisely.[/yellow]",
        "ssh_advice_title": "SSH Hardening Advice",
        "param_check_ok": "[green]OK[/green]",
        "param_check_bad": "[bold red]BAD[/bold red]",
        "param_check_info": "[yellow]INFO[/yellow]",
        "param_permit_root_login": "PermitRootLogin is 'no' or 'prohibit-password'",
        "param_password_auth": "PasswordAuthentication is 'no'",
        "param_protocol_2": "Protocol is '2'",
        "param_x11_forwarding": "X11Forwarding is 'no'",

        # Rootkit check
        "checking_for_rootkits": "\n[bold]Checking for rootkits...[/bold]",
        "chkrootkit_not_found": "[yellow]The utility '{package}' is not installed.[/yellow]",
        "install_prompt": "Would you like to try and install it now? (Requires sudo)",
        "installing_package": "Installing {package}...",
        "install_success": "[green]{package} installed successfully.[/green]",
        "install_fail": "[red]Failed to install {package}. Please install it manually.[/red]",
        "running_chkrootkit": "Running chkrootkit, this may take a moment...",
        "chkrootkit_results": "Chkrootkit Results:",
        "chkrootkit_error": "[red]An error occurred while running chkrootkit: {e}[/red]",
        "need_root_warning": "[bold yellow]Warning:[/bold yellow] This action requires root privileges. Please run the script with 'sudo' for full functionality.",

        # Lynis Audit
        "running_lynis": "Running Lynis audit... This may take several minutes.",
        "lynis_summary_title": "Lynis Audit Summary",
        "lynis_hardening_index": "Hardening Index",
        "lynis_tests_done": "Tests performed",
        "lynis_warnings": "Warnings",
        "lynis_suggestions": "Suggestions",
        "lynis_report_file": "Full report saved to",
        "lynis_suggestions_title": "Suggestions from Lynis",
        "lynis_suggestion_id": "ID",
        "lynis_suggestion_details": "Details",
        "lynis_suggestion_action": "Action",
        "lynis_error": "[red]An error occurred while running Lynis: {e}[/red]",
        "operation_cancelled": "[yellow]Operation cancelled. Returning to the previous menu.[/yellow]",
    } 