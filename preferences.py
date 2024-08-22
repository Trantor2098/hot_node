import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty

from . import props_py


class ExampleAddonPreferences(AddonPreferences):
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
    bpy.utils.register_class(ExampleAddonPreferences)


def unregister():
    bpy.utils.unregister_class(ExampleAddonPreferences)