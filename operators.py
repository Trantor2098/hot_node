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
from bpy.types import Operator
from bpy.props import StringProperty

from . import node_setter, props_bl, props_py, utils, file, node_parser, gui, sync, history, i18n
            
      
def _poll_preset_ops(context):
    return props_py.gl_pack_selected is not None and context.space_data.edit_tree is not None


def _exec_pop_confirm_if_need(ops, context, event):
    if context.preferences.addons[__package__].preferences.extra_confirm:
        wm = context.window_manager
        return wm.invoke_confirm(ops, event)
    else:
        return ops.execute(context)


# Operator Functions
def preset_create(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    step = history.Step(context, i18n.msg["Create Preset"], 
                        changed_paths=[file.pack_selected_meta_path],
                        undo_callback=history.select_preset_callback, redo_callback=history.select_preset_callback)
    props = context.scene.hot_node_props
    presets = props.presets
    edit_tree = context.space_data.edit_tree
    step.undo_callback_param = props.preset_selected
    # escape rename. The default name is "Preset"... Do this first to check sync
    # TODO if there is only a ng, set the ng name as the preset name
    # try to save current selected nodes. In node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
    cpreset, states = node_parser.parse_node_preset(edit_tree)
    
    # for now states means single node's name, we may extend it in the future
    if states is None:
        new_full_name = utils.ensure_unique_name_dot(i18n.msg["Preset"], -1, presets)
    else:
        new_full_name = utils.ensure_unique_name_dot(states, -1, presets)
    cpreset = node_parser.set_preset_data(new_full_name, props_py.gl_preset_selected)
    preset_path = file.create_preset(new_full_name, cpreset)
    step.created_paths = [preset_path]
    
    presets.add()
    # select newly created set
    length = len(presets)
    preset_selected_idx = length - 1
    props.preset_selected = preset_selected_idx
    step.redo_callback_param = preset_selected_idx
    # set type
    presets[preset_selected_idx].type = edit_tree.bl_idname
    props_py.skip_preset_rename_callback = True
    presets[preset_selected_idx].name = new_full_name
    props_py.gl_preset_selected = new_full_name
    props_py.skip_preset_rename_callback = False
    props_bl.allow_tex_save = True
    # ops.report(type={'INFO'}, message=f"Saved selected nodes as \"{new_full_name}\".")

    return {'FINISHED'}


def preset_delete(ops: Operator, context):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    
    props = context.scene.hot_node_props
    presets = props.presets

    length = len(presets)
    
    if length > 0:
        preset_selected_idx = props.preset_selected
        preset_name = presets[preset_selected_idx].name
        preset_path = file.get_preset_path(preset_name)
        step = history.Step(context, i18n.msg["Delete Preset"], 
                            deleted_paths=[preset_path], changed_paths=[file.pack_selected_meta_path],
                            undo_callback=history.select_preset_callback, redo_callback=history.select_preset_callback,
                            undo_callback_param=preset_selected_idx)
        presets.remove(preset_selected_idx)
        if preset_selected_idx == length - 1:
            props.preset_selected -= 1
        step.redo_callback_param = props.preset_selected
        
        file.delete_preset(preset_name)
    else:
        return {'CANCELLED'}

    return {'FINISHED'}


def preset_clear(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
            return {'CANCELLED'}
    pack = props_py.gl_pack_selected
    props = context.scene.hot_node_props
    history.Step(context, i18n.msg["Create Preset"], 
                 deleted_paths=[file.pack_selected_path])
    file.clear_preset(pack.name)
    props.presets.clear()
    ops.report({'INFO'}, i18n.msg["rpt_preset_clear_success"].format(pack_name=pack.name))

    return {'FINISHED'}


def _preset_move_to(selected_idx, dst_idx, presets):
    preset = presets[selected_idx]
    name, type = preset.name, preset.type
    if selected_idx > dst_idx:
        for i in range(selected_idx - dst_idx):
            presets[selected_idx - i].name = presets[selected_idx - i - 1].name
            presets[selected_idx - i].type = presets[selected_idx - i - 1].type
    elif selected_idx < dst_idx:
        for i in range(selected_idx, dst_idx):
            presets[i].name = presets[i + 1].name
            presets[i].type = presets[i + 1].type
    else:
        return
    presets[dst_idx].name = name
    presets[dst_idx].type = type


def preset_move(ops: Operator, context: bpy.types.Context, direction):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    
    length = len(presets)
    if length < 2:
        return {'FINISHED'}
    
    step = history.Step(context, i18n.msg["Move Preset"], refresh=False,
                        changed_paths=[file.pack_selected_meta_path])
    
    props_py.skip_preset_rename_callback = True
    props_py.skip_preset_selected_callback = True

    reorder = True
    if direction == 'UP':
        if preset_selected_idx == 0:
            dst_idx = length - 1
        else:
            dst_idx = preset_selected_idx - 1
            reorder = False
    elif direction == 'DOWN':
        if preset_selected_idx == length - 1:
            dst_idx = 0
        else:
            dst_idx = preset_selected_idx + 1
            reorder = False
    elif direction == 'TOP':
        dst_idx = 0
    elif direction == 'BOTTOM':
        dst_idx = length - 1
        
    _preset_move_to(preset_selected_idx, dst_idx, presets)
    # step.undo_callback_param = (dst_idx, preset_selected_idx)
    # step.redo_callback_param = (preset_selected_idx, dst_idx)

    # reoder means creating a new list to store the new order, which brings more cost
    if reorder:
        preset_names = []
        for i in range(len(presets)):
            preset_names.append(presets[i].name)
        file.reorder_preset_meta(preset_names)
    # exchange brings less cost
    else:
        file.exchange_order_preset_meta(dst_idx, preset_selected_idx)
    props.preset_selected = dst_idx
    
    props_py.skip_preset_selected_callback = False
    props_py.skip_preset_rename_callback = False

    return {'FINISHED'}


def preset_save(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
            return {'CANCELLED'}
    pack = props_py.gl_pack_selected
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    preset_selected = presets[preset_selected_idx]
    preset_name = preset_selected.name
    edit_tree = context.space_data.edit_tree
    
    presets[preset_selected_idx].type = edit_tree.bl_idname
    
    pack_meta_path = file.get_pack_selected_meta_path()
    preset_path = file.get_preset_path(preset_name)
    history.Step(context, i18n.msg["Save Preset"], 
                 changed_paths=[pack_meta_path, preset_path],
                 undo_callback=history.select_preset_callback, redo_callback=history.select_preset_callback,
                 undo_callback_param=preset_selected_idx, redo_callback_param=preset_selected_idx)
    
    # in node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
    cpreset, states = node_parser.parse_node_preset(edit_tree)
    cpreset = node_parser.set_preset_data(preset_name, pack.name)
    file.update_preset(preset_name, cpreset)
    
    props_bl.allow_tex_save = True
    # ops.report(type={'INFO'}, message=f"Saved selected nodes to \"{preset_name}\".")

    return {'FINISHED'}
    
    
def nodes_add(ops: Operator, context: bpy.types.Context, preset_name, pack_name, tree_type, user_report=True):
    '''Add nodes to the node tree. This function uses preset_name to find preset json and apply it.'''
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    if preset_name == "":
        preset = presets[preset_selected_idx]
        preset_name = preset.name
        tree_type = preset.type
    
    edit_tree = context.space_data.edit_tree
    edit_tree_type = edit_tree.bl_idname
    if tree_type != edit_tree_type:
        ops.report({'WARNING'}, i18n.msg["rpt_nodes_add_fail_tree"].format(tree_type=tree_type, edit_tree_type=edit_tree_type))
        return {'CANCELLED'}
    
    # adds the nodes
    failed_tex_num= node_setter.apply_preset(context, preset_name, pack_name=pack_name, apply_offset=True)
    
    if failed_tex_num > 0:
        ops.report({'INFO'}, i18n.msg["rpt_nodes_add_fail_tex"].format(failed_tex_num=failed_tex_num))
        
    # call translate ops for moving nodes. escaping select NodeFrames because they will cause bugs in move ops. reselect them later.
    selected_node_frames = []
    for node in edit_tree.nodes:
        if node.select and node.bl_idname == "NodeFrame":
            selected_node_frames.append(node)
            node.select = False
            
    bpy.ops.node.translate_attach_remove_on_cancel('INVOKE_DEFAULT')
        
    for node in selected_node_frames:
        node.select = True
        
    return {'FINISHED'}
    
    
def texture_save(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    pack = props_py.gl_pack_selected
    props = context.scene.hot_node_props
    presets = props.presets
    preset_selected_idx = props.preset_selected
    preset_selected = presets[preset_selected_idx]
    preset_name = preset_selected.name
    
    pack_meta_path = file.get_pack_selected_meta_path()
    preset_path = file.get_preset_path(preset_name)
    
    open_mode = props.tex_preset_mode
    tex_key = props.tex_key

    cpreset = node_parser.set_texture_rule(context.space_data.edit_tree, preset_name, pack.name, open_mode, tex_key)
    if not isinstance(cpreset, dict):
        if cpreset == 'EXCEED':
            ops.report(type={'WARNING'}, message=i18n.msg["rpt_tex_save_fail_exceed"])
        elif cpreset == 'NO_NODE_SELECTED':
            ops.report(type={'WARNING'}, message=i18n.msg["rpt_tex_save_fail_no_node"])
        elif cpreset == 'NOT_TEX_NODE':
            ops.report(type={'WARNING'}, message=i18n.msg["rpt_tex_save_fail_not_tex_node"])
        elif cpreset == 'NOT_SAVED_NODE':
            ops.report(type={'WARNING'}, message=i18n.msg["rpt_tex_save_fail_not_saved_node"])
        elif cpreset == 'NOT_PRESET_SELECTED':
            ops.report(type={'WARNING'}, message=i18n.msg["rpt_tex_save_fail_not_preset_selected"])
        else:
            print(cpreset)
            ops.report(type={'WARNING'}, message="Failed to save texture settings")
        return {'CANCELLED'}
    else:
        history.Step(context, i18n.msg["Save Texture"], 
                     changed_paths=[pack_meta_path, preset_path])
        file.update_preset(preset_name, cpreset)
        ops.report({'INFO'}, i18n.msg["rpt_tex_save_success"])
    
    return {'FINISHED'}
    
    
def pack_create(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    old_pack_name = props_py.get_gl_pack_selected_name()
    new_full_name = utils.ensure_unique_name(i18n.msg["Pack"], -1, list(props_py.gl_packs.keys()))

    pack_path = file.create_pack(new_full_name)
    props_bl.select_pack(context.scene.hot_node_props, props_py.gl_packs[new_full_name])
    gui.ensure_existing_pack_menu(new_full_name)
    step = history.Step(context, i18n.msg["Create Pack"], 
                        created_paths=[pack_path],
                        undo_callback=history.select_pack_callback, redo_callback=history.select_pack_callback,
                        undo_callback_param=old_pack_name, redo_callback_param=new_full_name)
    return {'FINISHED'}


def pack_delete(ops: Operator, context: bpy.types.Context):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    packs = props_py.gl_packs
    pack_name = props_py.gl_pack_selected.name
    pack_names = list(packs.keys())
    pack_selected_idx = pack_names.index(pack_name)
    step = history.Step(context, i18n.msg["Delete Pack"], 
                        deleted_paths=[file.pack_selected_path],
                        undo_callback=history.select_pack_callback, redo_callback=history.select_pack_callback,
                        undo_callback_param=pack_name)
    
    
    del packs[pack_name]
    del pack_names[pack_selected_idx]
    file.delete_pack(pack_name)
    file.update_mtime_data()
    # note the length is the original length - 1
    length = len(packs)

    # select another pack if there is one
    if length > 0:
        # if deleted pack's idx is the last one, and not the only one, select the idx - 1
        if pack_selected_idx == length and pack_selected_idx > 0:
            pack_name = pack_names[pack_selected_idx - 1]
        # or let the next pack come up
        else:
            pack_name = pack_names[pack_selected_idx]
    # no pack last
    else:
        props_py.gl_pack_selected = None
        pack_name = ""
    step.redo_callback_param = pack_name

    props_bl.select_pack(context.scene.hot_node_props, props_py.gl_packs.get(pack_name, None))
    gui.ensure_existing_pack_menu(pack_name)
    return {'FINISHED'}
    
    
def pack_select(ops: Operator, context: bpy.types.Context, pack_name, push_step=True):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    if push_step:
        ori_pack_name = props_py.get_gl_pack_selected_name()
        step = history.Step(context, i18n.msg["Select Pack"],
                            undo_callback=history.select_pack_callback, redo_callback=history.select_pack_callback,
                            undo_callback_param=ori_pack_name)
    dst_pack = props_py.gl_packs.get(pack_name, None)
    props_bl.select_pack(context.scene.hot_node_props, dst_pack)
    if push_step:
        step.redo_callback_param = dst_pack.name if dst_pack is not None else ""
    return {'FINISHED'}
    
    
def pack_import(ops: Operator, context: bpy.types.Context, file_names, dir_path, is_recovering):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    
    file_num = len(file_names)
    # backslash_idx = self.filepath.rfind("\\")
    # dir_path = self.filepath[:backslash_idx]
    success_num = 0
    last_success_pack_name = ""
    imported_pack_paths = []
    
    # import every selected file
    for i in range(file_num):
        file_name = file_names[i].name
                
        file_path = "\\".join((dir_path, file_name))
        
        if file_name == ".zip" or file_name == "":
            ops.report({'ERROR'}, i18n.msg["rpt_pack_import_fail_empty_name"].format(file_name=file_name))
            continue
        
        # cull autosave suffix
        if is_recovering:
            pack_name = utils.get_string_between_words(file_name, None, ("_autosave_", "_deprecated_"))
            if pack_name is False:
                ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_not_auto"].format(file_name=file_name))
                continue
        else:
            pack_name = file_name[:-4]
            if pack_name in props_py.gl_packs.keys():
                ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_existed"].format(file_name=file_name, pack_name=pack_name))
                continue
            
        result = file.import_pack(file_path, pack_name)
        
        if result == 'META_LACK':
            ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_meta_lack"].format(file_name=file_name))
        elif result == 'INVALID_META':
            ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_meta_invalid"].format(file_name=file_name))
        elif result == 'OVER_SIZE':
            ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_oversize"].format(file_name=file_name))
        else:
            imported_pack_paths.append(result)
            last_success_pack_name = pack_name
            success_num += 1
            
    # count import infos
    if success_num > 0:
        current_pack_selected_name = props_py.get_gl_pack_selected_name()
        history.Step(context, i18n.msg["Import Pack"],
                     created_paths=imported_pack_paths,
                     undo_callback=history.select_pack_callback, redo_callback=history.select_pack_callback,
                     undo_callback_param=current_pack_selected_name, redo_callback_param=last_success_pack_name)
        sync.sync(context.scene.hot_node_props)
        props_bl.select_pack(context.scene.hot_node_props, props_py.gl_packs[last_success_pack_name])
        # sync() will ensure it
        # gui.ensure_existing_pack_menu(pack_name)
        if success_num == file_num:
            if is_recovering:
                if success_num > 1:
                    ops.report({'INFO'}, i18n.msg["rpt_pack_import_success_import_mul"].format(success_num=success_num))
                else:
                    ops.report({'INFO'}, i18n.msg["rpt_pack_import_success_recover"].format(pack_name=pack_name))
            else:
                if success_num > 1:
                    ops.report({'INFO'}, i18n.msg["rpt_pack_import_success_import_mul"].format(success_num=success_num))
                else:
                    ops.report({'INFO'}, i18n.msg["rpt_pack_import_success_import"].format(pack_name=pack_name))
        else:
            ops.report({'INFO'}, i18n.msg["rpt_pack_import_partly_success"].format(success_num=success_num, file_num=file_num))
    # XXX is this complete?
    elif file_num > 1:
        ops.report({'WARNING'}, i18n.msg["rpt_pack_import_fail_all"])
        return {'CANCELLED'}
        
    return {'FINISHED'}
    
    
def pack_export(ops: Operator, context: bpy.types.Context, file_path, file_name, unique_name=True):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    
    to_file_path = utils.ensure_has_suffix(file_path, ".zip")
    if file_name == ".zip" or file_name == "":
        ops.report({'ERROR'}, i18n.msg["rpt_pack_export_fail_empty"])
        return {'CANCELLED'}
        
    to_file_path = file.export_selected_pack(to_file_path, unique_name)
    ops.report({'INFO'}, i18n.msg["rpt_pack_export_success"].format(pack_name=props_py.gl_pack_selected.name, to_file_path=to_file_path))
    return {'FINISHED'}
    
    
def pack_export_all(ops: Operator, context: bpy.types.Context, dir_path):
    if not sync.ensure_sync(context, ops):
        return {'CANCELLED'}
    file.export_packs(props_py.gl_packs.keys(), dir_path)
        
    ops.report({'INFO'}, i18n.msg['rpt_pack_export_all_success'].format(dir_path=dir_path))
    return {'FINISHED'}
    

# Operators
class HOTNODE_OT_preset_create(Operator):
    bl_idname = "node.hot_node_preset_create"
    bl_label = i18n.msg["Create Preset"]
    bl_description = i18n.msg["desc_create_preset"]
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context)

    def execute(self, context):
        return preset_create(self, context)
    

class HOTNODE_OT_preset_delete(Operator):
    bl_idname = "node.hot_node_preset_delete"
    bl_label = i18n.msg["Delete Preset"]
    bl_description = i18n.msg["desc_delete_preset"]
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return props_py.gl_pack_selected != "" and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        return preset_delete(self, context)
    
    def invoke(self, context, event):
        return _exec_pop_confirm_if_need(self, context, event)
    

class HOTNODE_OT_preset_clear(Operator):
    bl_idname = "node.hot_node_preset_clear"
    bl_label = i18n.msg["Clear Presets"]
    bl_description = i18n.msg["desc_clear_presets"]
    bl_options = {'UNDO', 'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        return preset_clear(self, context, use_report=True)
    

class HOTNODE_OT_preset_move(Operator):
    bl_idname = "node.hot_node_preset_move"
    bl_label = i18n.msg["Move Preset"]
    bl_description = i18n.msg["desc_move_preset"]
    bl_options = {'UNDO', 'REGISTER'}
    
    direction: StringProperty(
        name='direction',
        default='UP'
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        return props_py.gl_pack_selected is not None and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        return preset_move(self, context, self.direction)
    

class HOTNODE_OT_preset_save(Operator):
    bl_idname = "node.hot_node_preset_save"
    bl_label = i18n.msg["Save Preset"]
    bl_description = i18n.msg["desc_save_preset"]
    bl_options = {'UNDO', 'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        return preset_save(self, context)
    
    def invoke(self, context, event):
        return _exec_pop_confirm_if_need(self, context, event)
    
    
class HOTNODE_OT_nodes_add(Operator):
    bl_idname = "node.hot_node_nodes_add"
    bl_label = i18n.msg["Add Nodes"]
    bl_description = i18n.msg["desc_add_nodes"]
    bl_options = {'REGISTER'}
    
    # "" means use selected one in the UI
    preset_name: StringProperty(
        name="preset_name",
        default=""
    ) # type: ignore
    
    # "" means use selected one in the UI
    pack_name: StringProperty(
        name="pack_name",
        default=""
    ) # type: ignore
    
    tree_type: StringProperty(
        name="tree_type",
        default=""
    ) # type: ignore
    
    @staticmethod
    def store_mouse_cursor(context, event):
        space = context.space_data
        tree = space.edit_tree

        # convert mouse position to the View2D for later node placement
        if context.region.type == 'WINDOW':
            # convert mouse position to the View2D for later node placement
            space.cursor_location_from_region(event.mouse_region_x, event.mouse_region_y)
        else:
            space.cursor_location = tree.view_center
    
    @classmethod
    def poll(cls, context):
        return context.space_data.edit_tree is not None
    
    def execute(self, context):
        return nodes_add(self, context, self.preset_name, self.pack_name, self.tree_type)
    
    def invoke(self, context, event):
        self.store_mouse_cursor(context, event)
        return self.execute(context)
    
    
class HOTNODE_OT_preset_apply(HOTNODE_OT_nodes_add):
    bl_idname = "node.hot_node_preset_apply"
    bl_label = i18n.msg["Apply Preset"]
    bl_description = i18n.msg["desc_add_nodes"]
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0
    
    
class HOTNODE_OT_texture_save(Operator):
    bl_idname = "node.hot_node_texture_save"
    bl_label = i18n.msg["Save Texture"]
    bl_description = i18n.msg["desc_save_texture"]
    bl_options = {'UNDO', 'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return props_bl.allow_tex_save
    
    def execute(self, context):
        return texture_save(self, context)
    
    def invoke(self, context, event):
        return _exec_pop_confirm_if_need(self, context, event)

    
class HOTNODE_OT_pack_create(Operator):
    bl_idname = "node.hot_node_pack_create"
    bl_label = i18n.msg["Create Pack"]
    bl_description = i18n.msg["desc_create_pack"]
    bl_options = {'UNDO', 'REGISTER'}

    def execute(self, context):
        return pack_create(self, context)
    

class HOTNODE_OT_pack_delete(Operator):
    bl_idname = "node.hot_node_pack_delete"
    bl_label = i18n.msg["Delete Pack"]
    bl_description = i18n.msg["desc_delete_pack"]
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return props_py.gl_pack_selected is not None

    def execute(self, context):
        return pack_delete(self, context)
    
    def invoke(self, context, event):
        return _exec_pop_confirm_if_need(self, context, event)
    
    
class HOTNODE_OT_pack_select(Operator):
    bl_idname = "node.hot_node_pack_select"
    bl_label = i18n.msg["Select Pack"]
    bl_description = i18n.msg["desc_select_pack"]
    bl_options = {'UNDO', 'REGISTER'}

    pack_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    def execute(self, context):
        return pack_select(self, context, self.pack_name)
    
    
class HOTNODE_OT_pack_import(bpy.types.Operator):
    bl_idname = "import.hot_node_pack_import"
    bl_label = i18n.msg["Import Pack(s)"]
    bl_description = i18n.msg["desc_import_pack"]
    bl_options = {'UNDO', 'REGISTER'}
    
    # if recovering, open the system's temp folder
    is_recovering: bpy.props.BoolProperty(default=False, options = {'HIDDEN'}) # type: ignore
    
    # Blender's prop templete for file selector
    # directory path of file selector
    directory: bpy.props.StringProperty(subtype="DIR_PATH") # type: ignore
    # path of selected file
    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore
    # name of selected file with suffix
    filename: bpy.props.StringProperty(subtype="FILE_NAME") # type: ignore
    # filter suffix in file select window
    filter_glob: StringProperty(default= "*.zip", options = {'HIDDEN'}) # type: ignore
    # selected files
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    def execute(self, context):
        return pack_import(self, context, self.files, self.directory, self.is_recovering)

    def invoke(self, context, event):
        if self.is_recovering:
            self.directory = file.autosave_dir_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_pack_export(bpy.types.Operator):
    bl_idname = "export.hot_node_pack_export"
    bl_label = i18n.msg["Export Pack"]
    bl_description = i18n.msg["desc_export_pack"]
    bl_options = {'REGISTER'}
    
    # path of selected file
    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore
    # name of selected file with suffix
    filename: bpy.props.StringProperty(subtype="FILE_NAME") # type: ignore
    # filter suffix in file select window
    filter_glob: StringProperty(default= "*.zip", options = {'HIDDEN'}) # type: ignore
    # selected files
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    
    unique_name: bpy.props.BoolProperty(name=i18n.msg["Using Unique Name"], default=True) # type: ignore

    @classmethod
    def poll(cls, context):
        return props_py.gl_pack_selected is not None
    
    def execute(self, context):
        return pack_export(self, context, self.filepath, self.filename, self.unique_name)

    def invoke(self, context, event):
        self.filename = ".".join((props_py.gl_pack_selected.name, "zip"))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_pack_export_all(bpy.types.Operator):
    bl_idname = "export.hot_node_pack_export_all"
    bl_label = i18n.msg["Export All Packs"]
    bl_description = i18n.msg["desc_export_all_packs"]
    bl_options = {'REGISTER'}
    
    # path of selected folder
    filepath: bpy.props.StringProperty(subtype="DIR_PATH") # type: ignore

    @classmethod
    def poll(cls, context):
        return props_py.gl_pack_selected is not None
    
    def execute(self, context):
        # we may get a file path as a dir path (the subtype="DIR_PATH" seems not to work). we will handle this in file.export_packs()
        return pack_export_all(self, context, self.filepath)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_refresh(Operator):
    bl_idname = "node.hot_node_refresh"
    bl_label = "Refresh"
    bl_description = i18n.msg["desc_refresh"]
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.hot_node_props
        sync.sync(props)
        self.report({'INFO'}, "Hot Node refreshed.")
        return {'FINISHED'}
    
    
# help to invoke some functions without import it as a module and allows accessing context. call this ops only in codes.
class HOTNODE_OT_helper(Operator):
    bl_idname = "node.hot_node_helper"
    bl_label = "Hot Node Helper Operator"
    bl_description = "Help to invoke some functions without import it as a module. Call this only in codes"
    bl_options = {'REGISTER'}

    def execute(self, context):
        mode = props_py.helper_mode
        props = context.scene.hot_node_props
        # param = props_py.helper_param
        if mode == 'PACK_RENAME':
            pack_name = props_py.helper_param
            gui.ensure_existing_pack_menu(pack_name)
        elif mode == 'PACK_SELECT':
            pack_name = props_py.helper_param
            props_bl.select_pack(props, props_py.gl_packs.get(pack_name, None))
        elif mode == 'PACK_NAME_SYNC':
            props_py.skip_pack_rename_callback = True
            props.pack_selected_name = props_py.get_gl_pack_selected_name()
            props_py.skip_pack_rename_callback = False
            
        return {'FINISHED'}


classes = (
    HOTNODE_OT_preset_clear,
    HOTNODE_OT_preset_create,
    HOTNODE_OT_preset_delete,
    HOTNODE_OT_preset_move,
    HOTNODE_OT_preset_save,
    HOTNODE_OT_preset_apply,
    HOTNODE_OT_nodes_add,
    HOTNODE_OT_texture_save,
    HOTNODE_OT_pack_create,
    HOTNODE_OT_pack_delete,
    HOTNODE_OT_pack_select,
    HOTNODE_OT_pack_import,
    HOTNODE_OT_pack_export,
    HOTNODE_OT_pack_export_all,
    HOTNODE_OT_refresh,
    HOTNODE_OT_helper,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)