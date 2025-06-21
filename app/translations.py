import json
import os
from rich.console import Console

console = Console()
_translations = {}
_language = 'en'

def load_language(lang='en'):
    """Loads the language file from the locales directory."""
    global _translations, _language
    _language = lang
    try:
        # Construct the path relative to this file's location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, 'locales', f'{lang}.json')
        
        with open(path, 'r', encoding='utf-8') as f:
            _translations = json.load(f)
            
    except FileNotFoundError:
        console.print(f"[bold red]Language file for '{lang}' not found![/bold red]")
        if lang != 'en':
            console.print("[bold yellow]Falling back to English.[/bold yellow]")
            load_language('en')
    except json.JSONDecodeError:
        console.print(f"[bold red]Error decoding language file for '{lang}'. Check for syntax errors.[/bold red]")
        exit(1)


def t(key, **kwargs):
    """
    Returns the translated string for a given key.
    If the key is not found, it returns the key itself.
    """
    return _translations.get(key, key).format(**kwargs) 