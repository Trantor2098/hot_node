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

from . import utils, file, props_py, history, i18n, gui


# poll parameters
allow_tex_save = False


def select_pack(props, dst_pack: props_py.Pack):
    # to escaping overwrite 
    props_py.gl_pack_selected = dst_pack
    props_py.skip_pack_rename_callback = True
    pack_name = dst_pack.name if dst_pack is not None else ""
    props.pack_selected_name = pack_name
    props_py.skip_pack_rename_callback = False
    # load presets in the newly selected pack
    presets = props.presets
    props.preset_selected = 0
    presets.clear()
    file.select_pack(dst_pack)
    # if pack is None, means there is no pack, dont read any preset and keep pack as None, the ops will be grayed out because they will detect whether pack is None.
    if dst_pack is not None:
        preset_names, tree_types = file.read_presets()
        preset_num = len(preset_names)
        props_py.skip_preset_rename_callback = True
        for i in range(preset_num):
            name = preset_names[i]
            type = tree_types.get(name, None)
            if type is None:
                preset_names, tree_types = file.refresh_pack_meta(pack_name)
                select_pack(props, dst_pack)
                break
            presets.add()
            presets[i].name = name
            presets[i].type = type
        props_py.skip_preset_rename_callback = False


# Callbacks of hot node props updating
def _node_preset_type_update(self, context):
    pass


def _node_preset_name_update(self, context):
    # callback when user changed the preset name, but skip if we are moving position / creating new preset
    if props_py.skip_preset_rename_callback:
        return
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    new_full_name = presets[preset_selected_idx].name
    old_name = props_py.gl_preset_selected
    # we should skip callback or we will fall into loops
    if old_name == new_full_name:
        return
    if new_full_name == "":
        props_py.skip_preset_rename_callback = True
        presets[preset_selected_idx].name = old_name
        props_py.skip_preset_rename_callback = False
        return
    # checkuser renaming and do rename
    ensured_new_full_name = utils.ensure_unique_name_dot(new_full_name, preset_selected_idx, presets)
    props_py.skip_preset_rename_callback = True
    presets[preset_selected_idx].name = ensured_new_full_name
    props_py.skip_preset_rename_callback = False
    file.rename_preset(old_name, ensured_new_full_name)
    history.Step(context, i18n.msg["Rename Preset"], refresh=False,
                 undo_callback=history.rename_preset_callback, redo_callback=history.rename_preset_callback,
                 undo_callback_param=(new_full_name, old_name), redo_callback_param=(old_name, new_full_name))
    props_py.gl_preset_selected = ensured_new_full_name


def _preset_select_update(self, context):
    if props_py.skip_preset_selected_callback:
        return
    global allow_tex_save
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    if len(presets) > 0:
        props_py.gl_preset_selected = presets[preset_selected_idx].name
    else:
        props_py.gl_preset_selected = ""
    allow_tex_save = False
    

def _pack_selected_name_update(self, context):
    if props_py.skip_pack_rename_callback:
        return
    # callback when *PACK NAME CHANGED BY USER*. Switch packs will also call this.
    props = context.scene.hot_node_props
    new_name = props.pack_selected_name
    if props_py.gl_pack_selected is None:
        props_py.skip_pack_rename_callback = True
        props.pack_selected_name = ""
        props_py.skip_pack_rename_callback = False
        return
    if props_py.gl_pack_selected.name == new_name:
        return
    if new_name == "":
        props_py.skip_pack_rename_callback = True
        props.pack_selected_name = props_py.gl_pack_selected.name
        props_py.skip_pack_rename_callback = False
        return
    
    if len(props_py.gl_packs) > 0:
        old_name = props_py.gl_pack_selected.name
        file.rename_pack(old_name, new_name)
        props_py.gl_pack_selected = props_py.gl_packs[new_name]
        gui.ensure_existing_pack_menu(new_name)
        history.Step(context, i18n.msg["Rename Pack"],
                     undo_callback=(history.rename_pack_callback, history.select_preset_callback), 
                     redo_callback=(history.rename_pack_callback, history.select_preset_callback),
                     undo_callback_param=((new_name, old_name), props.preset_selected), 
                     redo_callback_param=((old_name, new_name), props.preset_selected))
    else:
        props_py.gl_pack_selected = None
        props_py.skip_pack_rename_callback = True
        props.pack_selected_name = ""
        props_py.skip_pack_rename_callback = False
    
        
        
def _fast_create_preset_name_update(self, context):
    if props_py.skip_fast_create_preset_name_callback:
        return
    props = context.scene.hot_node_props
    presets = props.presets
    fast_name = props.fast_create_preset_name
    if fast_name != "" and props_py.gl_pack_selected is not None:
        # This is the same with what we do in operators.py
        ensured_fast_name = utils.ensure_unique_name_dot(fast_name, -1, presets)
        edit_tree = context.space_data.edit_tree
        step = history.Step(context, i18n.msg["Create Preset"], 
                            changed_paths=[file.pack_selected_meta_path],
                            undo_callback=history.select_preset_callback, redo_callback=history.select_preset_callback)
            
        presets.add()
        # select newly created set
        length = len(presets)
        preset_selected_idx = length - 1
        props.preset_selected = preset_selected_idx
        step.redo_callback_param = preset_selected_idx
        # set type
        presets[preset_selected_idx].type = edit_tree.bl_idname
        props_py.skip_preset_rename_callback = True
        presets[preset_selected_idx].name = ensured_fast_name
        props_py.gl_preset_selected = ensured_fast_name
        props_py.skip_preset_rename_callback = False
        
        # try to save current selected nodes. In node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
        from . import node_parser
        cpreset, states = node_parser.parse_node_preset(edit_tree)
        cpreset = node_parser.set_preset_data(ensured_fast_name, props_py.gl_pack_selected.name)
        preset_path = file.create_preset(ensured_fast_name, cpreset)
        step.created_paths = [preset_path]
        
    props_py.skip_fast_create_preset_name_callback = True
    props.fast_create_preset_name = ""
    props_py.skip_fast_create_preset_name_callback = False
    
    
def _step_checker_update(self, context):
    if props_py.skip_step_checker_update:
        return
    history.step_checker_cache = context.scene.hot_node_props.step_checker
        


class HotNodePreset(bpy.types.PropertyGroup):
    '''Info class of node preset, will be used for UI, OPS'''
    name: StringProperty(
        name='Node Preset',
        default='Preset',
        update=_node_preset_name_update
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
        update=_node_preset_type_update
    ) # type: ignore
    
    
class HotNodeProps(bpy.types.PropertyGroup):
    '''Singleton class! These are Hot Node's properties that will be registed to blender, used for UI, OPS.'''
    presets: CollectionProperty(
        name="Node Presets",
        type=HotNodePreset
    ) # type: ignore

    preset_selected: IntProperty(
        name=i18n.msg["Preset"],
        update=_preset_select_update
    ) # type: ignore
    
    # for user to change pack name.
    pack_selected_name: StringProperty(
        name=i18n.msg["Selected Pack"],
        description=i18n.msg["desc_selected_pack"],
        default=props_py.get_gl_pack_selected_name(),
        update=_pack_selected_name_update
    ) # type: ignore
    
    # for user to fast create preset by Shift A.
    fast_create_preset_name: StringProperty(
        name=i18n.msg["Fast Create Preset Name"],
        default="",
        description=i18n.msg["desc_fast_create_preset_name"],
        update=_fast_create_preset_name_update
    ) # type: ignore
    
    tex_preset_mode: EnumProperty(
        name=i18n.msg["Texture Loading Mode"],
        description=i18n.msg["desc_tex_loading_mode"],
        # options=set(),
        items=[
            ('AUTO', "Auto", i18n.msg["desc_tex_mode_auto"]),
            ('SIMILAR', i18n.msg["Similar Name"], i18n.msg["desc_tex_mode_similar_name"]),
            ('KEYWORD', i18n.msg["Name Key"], i18n.msg["desc_tex_mode_keyword"]),
            ('FIXED_PATH', i18n.msg["Fixed Path"], i18n.msg["desc_tex_mode_fixed_path"]),
            ('STAY_EMPTY', i18n.msg["Stay Empty"], i18n.msg["desc_tex_mode_stay_empty"]),
        ]
    ) # type: ignore
    
    tex_key: StringProperty(
        name=i18n.msg["Texture Key"],
        description=i18n.msg["desc_tex_key"],
        default=""
    ) # type: ignore
    
    compare_tolerance: FloatProperty(
        name=i18n.msg["Compare Tolerance"],
        description=i18n.msg["desc_compare_tolerance"],
        default=0.5,
        min = 0.01,
        max = 0.99,
        step=1
    ) # type: ignore
    
    tex_dir_path: StringProperty(
        name=i18n.msg["Texture Directory"],
        description=i18n.msg["desc_texture_directory"],
        default="",
        subtype='DIR_PATH'
    ) # type: ignore
    
    step_checker: BoolProperty(
        name="Undo Redo Checker",
        default=True,
        update=_step_checker_update,
    ) # type: ignore
    

classes = (
    HotNodePreset,
    HotNodeProps,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.hot_node_props = bpy.props.PointerProperty(
        name="Hot Node Prop Group",
        type=HotNodeProps
    ) # type: ignore
    

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        
    if hasattr(bpy.types.Scene, "hot_node_props"):
        del bpy.types.Scene.hot_node_props