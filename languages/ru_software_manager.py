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

        # Webmin settings
        "webmin_settings_menu": "Настройки Webmin",
        "webmin_show_settings": "Показать текущие настройки (порт: {port}, SSL: {ssl})",
        "webmin_change_port": "Изменить порт Webmin",
        "webmin_toggle_ssl": "Включить/отключить SSL",
        "webmin_change_pass": "Сменить пароль администратора",
        "webmin_autostart": "Включить/отключить автозапуск",
        "webmin_current_port": "Текущий порт Webmin: {port}",
        "webmin_current_ssl": "SSL: {ssl}",
        "webmin_ssl_on": "включен",
        "webmin_ssl_off": "выключен",
        "webmin_enter_new_port": "Введите новый порт для Webmin (например, 10000):",
        "webmin_port_changed": "Порт Webmin изменён на {port}. Перезапуск...",
        "webmin_ssl_enabled": "SSL включён. Перезапуск...",
        "webmin_ssl_disabled": "SSL отключён. Перезапуск...",
        "webmin_pass_changed": "Пароль администратора Webmin успешно изменён!",
        "webmin_autostart_on": "Автозапуск Webmin включён.",
        "webmin_autostart_off": "Автозапуск Webmin отключён.",
        "webmin_restart_required": "[yellow]Для применения изменений требуется перезапуск Webmin![/yellow]",
        "webmin_settings_back": "Назад к Webmin",
    } 