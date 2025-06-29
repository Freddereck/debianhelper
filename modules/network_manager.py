import shutil
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from modules.panel_utils import clear_console
from localization import get_string
import concurrent.futures

console = Console()

# --- Открытые порты ---
def show_ports():
    if shutil.which('ss'):
        res = subprocess.run(['ss', '-tulnp'], capture_output=True, text=True)
        lines = res.stdout.splitlines() if res and res.stdout else []
    elif shutil.which('netstat'):
        res = subprocess.run(['netstat', '-tulnp'], capture_output=True, text=True)
        lines = res.stdout.splitlines() if res and res.stdout else []
    elif shutil.which('lsof'):
        res = subprocess.run(['lsof', '-i', '-n', '-P'], capture_output=True, text=True)
        lines = res.stdout.splitlines() if res and res.stdout else []
    else:
        console.print(f"[red]{get_string('network_no_tools')}[/red]")
        inquirer.text(message=get_string('network_press_enter')).execute()
        return
    table = Table(title=get_string('network_ports'), show_lines=True)
    for i, line in enumerate(lines[:1]):
        for col in line.split():
            table.add_column(col, style='cyan')
    for line in lines[1:]:
        table.add_row(*line.split())
    console.print(table)
    inquirer.text(message=get_string('network_press_enter')).execute()

# --- Speedtest ---
def run_speedtest():
    if not shutil.which('speedtest-cli'):
        console.print(f"[yellow]{get_string('network_speedtest_not_installed')}[/yellow]")
        install = inquirer.confirm(message=get_string('network_speedtest_install'), default=True).execute()
        if install:
            if shutil.which('apt'):
                subprocess.run(['sudo', 'apt', 'install', '-y', 'speedtest-cli'])
            elif shutil.which('yum'):
                subprocess.run(['sudo', 'yum', 'install', '-y', 'speedtest-cli'])
            elif shutil.which('pacman'):
                subprocess.run(['sudo', 'pacman', '-Sy', 'speedtest-cli'])
            else:
                console.print(f"[red]{get_string('network_no_tools')}[/red]")
                inquirer.text(message=get_string('network_press_enter')).execute()
                return
        else:
            return
    console.print(f"[green]{get_string('network_speedtest_running')}[/green]")
    inquirer.text(message=get_string('network_press_enter')).execute()
    subprocess.run(['speedtest-cli'])
    inquirer.text(message=get_string('network_press_enter')).execute()

# --- Пинг/trace/lookup ---
def run_ping():
    host = inquirer.text(message=get_string('network_ping_prompt')).execute()
    if not host:
        return
    subprocess.run(['ping', '-c', '4', host])
    inquirer.text(message=get_string('network_press_enter')).execute()

def run_traceroute():
    host = inquirer.text(message=get_string('network_trace_prompt')).execute()
    if not host:
        return
    if shutil.which('traceroute'):
        subprocess.run(['traceroute', host])
    else:
        subprocess.run(['ping', '-c', '1', host])
        console.print('[yellow]traceroute не найден, выполнен ping.[/yellow]')
    inquirer.text(message=get_string('network_press_enter')).execute()

def run_nslookup():
    host = inquirer.text(message=get_string('network_nslookup_prompt')).execute()
    if not host:
        return
    subprocess.run(['nslookup', host])
    inquirer.text(message=get_string('network_press_enter')).execute()

# --- UFW ---
def ufw_menu():
    if not shutil.which('ufw'):
        console.print(f"[yellow]{get_string('network_ufw_not_installed')}[/yellow]")
        inquirer.text(message=get_string('network_press_enter')).execute()
        return
    while True:
        clear_console()
        res = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
        status = res.stdout if res and res.stdout else 'unknown'
        console.print(Panel(status, title=get_string('network_ufw_status'), border_style='green'))
        choices = [
            Choice('enable', get_string('network_ufw_enable')),
            Choice('disable', get_string('network_ufw_disable')),
            Choice('allow', get_string('network_ufw_allow')),
            Choice('deny', get_string('network_ufw_deny')),
            Choice(None, get_string('network_back'))
        ]
        action = inquirer.select(message=get_string('network_ufw'), choices=choices, vi_mode=True).execute()
        if action == 'enable':
            subprocess.run(['sudo', 'ufw', 'enable'])
        elif action == 'disable':
            subprocess.run(['sudo', 'ufw', 'disable'])
        elif action == 'allow':
            port = inquirer.text(message=get_string('network_ufw_port_prompt')).execute()
            if port:
                subprocess.run(['sudo', 'ufw', 'allow', port])
        elif action == 'deny':
            port = inquirer.text(message=get_string('network_ufw_port_prompt')).execute()
            if port:
                subprocess.run(['sudo', 'ufw', 'deny', port])
        else:
            break
        inquirer.text(message=get_string('network_press_enter')).execute()

def show_interfaces():
    if shutil.which('ip'):
        res = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
        console.print(Panel(res.stdout, title=get_string('network_interfaces_title'), border_style='cyan'))
    elif shutil.which('ifconfig'):
        res = subprocess.run(['ifconfig'], capture_output=True, text=True)
        console.print(Panel(res.stdout, title=get_string('network_interfaces_title'), border_style='cyan'))
    else:
        console.print(f"[red]{get_string('network_no_tools')}[/red]")
    inquirer.text(message=get_string('network_press_enter')).execute()

def run_traffic_monitor():
    tool = None
    for t in ['bmon', 'iftop', 'nload']:
        if shutil.which(t):
            tool = t
            break
    if not tool:
        console.print(f"[yellow]{get_string('network_traffic_not_found')}[/yellow]")
        install = inquirer.confirm(message=get_string('network_traffic_install'), default=True).execute()
        if install:
            if shutil.which('apt'):
                subprocess.run(['sudo', 'apt', 'install', '-y', 'bmon'])
            elif shutil.which('yum'):
                subprocess.run(['sudo', 'yum', 'install', '-y', 'bmon'])
            elif shutil.which('pacman'):
                subprocess.run(['sudo', 'pacman', '-Sy', 'bmon'])
            else:
                console.print(f"[red]{get_string('network_no_tools')}[/red]")
                inquirer.text(message=get_string('network_press_enter')).execute()
                return
            tool = 'bmon'
        else:
            return
    console.print(f"[green]{get_string('network_traffic_running', tool=tool)}[/green]")
    inquirer.text(message=get_string('network_press_enter')).execute()
    subprocess.run([tool])
    console.print(f"[cyan]{get_string('network_traffic_exit', tool=tool)}[/cyan]")
    inquirer.text(message=get_string('network_press_enter')).execute()

# --- VLESS Popular Sites by Country (dict) ---
VLESS_SITES = {
    "Россия": ["yandex.ru", "mail.ru", "vk.com", "rambler.ru", "wildberries.ru", "ozon.ru", "lenta.ru", "avito.ru", "sberbank.ru", "rbc.ru"],
    "США": ["google.com", "youtube.com", "facebook.com", "twitter.com", "amazon.com", "netflix.com", "reddit.com", "apple.com", "microsoft.com", "cloudflare.com"],
    "Германия": ["adac.de", "spiegel.de", "bild.de", "web.de", "gmx.net", "t-online.de", "faz.net", "welt.de", "focus.de", "chip.de"],
    "Нидерланды": ["marktplaats.nl", "nu.nl", "bol.com", "telegraaf.nl", "rabobank.nl", "abnamro.nl", "ing.nl", "ah.nl", "nos.nl", "funda.nl"],
    "Польша": ["allegro.pl", "onet.pl", "wp.pl", "interia.pl", "olx.pl", "gazeta.pl", "o2.pl", "tvn24.pl", "bankier.pl", "money.pl"],
    "Великобритания": ["bbc.com", "theguardian.com", "dailymail.co.uk", "gov.uk", "sky.com", "telegraph.co.uk", "independent.co.uk", "mirror.co.uk", "express.co.uk", "thesun.co.uk"],
    "Франция": ["lemonde.fr", "lefigaro.fr", "orange.fr", "free.fr", "sfr.fr", "leparisien.fr", "bfmtv.com", "lci.fr", "ouest-france.fr", "20minutes.fr"],
    "Китай": ["baidu.com", "qq.com", "taobao.com", "tmall.com", "jd.com", "sina.com.cn", "sohu.com", "163.com", "alipay.com", "youku.com"],
    "Япония": ["yahoo.co.jp", "rakuten.co.jp", "dmm.com", "amazon.co.jp", "goo.ne.jp", "livedoor.com", "nicovideo.jp", "cookpad.com", "hatena.ne.jp", "excite.co.jp"],
    "Канада": ["cbc.ca", "amazon.ca", "canada.ca", "theglobeandmail.com", "toronto.ca", "rbc.com", "td.com", "scotiabank.com", "cp24.com", "globalnews.ca"],
    "Турция": ["sahibinden.com", "hurriyet.com.tr", "hepsiburada.com", "milliyet.com.tr", "trendyol.com", "sabah.com.tr", "sozcu.com.tr", "ensonhaber.com", "haberturk.com", "ntv.com.tr"],
    "Бразилия": ["globo.com", "uol.com.br", "mercadolivre.com.br", "olx.com.br", "americanas.com.br", "ig.com.br", "terra.com.br", "r7.com", "folha.uol.com.br", "estadao.com.br"],
    "Индия": ["google.co.in", "flipkart.com", "amazon.in", "indiatimes.com", "rediff.com", "sbi.co.in", "icicibank.com", "hdfcbank.com", "timesofindia.indiatimes.com", "ndtv.com"],
    "Австралия": ["news.com.au", "abc.net.au", "realestate.com.au", "seek.com.au", "domain.com.au", "smh.com.au", "theage.com.au", "anz.com.au", "westpac.com.au", "commbank.com.au"],
    "Сингапур": ["straitstimes.com", "singaporeair.com", "lazada.sg", "uob.com.sg", "dbs.com.sg", "ocbc.com", "sgcarmart.com", "hardwarezone.com.sg", "gov.sg", "ntucfairprice.com.sg"],
    "Южная Корея": ["naver.com", "11st.co.kr", "auction.co.kr", "ssg.com", "lotte.com", "yes24.com", "coupang.com", "gmarket.co.kr", "interpark.com", "daum.net"],
    "США (взрослые)": ["pornhub.com", "xvideos.com", "xhamster.com", "redtube.com", "brazzers.com", "youporn.com", "xnxx.com", "spankbang.com", "porntube.com", "tnaflix.com"],
}

def vless_ping_locations():
    country_choices = [Choice(country) for country in VLESS_SITES.keys()]
    selected_countries = inquirer.checkbox(
        message=get_string('vless_ping_select'),
        choices=country_choices,
        vi_mode=True
    ).execute()
    if not selected_countries:
        confirm = inquirer.confirm(message=get_string('vless_ping_none_selected'), default=True).execute()
        if not confirm:
            return
        selected_countries = list(VLESS_SITES.keys())
    selected_sites = []
    for country in selected_countries:
        for site in VLESS_SITES[country]:
            selected_sites.append((country, site))
    results = []
    total = len(selected_sites)
    def ping_site(args):
        country, host, idx = args
        console.print(f"[cyan][{idx}/{total}] {country} / {host}[/cyan]")
        try:
            res = subprocess.run(["ping", "-c", "2", "-W", "2", host], capture_output=True, text=True, timeout=5)
            avg_ping = None
            if res and res.stdout:
                import re
                match = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms", res.stdout)
                if match:
                    avg_ping = float(match.group(2))
        except Exception:
            avg_ping = None
        ping_str = f"{avg_ping:.1f} ms" if avg_ping is not None else get_string('vless_ping_error')
        console.print(f"[bold]{country}[/bold] / [magenta]{host}[/magenta]: [green]{ping_str}[/green]")
        return {"country": country, "host": host, "avg_ping": avg_ping}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        args = [(country, host, idx+1) for idx, (country, host) in enumerate(selected_sites)]
        for result in executor.map(ping_site, args):
            results.append(result)
    successful = [r for r in results if r["avg_ping"] is not None]
    top5 = sorted(successful, key=lambda r: r["avg_ping"])[:5]
    min_ping = min((r["avg_ping"] for r in top5), default=None)
    table = Table(title=get_string('vless_ping_results_title'), show_lines=True)
    table.add_column(get_string('vless_ping_country'), style="cyan")
    table.add_column(get_string('vless_ping_host'), style="magenta")
    table.add_column(get_string('vless_ping_avg'), style="green")
    for r in top5:
        ping_str = f"{r['avg_ping']:.1f}" if r["avg_ping"] is not None else get_string('vless_ping_error')
        style = "bold green" if min_ping is not None and r["avg_ping"] == min_ping else None
        table.add_row(r["country"], r["host"], ping_str, style=style)
    console.print(table)
    inquirer.text(message=get_string('vless_ping_continue')).execute()

def run_network_manager():
    while True:
        clear_console()
        console.print(Panel(f"[bold green]{get_string('network_manager_title')}[/bold green]", border_style='green'))
        choices = [
            Choice('interfaces', get_string('network_interfaces')),
            Choice('traffic', get_string('network_traffic')),
            Choice('ports', get_string('network_ports')),
            Choice('speedtest', get_string('network_speedtest')),
            Choice('ping', get_string('network_ping')),
            Choice('trace', get_string('network_trace')),
            Choice('nslookup', get_string('network_nslookup')),
            Choice('ufw', get_string('network_ufw')),
            Choice('vless_ping', get_string('vless_ping')),
            Choice(None, get_string('network_back'))
        ]
        action = inquirer.select(message=get_string('network_manager_title'), choices=choices, vi_mode=True).execute()
        if action == 'interfaces':
            show_interfaces()
        elif action == 'traffic':
            run_traffic_monitor()
        elif action == 'ports':
            show_ports()
        elif action == 'speedtest':
            run_speedtest()
        elif action == 'ping':
            run_ping()
        elif action == 'trace':
            run_traceroute()
        elif action == 'nslookup':
            run_nslookup()
        elif action == 'ufw':
            ufw_menu()
        elif action == 'vless_ping':
            vless_ping_locations()
        else:
            break 