import datetime
import os

LOG_FILE = '/var/log/pterodactyl_manager.log'

def log(msg, level='INFO'):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{now}] [{level}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass 