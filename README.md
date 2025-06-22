# Консольная панель управления сервером "И так сойдёт"

Короче, привет. Тебе тоже надоело постоянно гуглить одни и те же консольные команды, чтобы проверить, чем там дышит твой сервер? Вечно забываешь, как посмотреть логи докера, проверить обновы или рестартануть какой-нибудь сервис?

Меня это тоже достало. Поэтому я накидал на коленке этот скрипт на Python. Это не какая-то навороченная панель с графиками и свистелками. Это простая менюшка прямо в твоей консоли, чтобы делать самые частые вещи, не ломая голову и пальцы. Запустил, выбрал стрелочками, нажал Enter. Всё.

## Server Panel

A modular, console-based server administration tool written in Python.

## Features

- **System Health Check**: Check for APT updates and perform system cleanup.
- **Service Manager**: Start, stop, restart, and manage systemd services.
- **Docker Manager**: Manage Docker containers, including start, stop, logs, and system prune.
- **Software Manager**: A centralized place to install/uninstall and manage common software like Webmin.
- **System Monitor**: A live, `htop`-like dashboard showing CPU, RAM, Disk, and process information.
- **Security Audit**: Manage Fail2Ban and view network connections.
- **Developer Tools**: Quick access to install and manage development tools like MySQL.
- **Web Server Manager**:
  - Automatically detects and manages **Nginx** and **Apache**.
  - **Site Creation**:
    - Static HTML sites.
    - PHP sites with automatic PHP-FPM configuration.
    - Node.js sites (Next.js) with PM2 process management and reverse proxy setup.
  - **SSL Management**:
    - Integrated Let's Encrypt (`certbot`) support.
    - Automatically request and install SSL certificates for any created site.
    - Manage existing certificates (list, renew).
- **And more...**: Includes managers for Cron jobs, logs, packages, users, firewall (UFW/iptables), PM2, and network tools.

## Как эту штуку завести?

Сделано для Debian/Ubuntu и подобных. На других может и не взлететь.

1.  **Сначала скачай это всё:**
    ```bash
    git clone https://github.com/Freddereck/debianhelper
    cd debianhelper
    ```

2.  **Поставь зависимости:**
    Нужен `python3` и `pip`. Обычно они уже есть.
    ```bash
    pip install -r requirements.txt
    ```
    Если ругается, что нет `pip`, поставь его: `sudo apt install python3-pip`.

3.  **Запускай:**
    Почти все функции требуют прав админа, так что без `sudo` никуда.
    ```bash
    sudo python3 server_panel.py
    ```

После этого появится меню. Дальше разберёшься, не маленький.

## Важное замечание

Я делал это для себя, на скорую руку. Оно может где-то глючить, падать или работать не так, как ты ожидаешь. Используй на свой страх и риск. Если из-за этого скрипта твой сервер превратится в тыкву — я не виноват.

Если есть идеи, как сделать лучше, или нашёл баг — можешь написать в Issues. Может быть, я даже посмотрю, если не будет лень.

Удачи. 

## Installation / Usage

1.  Clone the repository:
    ```bash
    git clone https://github.com/Freddereck/server-panel.git
    ```
2.  Navigate to the directory:
    ```bash
    cd server-panel
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the script:
    ```bash
    python server_panel.py
    ```
It is recommended to run the script with `sudo` as many functions require root privileges.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. 
