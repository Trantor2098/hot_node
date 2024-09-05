# BEGIN GPL LICENSE BLOCK #####
#
# This file is part of Hot Node.
#
# Hot Node is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# Hot Node is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hot Node. If not, see <https://www.gnu.org/licenses/>.
#
# END GPL LICENSE BLOCK #####


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