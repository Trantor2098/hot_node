import csv

import bpy

from . import ServiceBase
from ..utils.constants import HOT_NODE_PKG
from bpy.app.translations import pgettext_iface as iface_

class I18nService(ServiceBase):
    csv_path = ServiceBase.fm.translations_csv_path
    translations = {}

    @classmethod
    def on_enable(cls):
        bpy.app.translations.register(HOT_NODE_PKG, cls.load_translations())

    @classmethod
    def on_disable(cls):
        bpy.app.translations.unregister(HOT_NODE_PKG)
        
    @classmethod
    def msg(cls, msg, locale: str = "en_US"):
        """Get translated message directly."""
        return cls.translations.get(locale, cls.translations["en_US"]).get(("*", msg), msg)

    @classmethod
    def load_translations(cls):
        translations = cls.translations
        translations = {
            "en_US": {},
            "zh_HANS": {},
        }
        with open(cls.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                msgid = row["msgid"]
                translations["en_US"][("*", msgid)] = row["msgid"] # msgid as en_US
                translations["zh_HANS"][("*", msgid)] = row["zh_HANS"]
        return translations