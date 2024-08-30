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


class HotNodePreferences(AddonPreferences):
    bl_idname = __package__

    overwrite_tree_io: BoolProperty(
        name='Overwrite Tree IO',
        description="Overwrite node tree interface (IO sockets, panels) if the existing one is not capatibale with the one in preset. Note: If open, your original node tree interface will be changed and the links to them will be disappeared",
        default=False,
    ) # type: ignore
    
    in_one_menu: BoolProperty(
        name='In One Menu',
        description="Put packs into one menu rather than listing all of them on the node add menu",
        default=False,
    ) # type: ignore

    extra_confirm: BoolProperty(
        name='Extra Confirmation',
        description="Popup a confirmation window when save & delete preset or packs, since it can't be undo",
        default=False,
    ) # type: ignore
    
    tex_default_mode: EnumProperty(
        name="Texture Default Mode",
        description="Default texture saving mode when save the preset",
        # options=set(),
        items=[
            ('AUTO', "Auto", "Try to open textures with the order Name Compare > Fixed Path > Stay Empty"),
            ('SIMILAR', "Similar", "Compare the texture names and open the best mattched one from user folder, stay empty when failed"),
            ('FIXED_PATH', "Fixed Path", "Try to open this texture with it's current path, keep empty if failed"),
            ('STAY_EMPTY', "Stay Empty", "Don't load texture for this texture node"),
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