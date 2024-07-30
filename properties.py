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
from bpy.props import StringProperty, EnumProperty, CollectionProperty, IntProperty, BoolProperty, FloatProperty

from . import utils, file


# NOTE selected preset is saved by blender property, and the python string is a mirror. But pack is saved by python string.

# packs will be loaded once the blender open
packs = []
# for script to get current pack.
pack_selected = ""
# only for checking rename as a name cache, wont be used to get preset
preset_selected = ""

# poll parameters
allow_tex_save = False
# to escape invoke rename update when create preset. ugly but works. for cases like select pack, add preset
skip_rename_callback = False

# for json file indent
# indent = 1


# Set function for global packs.
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


# Callbacks of hot node props updating
def node_preset_type_update(self, context):
    pass


def node_preset_name_update(self, context):
    # callback when user changed the preset name, but skip if we are moving position / creating new preset
    global skip_rename_callback
    if skip_rename_callback:
        return
    global preset_selected
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    new_full_name = presets[preset_selected_idx].name
    if preset_selected != new_full_name:
        # this second if is for checking user renaming
        ensured_new_full_name = utils.ensure_unique_name_dot(new_full_name, preset_selected_idx, presets)
        if ensured_new_full_name != new_full_name:
            # XXX should we skip update again? will the callback be invoked by callback itself?
            skip_rename_callback = True
            presets[preset_selected_idx].name = ensured_new_full_name
            skip_rename_callback = False
        file.rename_preset(preset_selected, ensured_new_full_name)
        preset_selected = ensured_new_full_name


def node_preset_select_update(self, context):
    if skip_rename_callback:
        return
    global preset_selected, allow_tex_save
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    if len(presets) > 0:
        preset_selected = presets[preset_selected_idx].name
    else:
        preset_selected = ""
    allow_tex_save = False
    

def pack_selected_name_update(self, context):
    # callback when *PACK NAME CHANGED BY USER*. Switch packs will also call this.
    global pack_selected
    props = context.scene.hot_node_props
    old_name = pack_selected
    new_name = props.pack_selected_name
    if old_name == new_name:
        return
    if len(packs) > 0:
        rename_pack(old_name, new_name)
    else:
        props.pack_selected_name = ''
        
        
def fast_create_preset_name_update(self, context):
    global skip_rename_callback
    global preset_selected
    props = context.scene.hot_node_props
    presets = props.presets
    fast_name = props.fast_create_preset_name
    if fast_name == "":
        return
    ensured_fast_name = utils.ensure_unique_name_dot(fast_name, -1, presets)
    edit_tree = context.space_data.edit_tree
        
    presets.add()
    # select newly created set
    length = len(presets)
    preset_selected_idx = length - 1
    props.preset_selected = preset_selected_idx
    # set type
    presets[preset_selected_idx].type = edit_tree.bl_idname
    # XXX this is ugly but works... for escaping renaming the exist preset and overwriting it
    skip_rename_callback = True
    presets[preset_selected_idx].name = ensured_fast_name
    preset_selected = ensured_fast_name
    skip_rename_callback = False
    
    # try to save current selected nodes. In node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
    from . import node_parser
    node_parser.parse_node_preset(edit_tree)
    cpreset = node_parser.set_preset_data(ensured_fast_name, pack_selected)
    file.create_preset(ensured_fast_name, cpreset)
    
    props.fast_create_preset_name = ""


class HotNodePreset(bpy.types.PropertyGroup):
    '''Info class of node preset, will be used for UI, OPS'''
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
    
    
class HotNodeProps(bpy.types.PropertyGroup):
    '''Singleton class! Hot Node's properties that will be registed to blender, used for UI, OPS.'''
    presets: CollectionProperty(
        name="Node Presets",
        type=HotNodePreset
    ) # type: ignore

    preset_selected: IntProperty(
        name="Selected Node Preset",
        update=node_preset_select_update
    ) # type: ignore
    
    # for user to change pack name.
    pack_selected_name: StringProperty(
        name="Selected Pack",
        description="Selected pack's name",
        default=pack_selected,
        update=pack_selected_name_update
    ) # type: ignore
    
    # for user to fast create preset by Shift A.
    fast_create_preset_name: StringProperty(
        name="Fast Create Preset Name",
        default="",
        description="Create preset with current selected nodes by this name",
        update=fast_create_preset_name_update
    ) # type: ignore
    
    tex_preset_mode: EnumProperty(
        name="Texture Preset Mode",
        description="Texture saving mode",
        # options=set(),
        items=[
            ('AUTO', "Auto", "Try to open textures with the order Name Compare > Fixed Path > Stay Empty"),
            ('SIMILAR', "Similar", "Compare the texture names and open the best mattched one from user folder, stay empty when failed"),
            ('KEYWORD', "Keys", "Using keywords to match texture in an user selected folder"),
            ('FIXED_PATH', "Fixed Path", "Try to open this texture with it's current path, keep empty if failed"),
            ('STAY_EMPTY', "Stay Empty", "Don't load texture for this texture node"),
        ]
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
    
    tex_key: StringProperty(
        name="Texture Key",
        description="When open texture, try to find best matched tex with keys. Use / to separate multiple keys",
        default=""
    ) # type: ignore
    
    compare_tolerance: FloatProperty(
        name="Compare Tolerance",
        description="The tolerance of the texture name comparation, higher means that more dissimilar textures can pass the comparation rather than stay empty. Default 0.50 as a moderate tolerance",
        default=0.5,
        min = 0.01,
        max = 0.99,
        step=1
    ) # type: ignore
    
    tex_dir_path: StringProperty(
        name="Texture Directory",
        description="Searching textures in this directory when apply preset",
        default="",
        subtype='DIR_PATH'
    ) # type: ignore
    
    overwrite_tree_io: BoolProperty(
        name='Overwrite Tree IO',
        description="Overwrite node tree interface (IO sockets, panels) if the existing one is not capatibale with the one in preset. Note: If open, your original node tree interface will be changed and the links to them will be disappeared",
        default=False,
    ) # type: ignore

    extra_confirm: BoolProperty(
        name='Extra Confirmation',
        description="Popup a confirmation window when save & delete preset or packs, since it can't be undo",
        default=False,
    ) # type: ignore


classes = (
    HotNodePreset,
    HotNodeProps,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    read_packs()
    
    bpy.types.Scene.hot_node_props = bpy.props.PointerProperty(
        name='Hot Node Prop Group',
        type=HotNodeProps
    ) # type: ignore
    

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.hot_node_props