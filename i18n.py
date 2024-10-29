import bpy

from . import file


msg = {}


def select_language():
    global msg
    locale = bpy.app.translations.locale
    translation_dict = file.read_translation_dict()
    if locale in ('zh_CN', 'zh_TW', 'zh_HANS', 'zh_HANT'):
        msg = translation_dict["zh"]
    else:
        msg = translation_dict["en"]