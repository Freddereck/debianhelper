#-*- coding: utf-8 -*-

def get_strings():
    return {
        # Main Menu
        "manager_title": "Менеджер ПО",
        "manager_prompt": "Выберите ПО для управления",
        "status_installed": "[green]Установлено[/green]",
        "status_not_installed": "[red]Не установлено[/red]",
        "back_to_main_menu": "Вернуться в главное меню",

        # Actions Sub-menu
        "actions_prompt": "Действие для {package}",
        "action_install": "Установить",
        "action_manage_service": "Управлять службой (systemctl)",
        "action_uninstall": "Удалить",
        "action_check_version": "Проверить версию",
        "action_back": "Назад",

        # Service Management Sub-menu
        "service_actions_prompt": "Действия со службой для {package}:",
        "service_start": "Запустить",
        "service_stop": "Остановить",
        "service_restart": "Перезапустить",
        "service_status": "Статус",

        # Action Status Messages
        "installing": "Установка {package}...",
        "install_success": "[green]{package} успешно установлен.[/green]",
        "install_fail": "[red]Не удалось установить {package}.[/red]",
        "uninstalling": "Удаление {package}...",
        "uninstall_confirm": "Вы уверены, что хотите полностью удалить {package}? Это действие удалит данные и конфигурацию.",
        "uninstall_success": "[green]{package} успешно удален.[/green]",
        "uninstall_fail": "[red]Не удалось удалить {package}.[/red]",
        "version_info": "Версия для {package}:",
        "version_not_found": "[yellow]Не удалось определить версию.[/yellow]",
        "service_operation_success": "[green]Операция '{op}' для {package} прошла успешно.[/green]",
        "service_operation_fail": "[red]Операция '{op}' для {package} не удалась.[/red]",
        "need_root_warning": "[bold yellow]Внимание:[/bold yellow] Это действие требует прав root. Пожалуйста, запустите скрипт с 'sudo'.",
        "java_display_name": "Java (OpenJDK)",
    } 