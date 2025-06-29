#-*- coding: utf-8 -*-

def get_strings():
    return {
        # Security Sub-menu
        "security_menu_title": "Меню анализа безопасности",
        "security_menu_prompt": "Выберите инструмент для запуска",
        "port_scan_option": "Сканер портов (ss)",
        "ssh_config_option": "Анализ конфигурации SSH",
        "system_updates_option": "Проверка системных обновлений",
        "rootkit_check_option": "Сканер руткитов (chkrootkit)",
        "lynis_audit_option": "Комплексный аудит (Lynis)",
        "back_to_main_menu": "Вернуться в главное меню",

        # check_open_ports
        "open_ports_title": "Открытые порты (TCP/UDP)",
        "protocol_col": "Протокол",
        "address_col": "Локальный адрес:Порт",
        "process_col": "Процесс",
        "no_ports_msg": "[green]Открытых портов не найдено.[/green]",
        "ss_not_found_err": "[red]Ошибка: команда 'ss' не найдена. Убедитесь, что утилиты iproute2 установлены.[/red]",
        "ss_exec_err": "[red]Ошибка при выполнении 'ss': {e}[/red]",

        # run_security_analysis
        "start_security_analysis": "\n[bold cyan]=== Запуск анализа безопасности ===[/bold cyan]",

        # check_system_updates
        "checking_updates": "\n[bold]Проверка доступных обновлений...[/bold]",
        "updates_title": "Доступные обновления пакетов",
        "package_col": "Пакет",
        "version_col": "Новая версия",
        "no_updates_msg": "[green]Поздравляем! Ваша система обновлена.[/green]",
        "updates_found_msg": "[yellow]Найдены обновления. Рекомендуется выполнить 'sudo apt update && sudo apt upgrade'.[/yellow]",
        "apt_not_found_err": "[red]Не удалось проверить обновления. Убедитесь, что 'apt' установлен и доступен.[/red]",
        "generic_err": "[red]Произошла ошибка: {e}[/red]",

        # check_ssh_config
        "checking_ssh_config": "\n[bold]Проверка конфигурации SSH...[/bold]",
        "ssh_config_path": "/etc/ssh/sshd_config",
        "ssh_not_found": "[yellow]Конфигурационный файл SSH ({path}) не найден. Сервер SSH, вероятно, не установлен.[/yellow]",
        "ssh_root_ok": "[green]Вход для root через SSH отключен. Это хорошо.[/green]",
        "ssh_root_bad": "[bold red]Обнаружена небезопасная конфигурация: 'PermitRootLogin yes'. Рекомендуется отключить.[/bold red]",
        "ssh_default_case": "[yellow]Параметр 'PermitRootLogin' не задан явно. По умолчанию он может быть разрешен. Рекомендуется установить 'PermitRootLogin no'.[/yellow]",
        "ssh_permission_err": "[red]Не удалось прочитать файл {path}. Попробуйте запустить с sudo.[/red]",
        "ssh_read_err": "[red]Произошла ошибка при чтении файла SSH: {e}[/red]",
        "ssh_undetermined_status": "[yellow]Не удалось точно определить статус 'PermitRootLogin'.[/yellow]",
        "ssh_advice_title": "Рекомендации по усилению SSH",
        "param_check_ok": "[green]OK[/green]",
        "param_check_bad": "[bold red]ПЛОХО[/bold red]",
        "param_check_info": "[yellow]ИНФО[/yellow]",
        "param_permit_root_login": "PermitRootLogin установлен в 'no' или 'prohibit-password'",
        "param_password_auth": "PasswordAuthentication установлен в 'no'",
        "param_protocol_2": "Protocol установлен в '2'",
        "param_x11_forwarding": "X11Forwarding установлен в 'no'",

        # Rootkit check
        "checking_for_rootkits": "\n[bold]Проверка на руткиты...[/bold]",
        "chkrootkit_not_found": "[yellow]Утилита '{package}' не установлена.[/yellow]",
        "install_prompt": "Хотите попробовать установить ее сейчас? (Требуется sudo)",
        "installing_package": "Установка {package}...",
        "install_success": "[green]{package} успешно установлен.[/green]",
        "install_fail": "[red]Не удалось установить {package}. Пожалуйста, установите его вручную.[/red]",
        "running_chkrootkit": "Запускаю chkrootkit, это может занять некоторое время...",
        "chkrootkit_results": "Результаты Chkrootkit:",
        "chkrootkit_error": "[red]Произошла ошибка при запуске chkrootkit: {e}[/red]",
        "need_root_warning": "[bold yellow]Внимание:[/bold yellow] Это действие требует прав root. Пожалуйста, запустите скрипт с 'sudo' для полной функциональности.",
        
        # Lynis Audit
        "running_lynis": "Выполняется аудит Lynis... Это может занять несколько минут.",
        "lynis_summary_title": "Сводка аудита Lynis",
        "lynis_hardening_index": "Индекс защищенности",
        "lynis_tests_done": "Проведено тестов",
        "lynis_warnings": "Предупреждения",
        "lynis_suggestions": "Предложения",
        "lynis_report_file": "Полный отчет сохранен в",
        "lynis_suggestions_title": "Предложения от Lynis",
        "lynis_suggestion_id": "ID",
        "lynis_suggestion_details": "Описание",
        "lynis_suggestion_action": "Действие",
        "lynis_error": "[red]Произошла ошибка при запуске Lynis: {e}[/red]",
        "operation_cancelled": "[yellow]Операция отменена. Возврат в предыдущее меню.[/yellow]",
    } 