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

        # Pterodactyl
        "pterodactyl_description": "Pterodactyl — это бесплатная open-source панель для управления игровыми серверами (Minecraft, CS:GO, Rust и др.) через красивый веб-интерфейс. Все серверы изолированы в Docker-контейнерах. Подробнее: https://pterodactyl.io/project/introduction.html",
        "pterodactyl_manage_menu": "Управление Pterodactyl Panel",
        "pterodactyl_open_panel": "Открыть веб-панель Pterodactyl",
        "pterodactyl_add_server": "Добавить игровой сервер (через веб-интерфейс)",

        # Java diagnostics
        "java_not_found": "Java не найдена в системе!",
        "java_found_in_path": "Java найдена в PATH: {path}",
        "java_found_in_std": "Java найдена по пути: {path}",
        "java_not_in_path": "Java не найдена в стандартных путях. Установите Java или укажите путь вручную.",
        "java_manual_path_prompt": "Введите полный путь к исполняемому файлу java:",
        "java_manual_path_success": "Путь к Java сохранён: {path}",
        "java_manual_path_fail": "[red]Не удалось найти или запустить java по указанному пути.[/red]",
        "java_diagnostics_title": "Диагностика Java",

        # Wings
        "wings_description": "Wings — это агент (демон) для запуска игровых серверов под управлением панели Pterodactyl. Требует Docker. Подробнее: https://pterodactyl.io/wings/1.11/installing.html",
        "wings_manage_menu": "Управление Wings (Pterodactyl)",
        "wings_open_docs": "Открыть документацию Wings",
        "wings_connect_guide": "Для подключения Wings к панели Pterodactyl следуйте инструкции на https://pterodactyl.io/wings/1.11/installing.html. После установки добавьте node в панели и используйте токен для авторизации.",
        "wings_status": "Статус Wings",
        "wings_start": "Запустить Wings",
        "wings_stop": "Остановить Wings",
        "wings_restart": "Перезапустить Wings",
        "wings_remove": "Удалить Wings",
    } 