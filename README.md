# 🚀 Linux Helper Panel v3.0 PRE-Release

![Logo](https://img.shields.io/badge/Linux%20Helper-3.0%20PRE--Release-blue?style=for-the-badge)
[![GitHub stars](https://img.shields.io/github/stars/Freddereck/debianhelper?style=social)](https://github.com/Freddereck/debianhelper)

> 🛠️ Консольная панель для управления сервером — всё, что нужно, в одном меню!

---

## ✨ Возможности

- 🖥️ **Мониторинг процессов**
- 👤 **Управление пользователями**
- ⏰ **Cron-менеджер**
- 🌐 **Сетевые инструменты**
- 🧩 **Менеджер ПО** (установка/удаление/обновление)
- 🛡️ **Анализ безопасности**
- 📝 **Просмотр логов**
- ⚡ **WireGuard-менеджер**
- 🕸️ **Менеджер веб-сервера и деплоя**
- 🔄 **Автообновление панели через git**
- ...и многое другое!

---

## 📦 Модули (`/modules`)

| Модуль                | Описание                                      |
|-----------------------|-----------------------------------------------|
| `process_manager.py`  | Мониторинг и управление процессами            |
| `user_manager.py`     | Управление пользователями и паролями          |
| `cron_manager.py`     | Менеджер задач cron                           |
| `network_manager.py`  | Сетевые инструменты (ping, trace, порты и др.)|
| `software_manager.py` | Централизованный менеджер ПО                  |
| `security.py`         | Аудит безопасности, сканеры, обновления       |
| `log_viewer.py`       | Просмотр и очистка логов                      |
| `wireguard_manager.py`| Управление WireGuard VPN                      |
| `webserver_manager.py`| Деплой сайтов, управление nginx, SSL          |
| `pm2_manager.py`      | Управление процессами через PM2               |
| `system_info.py`      | Системная информация (uptime, RAM, load)      |
| `pterodactyl_manager.py`| Управление Pterodactyl Panel и Wings (установка, удаление, диагностика, меню) |
| ...                   | ...                                           |

---

## 🛠️ Поддерживаемые панели и сервисы

### 🕸️ Webmin
- Мощная веб-панель для администрирования Linux-серверов через браузер
- Управление пользователями, сервисами, сетевыми настройками, брандмауэром, пакетами, cron, логами и др.
- Доступ: https://<IP>:10000
- [Подробнее о Webmin](https://www.webmin.com/)

## 🚀 Как установить Webmin через панель?
1. Откройте Менеджер ПО
2. Выберите нужную панель (Webmin)
3. Следуйте инструкциям на экране (будет показано описание, предупреждения и гайды)
4. После установки управляйте сервисами и настройками прямо из панели

---

## 🚀 Быстрый старт

```bash
git clone https://github.com/Freddereck/debianhelper
cd debianhelper
pip install -r requirements.txt
sudo python3 panel.py
```

---

## 🆕 Как обновлять панель?

- Просто выбери пункт **"Обновить панель"** в главном меню!
- Все обновления подтянутся автоматически из [github.com/Freddereck/debianhelper](https://github.com/Freddereck/debianhelper)

---

## 📝 Примеры использования

- Запусти скрипт с правами root:  
  `sudo python3 panel.py`
- Навигируй стрелками, выбирай Enter.
- Для обновления — пункт "Обновить панель".

---

## ℹ️ Важно

- Работает на Debian/Ubuntu и совместимых.
- Почти все функции требуют root-прав.
- Если что-то не работает — смотри логи или пиши в Issues.

---

## 📬 Обратная связь

- Issues и предложения: [github.com/Freddereck/debianhelper/issues](https://github.com/Freddereck/debianhelper/issues)
- Автор: [mderick.su](https://mderick.su/)

---

## 🏷️ Лицензия

MIT