import importlib
import glob
import os

# This will hold all the loaded strings for the selected language
_language_strings = {}

def load_language_strings(lang_code):
    """Loads all language strings for the given language code from all modules."""
    global _language_strings
    _language_strings = {}
    # Основной файл
    main_module = f"languages.{lang_code}_panel"
    try:
        mod = importlib.import_module(main_module)
        _language_strings.update(mod.get_strings())
    except Exception:
        pass
    # Все остальные языковые файлы
    lang_dir = os.path.join(os.path.dirname(__file__), "languages")
    for path in glob.glob(os.path.join(lang_dir, f"{lang_code}_*.py")):
        fname = os.path.basename(path)
        if fname == f"{lang_code}_panel.py":
            continue
        modname = f"languages.{fname[:-3]}"
        try:
            mod = importlib.import_module(modname)
            _language_strings.update(mod.get_strings())
        except Exception:
            pass

def get_string(key, **kwargs):
    """
    Gets a string by its key and formats it if needed.
    """
    s = _language_strings.get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s