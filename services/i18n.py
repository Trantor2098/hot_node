import csv

import bpy

from . import ServiceBase
from ..utils.constants import HOT_NODE_PKG
from bpy.app.translations import pgettext_iface as iface_

class I18nService(ServiceBase):
    csv_path = ServiceBase.fm.translations_csv_path
    translations = {
        "en_US": {},
        "zh_HANS": {},
    }

    @classmethod
    def on_enable(cls):
        bpy.app.translations.register(HOT_NODE_PKG, cls.load_translations())

    @classmethod
    def on_disable(cls):
        bpy.app.translations.unregister(HOT_NODE_PKG)
        
    @classmethod
    def msg(cls, msg, locale: str = "en_US"):
        """Get translated message directly."""
        translation = cls.translations.get(locale)
        msg = translation.get(("*", msg), msg) if translation else msg
        return msg
    
    @classmethod
    def get_msg_from_all_locales(cls, msg):
        """Get message from all locales."""
        translations = cls.translations
        return {locale: translation.get(("*", msg), msg) for locale, translation in translations.items()}

    @classmethod
    def load_translations(cls):
        translations = cls.translations
        with open(cls.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                msgid = row["msgid"]
                translations["en_US"][("*", msgid)] = row["msgid"] # msgid as en_US
                translations["zh_HANS"][("*", msgid)] = row["zh_HANS"]
        return translations