def get_strings():
    return {
        # Menu
        "log_viewer_title": "Log Viewer",
        "log_viewer_prompt": "Select a log to view",
        "important_logs_title": "─── Important System Logs ───",
        "other_logs_title": "─── Other Log Files ───",
        "back_to_main_menu": "Back to Main Menu",
        
        # Log Actions Sub-menu
        "log_actions_prompt": "Selected '{filename}':",
        "action_view": "View Log",
        "action_clear": "Clear Log",
        "action_back": "Back",
        "clear_confirm_prompt": "Are you sure you want to clear this log file? This cannot be undone.",
        "clear_success": "[green]Log file '{filename}' has been cleared.[/green]",
        "clear_fail": "[red]Failed to clear log file '{filename}'.[/red]",

        # Important Logs (Name and Description)
        "log_journald_name": "Journald Logs (journalctl)",
        "log_journald_desc": "Modern systemd logging service. Shows recent system-wide logs.",
        "log_auth_name": "Authentication Log (auth.log)",
        "log_auth_desc": "Login attempts, sudo usage, and other security-related events.",
        "log_dpkg_name": "Package Manager Log (dpkg.log)",
        "log_dpkg_desc": "History of package installations, updates, and removals.",
        "log_syslog_name": "System Log (syslog/rsyslog)",
        "log_syslog_desc": "General system messages from various services.",
        "log_kern_name": "Kernel Log (kern.log)",
        "log_kern_desc": "Kernel-related messages (hardware, drivers, firewall).",

        # File reading
        "log_file_not_found": "[red]Log file not found.[/red]",
        "permission_denied": "[red]Permission denied. Try running with 'sudo'.[/red]",
        "reading_log_file": "Reading log file: {path}",
        "last_100_lines": "Displaying last 100 lines",
        "empty_log_file": "[yellow]Log file is empty.[/yellow]",
        "back_to_main_menu": "Back to Main Menu",
    } 