# utils/localization.py

import json
import i18n

i18n.load_path.append('locales')
i18n.set('filename_format', '{locale}/messages')
i18n.set('locale', 'en')

_ = i18n.t
_listeners = []

def register_language_listener(callback):
    _listeners.append(callback)

def set_language(lang):
    if not Path(f"locales/{lang}").exists():
        return f"Unsupported language: {lang}\nAvailable languages: {available_languages()}"
    i18n.set('locales', lang)
    for cb in _listeners:
        cb(lang)
    return _("language_been_set")

def available_languages():
    return [p.name for p in Path("locales").iterdir() if p.is_dir()]
