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
from bpy.types import Scene, PropertyGroup
from bpy.props import StringProperty, EnumProperty, CollectionProperty, IntProperty, BoolProperty, FloatProperty

from . import utils, file


# NOTE selected preset is saved by blender property, and the python string is a mirror. But pack is saved by python string.

packs = []
# for script to get current pack.
pack_selected = ""
# only for checking rename as a name cache, wont be used to get preset
preset_selected = ""

# poll parameters
allow_tex_save = False

# XXX to escape invoke rename update when create preset. ugly but works.
skip_update = False

# for json file indent
# indent = 1


# XXX For now i havent find a way to init preset collection before user making a explicit UI / OPS action...
def init():
    global packs
    file.init_root_meta()
    packs = file.read_packs()
    
    
def read_packs():
    global packs
    packs = file.read_packs()


def rename_pack(old_name, new_name):
    global packs
    global pack_selected
    idx = packs.index(old_name)
    packs[idx] = new_name
    pack_selected = new_name
    file.rename_pack(old_name, new_name)


def node_preset_type_update(self, context):
    pass


def node_preset_name_update(self, context):
    # callback when user changed the preset name, but skip if we are moving position / creating new preset
    if skip_update:
        return
    global preset_selected
    scene = context.scene
    presets = scene.hot_node_presets
    preset_selected_idx = scene.hot_node_preset_selected
    new_full_name = presets[preset_selected_idx].name
    if preset_selected != new_full_name:
        ensured_new_full_name = utils.ensure_unique_name_dot(new_full_name, preset_selected_idx, presets)
        if ensured_new_full_name != new_full_name:
            presets[preset_selected_idx].name = ensured_new_full_name
        file.rename_preset(preset_selected, ensured_new_full_name)
        preset_selected = ensured_new_full_name


def node_preset_select_update(self, context):
    if skip_update:
        return
    global preset_selected, allow_tex_save
    scene = context.scene
    presets = scene.hot_node_presets
    preset_selected_idx = scene.hot_node_preset_selected
    if len(presets) > 0:
        preset_selected = presets[preset_selected_idx].name
    else:
        preset_selected = ""
    allow_tex_save = False
    

def node_preset_active_update(self, context):
    pass


def node_pack_active_update(self, context):
    pass


def node_pack_selected_name_update(self, context):
    # callback when *PACK NAME CHANGED BY USER*. Switch packs will also call this.
    global pack_selected
    scene = context.scene
    old_name = pack_selected
    new_name = scene.hot_node_pack_selected_name
    if old_name == new_name:
        return
    if len(packs) > 0:
        rename_pack(old_name, new_name)
    else:
        scene.hot_node_pack_selected_name = ''
        
        
# def reduce_file_size_update(self, context):
#     global indent
#     if context.scene.hot_node_reduce_file_size:
#         indent = None
#     else:
#         indent = 1


class NodePreset(PropertyGroup):
    # This class stores the presets infos in a pack
    name: StringProperty(
        name='Node Preset',
        default='Preset',
        update=node_preset_name_update
    ) # type: ignore

    type: EnumProperty(
        name="Type",
        # in blender specification, enum item should be in upper, but just use the bl_idname is more convenient
        items=[
            ('ShaderNodeTree', 'Shader Nodes', 'Presets that can be applied to shader node tree'),
            ('GeometryNodeTree', 'Geometry Nodes', 'Presets that can be applied to geometry node tree'),
            ('CompositorNodeTree', 'Compositing Nodes', 'Presets that can be applied to compositing node tree'),
            ('TextureNodeTree', 'Texture Nodes', 'Presets that can be applied to texture node tree'),
            ('UNIVERSAL', 'Universal Nodes', 'Presets that can be applied to all kinds of node tree')
        ],
        default='ShaderNodeTree',
        update=node_preset_type_update
    ) # type: ignore


classes = (
    NodePreset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    init()
    
    Scene.hot_node_presets = CollectionProperty(
        name='Node Presets',
        type=NodePreset
    )

    Scene.hot_node_preset_selected = IntProperty(
        name='Selected Preset',
        update=node_preset_select_update
    )

    Scene.hot_node_preset_active = IntProperty(
        update=node_preset_active_update
    )

    # for user to change pack name.
    Scene.hot_node_pack_selected_name = StringProperty(
        name='',
        default=pack_selected,
        update=node_pack_selected_name_update
    )
    
    Scene.hot_node_tex_preset_mode = EnumProperty(
        name="Texture Preset Mode",
        description="Texture saving mode",
        # options=set(),
        items=[
            ('AUTO', "Auto", "Try to open textures with the order Name Compare > Fixed Path > Stay Empty"),
            ('COMPARE', "Compare", "Compare the texture names and open the best mattched one from user folder, stay empty when failed"),
            ('KEYWORD', "Keys", "Using keywords to match texture in an user selected folder"),
            ('FIXED_PATH', "Fixed Path", "Try to open this texture with it's current path, keep empty if failed"),
            ('STAY_EMPTY', "Stay Empty", "Don't load texture for this texture node"),
        ]
    )
    
    Scene.hot_node_tex_default_mode = EnumProperty(
        name="Texture Default Mode",
        description="Default texture saving mode when save the preset",
        # options=set(),
        items=[
            ('AUTO', "Auto", "Try to open textures with the order Name Compare > Fixed Path > Stay Empty"),
            ('COMPARE', "Compare", "Compare the texture names and open the best mattched one from user folder, stay empty when failed"),
            ('FIXED_PATH', "Fixed Path", "Try to open this texture with it's current path, keep empty if failed"),
            ('STAY_EMPTY', "Stay Empty", "Don't load texture for this texture node"),
        ]
    )
    
    Scene.hot_node_tex_key = StringProperty(
        name="Texture Key",
        description="When open texture, try to find best matched tex with keys. Use / to separate multiple keys",
        default=""
    )
    
    Scene.hot_node_compare_tolerance = FloatProperty(
        name="Compare Tolerance",
        description="The tolerance of the texture name comparation, higher means that more dissimilar textures can pass the comparation rather than stay empty. Default 0.50 as a moderate tolerance",
        default=0.5,
        min = 0.01,
        max = 0.99,
        step=1
    )
    
    Scene.hot_node_tex_dir_path = StringProperty(
        name="Texture Directory",
        description="Searching textures in this directory when apply preset",
        default="",
        subtype='DIR_PATH'
    )
    
    Scene.hot_node_overwrite_tree_io = BoolProperty(
        name='Overwrite Tree IO',
        description="Overwrite node tree interface (IO sockets, panels) if the existing one is not capatibale with the one in preset. Note: If open, your original node tree interface will be changed and the links to them will be disappeared",
        default=False,
    )

    Scene.hot_node_confirm = BoolProperty(
        name='Extra Confirmation',
        description="Popup a confirmation window when save & delete preset or packs, since it can't be undo",
        default=False,
    )
    
    # XXX Not sure should i add this feature...
    # Scene.hot_node_reduce_file_size = BoolProperty(
    #     name='Reduce Data File Size',
    #     description="Reduce preset data file size by about 1/3, by removing line feeds in the data files. The data may be unreadable.",
    #     default=False,
    #     update=reduce_file_size_update
    # )
    
    # NOTE Deprecated, now by default we compare two ngs
    # Scene.hot_node_ng_reuse = BoolProperty(
    #     name='Try Re-use Node Group',
    #     description="When apply a preset, compare and re-use the totally same existing node group, rather than create a copy with an unique name",
    #     default=True
    # )
    
    # NOTE Deprecated, now by default we compare two images
    # Scene.hot_node_tex_reuse = BoolProperty(
    #     name='Try Re-use Texture',
    #     description="When apply a preset, use the existing texture with the same name, rather than load a copy with an unique name",
    #     default=True
    # )

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


    del Scene.hot_node_presets
    del Scene.hot_node_preset_selected
    del Scene.hot_node_preset_active
    del Scene.hot_node_pack_selected_name
    del Scene.hot_node_confirm
    del Scene.hot_node_tex_preset_mode
    del Scene.hot_node_tex_key
    del Scene.hot_node_compare_tolerance
    del Scene.hot_node_tex_dir_path
    del Scene.hot_node_tex_default_mode
    del Scene.hot_node_overwrite_tree_io