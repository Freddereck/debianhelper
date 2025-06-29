#-*- coding: utf-8 -*-

def get_strings():
    return {
        # Menu
        "log_viewer_title": "Просмотр логов",
        "log_viewer_prompt": "Выберите лог для просмотра",
        "important_logs_title": "─── Важные системные логи ───",
        "other_logs_title": "─── Другие лог-файлы ───",
        "back_to_main_menu": "Вернуться в главное меню",

        # Log Actions Sub-menu
        "log_actions_prompt": "Выбран файл '{filename}':",
        "action_view": "Просмотреть",
        "action_clear": "Очистить",
        "action_back": "Назад",
        "clear_confirm_prompt": "Вы уверены, что хотите очистить этот лог-файл? Это действие необратимо.",
        "clear_success": "[green]Лог-файл '{filename}' был очищен.[/green]",
        "clear_fail": "[red]Не удалось очистить лог-файл '{filename}'.[/red]",

        # Important Logs (Name and Description)
        "log_journald_name": "Логи Journald (journalctl)",
        "log_journald_desc": "Современная служба логирования systemd. Показывает последние общесистемные логи.",
        "log_auth_name": "Логи аутентификации (auth.log)",
        "log_auth_desc": "Попытки входа, использование sudo и другие события, связанные с безопасностью.",
        "log_dpkg_name": "Логи менеджера пакетов (dpkg.log)",
        "log_dpkg_desc": "История установки, обновления и удаления пакетов.",
        "log_syslog_name": "Системный лог (syslog/rsyslog)",
        "log_syslog_desc": "Общие системные сообщения от различных служб.",
        "log_kern_name": "Логи ядра (kern.log)",
        "log_kern_desc": "Сообщения, связанные с ядром (оборудование, драйверы, файрвол).",

        # File reading
        "log_file_not_found": "[red]Лог-файл не найден.[/red]",
        "permission_denied": "[red]Отказано в доступе. Попробуйте запустить с 'sudo'.[/red]",
        "reading_log_file": "Чтение лог-файла: {path}",
        "last_100_lines": "Отображение последних 100 строк",
        "empty_log_file": "[yellow]Лог-файл пуст.[/yellow]",
        "back_to_main_menu": "Вернуться в главное меню",
    } 