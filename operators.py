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

from . import node_setter, utils, file, properties, node_parser


def _sync(context: bpy.types.Context):
    file.refresh_pack_root()
    properties.packs = file.read_packs()
    if properties.pack_selected not in properties.packs:
        properties.pack_selected = file.root_meta_cache["pack_selected"]
    _select_pack(context, properties.pack_selected)
    
    
def _ensure_sync(ops: Operator, context: bpy.types.Context):
    if file.check_sync():
        return True
    else:
        _sync(context)
        ops.report({'WARNING'}, "Out of sync, nothing happend but auto refreshing. Now it's READY!")
        return False
    
    
def _select_pack(context, dst_pack: str):
    # to escaping overwrite 
    props = context.scene.hot_node_props
    ori_pack = properties.pack_selected
    properties.pack_selected = dst_pack
    props.pack_selected_name = dst_pack
    preset_selected_old = props.preset_selected
    props.preset_selected = 0
    # load presets in the newly selected pack
    presets = props.presets
    presets.clear()
    file.select_pack(dst_pack)
    # if pack == "", means there is no pack, dont read any preset and keep pack as "", the ops will be grayed out because they will detect whether pack is "".
    if dst_pack != "":
        preset_names, tree_types = file.read_presets()
        preset_num = len(preset_names)
        properties.skip_rename_callback = True
        for i in range(preset_num):
            name = preset_names[i]
            type = tree_types[name]
            presets.add()
            presets[i].name = name
            presets[i].type = type
        properties.skip_rename_callback = False
        if ori_pack == dst_pack and preset_selected_old < preset_num:
            props.preset_selected = preset_selected_old

    
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
    
    
def _poll_preset_ops(context):
    return properties.pack_selected != "" and context.space_data.edit_tree is not None


# Functions for Calling Operators
def execute_refresh():
    try:
        bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')
        return None
    except AttributeError:
        # '_RestrictContext' object has no attribute 'view_layer'
        # if the registing is not finished yet, bpy.app.timer will take another 0.1s wait to call this func again
        return 0.1


# Operators
class HOTNODE_OT_preset_create(Operator):
    bl_idname = "node.hot_node_preset_create"
    bl_label = "Add Node Preset"
    bl_description = "Create a new node preset with selected nodes"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context)

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets
        edit_tree = context.space_data.edit_tree
        pack_name = properties.pack_selected
        # escape rename. The default name is "Preset"... Do this first to check sync
        new_full_name = utils.ensure_unique_name_dot("Preset", -1, presets)
        
        presets.add()
        # select newly created set
        length = len(presets)
        preset_selected_idx = length - 1
        props.preset_selected = preset_selected_idx
        # set type
        presets[preset_selected_idx].type = edit_tree.bl_idname
        properties.skip_rename_callback = True
        presets[preset_selected_idx].name = new_full_name
        properties.preset_selected = new_full_name
        properties.skip_rename_callback = False
        
        # try to save current selected nodes. In node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
        node_parser.parse_node_preset(edit_tree)
        cpreset = node_parser.set_preset_data(new_full_name, pack_name)
        file.create_preset(new_full_name, cpreset)

        return {'FINISHED'}
    

class HOTNODE_OT_preset_delete(Operator):
    bl_idname = "node.hot_node_preset_delete"
    bl_label = "Delete Node Preset"
    bl_description = "Delete selected node preset"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return properties.pack_selected != "" and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets

        length = len(presets)
        preset_selected_idx = props.preset_selected
        preset_name = presets[preset_selected_idx].name
        
        if length > 0:
            presets.remove(preset_selected_idx)
            if preset_selected_idx == length - 1:
                props.preset_selected -= 1
                
        file.delete_preset(preset_name)

        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_props.extra_confirm:
            wm = context.window_manager
            result = wm.invoke_confirm(self, event, title='Delete Preset (Can\'t Undo)', confirm_text='Delete')
        else:
            result = self.execute(context)
        return result
    

class HOTNODE_OT_preset_clear(Operator):
    bl_idname = "node.hot_node_preset_clear"
    bl_label = "Clear All"
    bl_description = "Delete all node presets in this pack"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        file.clear_preset(properties.pack_selected)
        props.presets.clear()
        self.report({'INFO'}, f"All presets in pack \"{properties.pack_selected}\" were deleted.")

        return {'FINISHED'}
    

class HOTNODE_OT_preset_move(Operator):
    bl_idname = "node.hot_node_preset_move"
    bl_label = "Move Preset"
    bl_description = "Move the active preset up/down in the list"
    bl_options = {'REGISTER'}
    
    direction: StringProperty(
        name='direction',
        default='UP'
    ) # type: ignore
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context)

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets
        preset_selected_idx = props.preset_selected
        
        length = len(presets)
        if length < 2:
            return {'FINISHED'}
        
        properties.skip_rename_callback = True

        reorder = True
        if self.direction == 'UP':
            if preset_selected_idx == 0:
                dst_idx = length - 1
            else:
                dst_idx = preset_selected_idx - 1
                reorder = False
        elif self.direction == 'DOWN':
            if preset_selected_idx == length - 1:
                dst_idx = 0
            else:
                dst_idx = preset_selected_idx + 1
                reorder = False
        elif self.direction == 'TOP':
            dst_idx = 0
        elif self.direction == 'BOTTOM':
            dst_idx = length - 1
            
        _preset_move_to(preset_selected_idx, dst_idx, presets)

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
        
        properties.skip_rename_callback = False

        return {'FINISHED'}
    

class HOTNODE_OT_preset_save(Operator):
    bl_idname = "node.hot_node_preset_save"
    bl_label = "Save Node Preset"
    bl_description = "Save selected nodes to the current preset"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets
        preset_selected_idx = props.preset_selected
        preset_selected = presets[preset_selected_idx]
        preset_name = preset_selected.name
        pack_name = properties.pack_selected
        edit_tree = context.space_data.edit_tree
        
        presets[preset_selected_idx].type = edit_tree.bl_idname
        # in node_parser.py we have a cpreset cache so dont need to store the return value of parse_node_preset()...
        node_parser.parse_node_preset(edit_tree)
        cpreset = node_parser.set_preset_data(preset_name, pack_name)
        file.update_preset(preset_name, cpreset)
        
        properties.allow_tex_save = True
        self.report(type={'INFO'}, message="Preset saved.")

        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_props.extra_confirm:
            wm = context.window_manager
            result = wm.invoke_confirm(self, event, title='Save Preset (Can\'t Undo)', confirm_text='Save')
        else:
            result = self.execute(context)
        return result
    
    
class HOTNODE_OT_nodes_add(Operator):
    bl_idname = "node.hot_node_nodes_add"
    bl_label = "Add Nodes"
    bl_description = "Add nodes to the editor tree"
    bl_options = {'UNDO', 'REGISTER'}
    
    # None means use selected one in the UI
    preset_name: StringProperty(
        name="preset_name",
        default=""
    ) # type: ignore
    
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
        return _poll_preset_ops(context)
    
    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets
        preset_selected_idx = props.preset_selected
        if self.preset_name == "":
            preset = presets[preset_selected_idx]
            self.preset_name = preset.name
            self.tree_type = preset.type
        
        edit_tree = context.space_data.edit_tree
        edit_tree_type = edit_tree.bl_idname
        if self.tree_type != edit_tree_type:
            self.report({'ERROR'}, f"Cannot apply preset: It is a {self.tree_type} but current edit tree is a {edit_tree_type}.")
            return {'CANCELLED'}
        
        # adds the nodes
        failed_tex_num= node_setter.apply_preset(context, self.preset_name, pack_name=self.pack_name, apply_offset=True)
        
        if failed_tex_num > 0:
            self.report({'INFO'}, f"Nodes added. But {failed_tex_num} textures can't be found. Check if your path exist, and has images that match at least one keyword.")
            
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
    
    def invoke(self, context, event):
        self.store_mouse_cursor(context, event)
        result = self.execute(context)

        return result
    
    
class HOTNODE_OT_preset_apply(HOTNODE_OT_nodes_add):
    bl_idname = "node.hot_node_preset_apply"
    bl_label = "Apply Node Preset"
    
    @classmethod
    def poll(cls, context):
        return _poll_preset_ops(context) and len(context.scene.hot_node_props.presets) > 0
    
    
class HOTNODE_OT_texture_save(Operator):
    bl_idname = "node.hot_node_texture_save"
    bl_label = "Save Texture Rule"
    bl_description = "Save rules of auto searching texture when apply preset. Note that you should do a save preset action and keep the last saved preset selected to save texture rules"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return properties.allow_tex_save
    
    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        props = context.scene.hot_node_props
        presets = props.presets
        preset_selected_idx = props.preset_selected
        preset_selected = presets[preset_selected_idx]
        preset_name = preset_selected.name
        pack_name = properties.pack_selected
        
        open_mode = props.tex_preset_mode
        tex_key = props.tex_key

        cpreset = node_parser.set_texture_rule(context.space_data.edit_tree, preset_name, pack_name, open_mode, tex_key)
        if not isinstance(cpreset, dict):
            if cpreset == 'EXCEED':
                self.report(type={'ERROR'}, message="Too more nodes were selected! You can only save one texture rule at a time!")
            elif cpreset == 'NO_NODE_SELECTED':
                self.report(type={'ERROR'}, message="You haven't select a texture node!")
            elif cpreset == 'NO_TEX_NODE':
                self.report(type={'ERROR'}, message="You are saving a node that don't need textures! Only node that needs a texture file can be saved!")
            elif cpreset == 'NOT_SAVED_NODE':
                self.report(type={'ERROR'}, message="This node is not in the last saved preset!")
            elif cpreset == 'NOT_PRESET_SELECTED':
                self.report(type={'ERROR'}, message="Current selected preset is not the last saved one. Do a save first.")
            return {'CANCELLED'}
        else:
            file.update_preset(preset_name, cpreset)
            self.report({'INFO'}, f"Texture saved.")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_props.extra_confirm:
            wm = context.window_manager
            result = wm.invoke_confirm(self, event, title='Save Texture (Can\'t Undo)', confirm_text='Save')
        else:
            result = self.execute(context)
        return result
    

class HOTNODE_OT_pack_create(Operator):
    bl_idname = "node.hot_node_pack_create"
    bl_label = "Create Pack"
    bl_description = "Create a new preset pack to store presets"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        packs = properties.packs
        new_full_name = utils.ensure_unique_name("Pack", -1, packs)
        packs.append(new_full_name)
        # select newly created pack
        length = len(packs)
        properties.pack_selected = packs[length - 1]

        file.create_pack(new_full_name)
        _select_pack(context, new_full_name)
        
        return {'FINISHED'}
    

class HOTNODE_OT_pack_delete(Operator):
    bl_idname = "node.hot_node_pack_delete"
    bl_label = "Delete Pack"
    bl_description = "Delete selected pack and all the node presets in it"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return properties.pack_selected != ''

    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        packs = properties.packs
        pack_name = properties.pack_selected
        pack_selected_idx = packs.index(pack_name)
        
        
        packs.remove(pack_name)
        file.delete_pack(pack_name)
        # note the length is the original length - 1
        length = len(packs)

        # select another pack if there is one
        if length > 0:
            # if deleted pack's idx is the last one, and not the only one, select the idx - 1
            if pack_selected_idx == length and pack_selected_idx > 0:
                pack_name = packs[pack_selected_idx - 1]
            # or let the next pack come up
            else:
                pack_name = packs[pack_selected_idx]
        # no pack last
        else:
            properties.pack_selected = ""
            pack_name = ""

        _select_pack(context, pack_name)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_props.extra_confirm:
            wm = context.window_manager
            result = wm.invoke_confirm(self, event, title='Delete Pack (Can\'t Undo)', confirm_text='Delete')
        else:
            result = self.execute(context)
        return result
    
    
class HOTNODE_OT_pack_select(Operator):
    bl_idname = "node.hot_node_pack_select"
    bl_label = "Select Pack"
    bl_description = "Select pack"
    bl_options = {'REGISTER'}

    pack: StringProperty(
        name='',
        default='',
        options={'HIDDEN'}
    ) # type: ignore
    
    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        _select_pack(context, self.pack)
        
        return {'FINISHED'}
    
    
class HOTNODE_OT_pack_import(bpy.types.Operator):
    bl_idname = "import.hot_node_pack_import"
    bl_label = "Import Pack(s)"
    bl_description = "Import hot node preset pack(s) with .zip suffix"
    bl_options = {'REGISTER'}
    
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
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        
        file_num = len(self.files)
        # backslash_idx = self.filepath.rfind("\\")
        # dir_path = self.filepath[:backslash_idx]
        success_num = 0
        
        # import every selected file
        for i in range(file_num):
            file_name = self.files[i].name
                    
            file_path = "\\".join((self.directory, file_name))
            
            if file_name == ".zip" or file_name == "":
                self.report({'ERROR'}, f"\"{file_name}\" failed to import: Pack name cannot be empty.")
                continue
            
            # cull autosave suffix
            if self.is_recovering:
                pack_name = utils.get_string_between_words(file_name, None, ("_autosave_", "_deprecated_"))
                if pack_name is False:
                    self.report({'ERROR'}, f"\"{file_name}\" failed to import: The file seems not a autosaved hot node pack.")
                    continue
            else:
                pack_name = file_name[:-4]
                if pack_name in properties.packs:
                    self.report({'ERROR'}, f"\"{file_name}\" failed to import: Pack \"{pack_name}\" already existed.")
                    continue
                
            result = file.import_pack(file_path, pack_name)
            
            if result == 'META_LACK':
                self.report({'ERROR'}, f"\"{file_name}\" failed to import: The file seems not a hot node pack.")
            elif result == 'INVALID_META':
                self.report({'ERROR'}, f"\"{file_name}\" failed to import: The pack's meta data is corrupted.")
            elif result == 'OVER_SIZE':
                self.report({'ERROR'}, f"\"{file_name}\" failed to import: Cannot import pack that is bigger than 100 MiB.")
            else:
                success_num += 1
                
        # count import infos
        if success_num > 0:
            properties.packs = file.read_packs()
            _select_pack(context, pack_name)
            if success_num == file_num:
                if self.is_recovering:
                    self.report({'INFO'}, f"\"{pack_name}\" recovered.")
                else:
                    self.report({'INFO'}, f"\"{pack_name}\" imported.")
            else:
                self.report({'INFO'}, f"Imported {success_num} packs of all {file_num} packs. The others were failed to import, see the previous error infos.")
        elif file_num > 1:
            self.report({'ERROR'}, f"Failed to import. See the previous error infos.")
            
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.is_recovering:
            self.directory = file.temp_dir_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_pack_export(bpy.types.Operator):
    bl_idname = "export.hot_node_pack_export"
    bl_label = "Export Pack"
    bl_description = "Export hot node preset pack with .zip suffix"
    bl_options = {'REGISTER'}
    
    # path of selected file
    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore
    # name of selected file with suffix
    filename: bpy.props.StringProperty(subtype="FILE_NAME") # type: ignore
    # filter suffix in file select window
    filter_glob : StringProperty(default= "*.zip", options = {'HIDDEN'}) # type: ignore
    # selected files
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    @classmethod
    def poll(cls, context):
        return properties.pack_selected != ""
    
    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        
        to_file_path = utils.ensure_has_suffix(self.filepath, ".zip")
        if self.filename == ".zip" or self.filename == "":
            self.report({'ERROR'}, "Export Failed: Pack name cannot be empty.")
            return {'CANCELLED'}
            
        file.export_selected_pack(to_file_path)
        self.report({'INFO'}, f"Exported pack \"{properties.pack_selected}\" to {to_file_path}.")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ".".join((properties.pack_selected, "zip"))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_pack_export_all(bpy.types.Operator):
    bl_idname = "export.hot_node_pack_export_all"
    bl_label = "Export All Packs"
    bl_description = "Export all preset packs with .zip suffix"
    bl_options = {'REGISTER'}
    
    # path of selected file
    filepath: bpy.props.StringProperty(subtype="DIR_PATH") # type: ignore

    @classmethod
    def poll(cls, context):
        return properties.pack_selected != ""
    
    def execute(self, context):
        if not _ensure_sync(self, context):
            return {'CANCELLED'}
        
        file.export_packs(properties.packs, self.filepath)
            
        self.report({'INFO'}, f"Exported all packs to {self.filepath}.")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ".".join((properties.pack_selected, "zip"))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    

class HOTNODE_OT_refresh(Operator):
    bl_idname = "node.hot_node_refresh"
    bl_label = "Refresh"
    bl_description = "Refresh presets and packs, useful for cross-file sync"
    bl_options = {'REGISTER'}

    def execute(self, context):
        _sync(context)
        self.report({'INFO'}, "Hot Node refreshed.")
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
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)