# Changelog

All notable changes to this project will be documented in this file.

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