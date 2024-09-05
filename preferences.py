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
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty

from . import i18n


class HotNodePreferences(AddonPreferences):
    bl_idname = __package__

    overwrite_tree_io: BoolProperty(
        name=i18n.msg["Overwrite Tree I/O"],
        description=i18n.msg["desc_overwrite_tree_io"],
        default=False,
    ) # type: ignore
    
    in_one_menu: BoolProperty(
        name=i18n.msg["In One Menu"],
        description=i18n.msg["desc_in_one_menu"],
        default=False,
    ) # type: ignore

    extra_confirm: BoolProperty(
        name=i18n.msg["Extra Confirmation"],
        description=i18n.msg["desc_extra_confirmation"],
        default=False,
    ) # type: ignore
    
    tex_default_mode: EnumProperty(
        name=i18n.msg["Texture Default Mode"],
        description=i18n.msg["desc_tex_default_mode"],
        # options=set(),
        items=[
            ('AUTO', "Auto", i18n.msg["desc_tex_mode_auto"]),
            ('SIMILAR', i18n.msg["Similar Name"], i18n.msg["desc_tex_mode_similar_name"]),
            ('FIXED_PATH', i18n.msg["Fixed Path"], i18n.msg["desc_tex_mode_fixed_path"]),
            ('STAY_EMPTY', i18n.msg["Stay Empty"], i18n.msg["desc_tex_mode_stay_empty"]),
        ]
    ) # type: ignore

    # def draw(self, context):
    #     layout = self.layout
    #     layout.label(text="This is a preferences view for our add-on")
    #     layout.prop(self, "overwrite_tree_io")
    #     layout.prop(self, "in_one_menu")
    #     layout.prop(self, "extra_confirm")
        
        
def register():
    bpy.utils.register_class(HotNodePreferences)


def unregister():
    try:
        bpy.utils.unregister_class(HotNodePreferences)
    except:
        pass