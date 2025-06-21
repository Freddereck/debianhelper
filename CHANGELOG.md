# Changelog

All notable changes to this project will be documented in this file.

## [2.2.1] - 2025-06-22

### Added
- **Major Feature: Software Manager**: A new centralized module (`app/modules/software_manager.py`) for installing and managing various services. The menu dynamically shows "Install" or "Manage" based on the software's installation status.
- **Nginx & Apache2**: Added full management support (status, restart, reload, config test, uninstall).
- **Databases**: Added management for **MySQL**, **PostgreSQL**, and **MongoDB**.
- **In-Memory Store**: Added management for **Redis**.
- **Custom Installers**:
    - **3X-UI**: Added a custom installer and manager for the 3X-UI panel.
    - **PHPMyAdmin**: Added a guided installer with dependency checks.
    - **Certbot (Let's Encrypt)**: Added an installer and manager to obtain SSL certificates using the Nginx plugin.
- **Utilities**: Added a universal `is_tool_installed` function in `app/utils.py` and improved installation checks to support both PATH commands and direct file paths.
- **Localization**: Added dozens of new translation keys in `ru.json` and `en.json` to support all new features.

### Changed
- **Main Menu**: The menu now features a "Software Manager" entry, consolidating all service management.
- **PM2 Manager**: The menu item for the PM2 manager is now conditional and only appears if PM2 is actually installed.
- **Code Structure**:
    - The old `app/modules/web_server.py` has been removed.
    - Logic for MySQL and PHPMyAdmin has been migrated from `dev_tools.py` to the new `software_manager.py`.
    - The `dev_tools.py` module is now leaner, containing only the Java installer.

### Fixed
- **Missing functionality**: Re-implemented the lost "MySQL Manager" functionality and greatly expanded it.

## [2.1.4] - 2025-06-21

### Added
- **Docker:** Реализован просмотр списка локальных Docker-образов.
- **Firewall:** Добавлена проверка статуса UFW и инструкции по установке, если он отсутствует.
- **Localization:** Добавлены многочисленные переводы для модулей Firewall, WireGuard, Network, Users и Docker.

### Changed
- **UI:** Полностью переработан дизайн главного меню для более современного и удобного вида. Добавлен копирайт.
- **System Monitor:** Интерфейс полностью переделан, чтобы быть более похожим на `htop`, с единой таблицей процессов и наглядными индикаторами нагрузки вверху.
- **Updater:** Механизм обновления полностью переписан для использования GitHub API, что значительно повысило его надежность. Исправлена критическая ошибка, когда скрипт не мог обновиться.

### Fixed
- **Cron:** Исправлена критическая ошибка, приводившая к падению приложения при входе в менеджер Cron.
- **Hardcoded Strings:** Заменены жестко закодированные строки на ключи локализации в модулях Network и Users.

## [Unreleased]

### Added
- First draft of the changelog.

## [2.0.0] - 2023-10-27

### Added
- Complete project refactoring into modules.
- Language selection (English/Russian).
- Self-update mechanism via Git.
- Docker, Services, Security, Health, and Monitor modules.

### Changed
- Improved UI with `rich` and `questionary`.

## [1.0.0] - 2023-10-26

### Added
- Initial script for server management.
- Basic health checks and system monitoring. 