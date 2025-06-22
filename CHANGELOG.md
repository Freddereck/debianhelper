# Changelog

## [2.3.0] - YYYY-MM-DD

### Added
- **Web Server Manager**: A major new module for web server management.
  - Automatically detects installed servers (Nginx, Apache).
  - Allows choosing which server to manage if both are installed.
- **Nginx Support**:
  - Create simple static HTML sites.
  - Create and deploy Next.js applications with PM2 and reverse proxy.
  - Create PHP sites with automatic PHP-FPM configuration.
- **Apache Support**:
  - Create simple static HTML sites.
  - Create PHP sites with automatic PHP-FPM configuration (`proxy_fcgi`).
  - *Next.js support for Apache is planned for a future release.*
- **SSL Management (Let's Encrypt)**:
  - Integrated `certbot` support.
  - Option to request and install a free SSL certificate after creating any site.
  - Automatic configuration of HTTPS redirection.
  - A separate menu to list and test renewal of existing certificates.

### Changed
- Refactored the entire `web_server.py` module to be modular and support multiple web servers.
- The main menu now conditionally shows the "Web Server Manager" option.

---

## [2.2.5] - 2025-06-24

### Added
- **Software Manager**: Added the ability to completely uninstall WireGuard (`wireguard-tools` package) through the manager interface, which was previously missing.

## [2.2.4] - 2025-06-24

### Fixed
- **Localization**: Added missing Russian and English translations for the Webmin management feature and for common service control actions and statuses.

## [2.2.3] - 2025-06-24

### Added
- **Software Manager**:
    - Added comprehensive management for **Webmin**. Includes a guided installer that sets up the official repository, an uninstaller, and a management menu to control the `webmin` service and view the access URL.

### Changed
- **Major Refactor (Services & Software)**:
    - **WireGuard** management has been logically moved from the "Service Manager" to the "Software Manager" for better consistency.
    - The "Service Manager" module has been simplified. It no longer contains specific application logic and now serves as a general-purpose viewer for the status of all `systemd` services, providing a clearer, more focused utility.
- **Updater**:
    - The update checker has been significantly improved. It now parses the `CHANGELOG.md` and displays only the notes for the latest available version, rather than showing the entire file. This makes update information much more concise and user-friendly.

## [2.2.2] - 2025-06-23

### Added
- **Developer Tools**:
    - The "Developer Tools" module has been significantly enhanced.
    - Added a comprehensive manager for **Node.js** using **NVM** (Node Version Manager).
    - The panel can now install NVM if it's not present.
    - Implemented features to install different Node.js versions and list installed versions.
    - Added a direct option to install or update **PM2** globally via NPM within the Node.js manager.
- **Software Manager Features**:
    - **Nginx**: Added a feature to list all configured sites from `/etc/nginx/sites-enabled`.
    - **MySQL & PostgreSQL**: Added the ability to list all databases.
    - **Certbot**: Added a feature to list all existing SSL certificates.
    - **Fail2Ban**: Added full management support, including listing jails, checking status, and a utility to unban IP addresses.
    - **Docker Compose**: Added installation support for Docker Compose.
- **Docker Module**:
    - Integrated **Docker Compose** management directly into the Docker module.
    - Users can now point to a project directory and run `up`, `down`, `ps`, and `logs` commands on a `docker-compose.yml` file.
- **Nextcloud**: Laid the groundwork for a future "Nextcloud Installation Wizard" with a placeholder menu item.

### Changed
- **UI/UX**:
    - The Software Manager menu is now more informative. It displays `[Manage]` or `[Install]` prefixes for clarity.
    - For installed software, the panel now attempts to detect and display the current version number (e.g., `Nginx (v1.18.0)`).
- **Code Structure**: The "Developer Tools" module is now the dedicated home for managing development environments like Node.js and Java.

### Fixed
- **3X-UI Detection**: Corrected the file path used to check for an existing 3X-UI installation, ensuring more reliable detection. Added a command to fetch its version.

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