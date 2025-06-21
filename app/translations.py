import json
import os
import questionary
from rich.console import Console

console = Console()
TRANSLATIONS = {}
DEFAULT_LANG = "en"

def load_language():
    """
    Prompts the user to select a language and loads the corresponding
    translation file into the global TRANSLATIONS dictionary.
    """
    global TRANSLATIONS
    
    # Simple language selection
    lang_choice = questionary.select(
        "Please select a language / Пожалуйста, выберите язык:",
        choices=[
            {"name": "English", "value": "en"},
            {"name": "Русский", "value": "ru"}
        ],
        pointer="👉"
    ).ask()

    if lang_choice is None:
        lang_choice = DEFAULT_LANG # Default to English if user cancels

    filepath = os.path.join("app", "locales", f"{lang_choice}.json")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            TRANSLATIONS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        console.print(f"[bold red]Could not load language file: {filepath}. Defaulting to English.[/bold red]")
        # Fallback to English
        filepath = os.path.join("app", "locales", f"{DEFAULT_LANG}.json")
        with open(filepath, "r", encoding="utf-8") as f:
            TRANSLATIONS = json.load(f)
            
    return lang_choice

def t(key, **kwargs):
    """
    Returns the translated string for a given key.
    Replaces placeholders with values from kwargs.
    """
    return TRANSLATIONS.get(key, key).format(**kwargs) 