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

from . import utils, file, properties, node_parser, node_generator


# Tool Functions
def sync_data(context: bpy.types.Context):
    file.refresh_root_meta_cache()
    properties.pack_selected = file.root_meta_cache["pack_selected"]
    properties.packs = file.read_packs()
    select_pack(context, properties.pack_selected)
    
    
def select_pack(context, pack):
    # to escaping overwrite 
    scene = context.scene
    properties.pack_selected = pack
    scene.hot_node_pack_selected_name = pack
    scene.hot_node_preset_selected = 0
    # load presets in the newly selected pack
    presets = scene.hot_node_presets
    presets.clear()
    file.select_pack(pack)
    if pack != "":
        preset_names, tree_types = file.read_preset_infos()
        length = len(preset_names)
        # properties.skip_update = True
        for i in range(length):
            name = preset_names[i]
            type = tree_types[name]
            presets.add()
            presets[i].name = name
            presets[i].type = type
        # properties.skip_update = False


def exchange(preset1, preset2):
    name, type = preset2.name, preset2.type
    preset2.name = preset1.name
    preset2.type = preset1.type
    preset1.name = name
    preset1.type = type
    
    
def bottom_to_top(presets):
    length = len(presets)
    preset = presets[length - 1]
    name, type = preset.name, preset.type
    for i in range(1, length):
        presets[length - i].name = presets[length - 1 - i].name
        presets[length - i].type = presets[length - 1 - i].type
    presets[0].name = name
    presets[0].type = type
    
    
def top_to_bottom(presets):
    length = len(presets)
    preset = presets[0]
    name, type = preset.name, preset.type
    for i in range(1, length):
        presets[i - 1].name = presets[i].name
        presets[i - 1].type = presets[i].type
    presets[length - 1].name = name
    presets[length - 1].type = type
    
    
def ensure_sync(ops: Operator, context: bpy.types.Context):
    if file.check_sync():
        return True
    else:
        sync_data(context)
        ops.report({'WARNING'}, "Out of sync. Nothing happend but the add-on's auto refreshing. Now everything is ok!")
        return False
    
    
def poll_preset_ops(context):
    return properties.pack_selected != '' and context.space_data.edit_tree is not None


# Operators
class HOTNODE_OT_preset_create(Operator):
    bl_idname = "node.hot_node_preset_create"
    bl_label = "Add Node Preset"
    bl_description = "Create a new node preset with selected nodes"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return poll_preset_ops(context)

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets
        edit_tree = context.space_data.edit_tree
            
        pack_name = properties.pack_selected
        presets = scene.hot_node_presets
        # escape rename. The default name is "Preset"... Do this first to check sync
        new_full_name = utils.ensure_unique_name_dot("Preset", -1, presets)
        
        presets.add()
        # select newly created set
        length = len(presets)
        preset_selected_idx = length - 1
        scene.hot_node_preset_selected = preset_selected_idx
        # set type
        presets[preset_selected_idx].type = edit_tree.bl_idname
        # XXX this is ugly but works... for escaping renaming the exist preset and overwriting it
        properties.skip_update = True
        presets[preset_selected_idx].name = new_full_name
        properties.preset_selected = new_full_name
        properties.skip_update = False
        
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
        return poll_preset_ops(context) and len(context.scene.hot_node_presets) > 0

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets

        length = len(presets)
        preset_selected_idx = scene.hot_node_preset_selected
        preset_name = presets[preset_selected_idx].name
        
        if length > 0:
            presets.remove(preset_selected_idx)
            if preset_selected_idx == length - 1:
                scene.hot_node_preset_selected -= 1
                
        file.delete_preset(preset_name)

        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_confirm:
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
        return poll_preset_ops(context) and len(context.scene.hot_node_presets) > 0

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        file.clear_preset(properties.pack_selected)
        scene.hot_node_presets.clear()
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
        return poll_preset_ops(context)

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets
        preset_selected_idx = scene.hot_node_preset_selected
        
        length = len(presets)
        if length < 2:
            return {'FINISHED'}
        
        properties.skip_update = True

        reorder = True
        if self.direction == 'UP':
            if preset_selected_idx == 0:
                dst_idx = length - 1
                top_to_bottom(presets)
            else:
                dst_idx = preset_selected_idx - 1
                exchange(presets[dst_idx], presets[preset_selected_idx])
                reorder = False
        elif self.direction == 'DOWN':
            if preset_selected_idx == length - 1:
                dst_idx = 0
                bottom_to_top(presets)
            else:
                dst_idx = preset_selected_idx + 1
                exchange(presets[dst_idx], presets[preset_selected_idx])
                reorder = False
        elif self.direction == 'TOP':
            dst_idx = 0
            bottom_to_top(presets)
        elif self.direction == 'BOTTOM':
            dst_idx = length - 1
            top_to_bottom(presets)

        # XXX should we save json every time we move position...? so ugly...
        # XXX the presets.keys() is supposed to work but when we move up a first created preset
        # in a first created pack, the keys[0] will be "" some how...
        if reorder:
            preset_names = []
            for i in range(len(presets)):
                preset_names.append(presets[i].name)
            file.reorder_preset_meta(preset_names)
        else:
            file.exchange_order_preset_meta(dst_idx, preset_selected_idx)
        scene.hot_node_preset_selected = dst_idx
        properties.skip_update = False

        return {'FINISHED'}
    

class HOTNODE_OT_preset_save(Operator):
    bl_idname = "node.hot_node_preset_save"
    bl_label = "Save Node Preset"
    bl_description = "Save selected nodes to the current preset"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return poll_preset_ops(context) and len(context.scene.hot_node_presets) > 0

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets
        preset_selected_idx = scene.hot_node_preset_selected
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
        if context.scene.hot_node_confirm:
            wm = context.window_manager
            result = wm.invoke_confirm(self, event, title='Save Preset (Can\'t Undo)', confirm_text='Save')
        else:
            result = self.execute(context)
        return result
    

class HOTNODE_OT_preset_apply(Operator):
    bl_idname = "node.hot_node_preset_apply"
    bl_label = "Apply Node Preset"
    bl_description = "Apply selected node preset to current window"
    bl_options = {'UNDO', 'REGISTER'}

    @classmethod
    def poll(cls, context):
        return poll_preset_ops(context) and len(context.scene.hot_node_presets) > 0
    
    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets

        preset_selected_idx = scene.hot_node_preset_selected
        preset = presets[preset_selected_idx]
        
        edit_tree_type = context.space_data.edit_tree.bl_idname
        if preset.type != edit_tree_type:
            self.report({'ERROR'}, f"Cannot apply preset: It is a {preset.type} but current edit tree is a {edit_tree_type}.")
            return {'CANCELLED'}
        
        failed_tex_num = node_generator.generate_preset(context, preset.name)
        if failed_tex_num > 0:
            self.report({'INFO'}, f"Nodes preset applied. But {failed_tex_num} textures can't be found. Check if your path exist, and has images that match at least one keyword.")
        else:
            self.report({'INFO'}, "Preset applied.")
            
        return {'FINISHED'}
    
    
class HOTNODE_OT_texture_save(Operator):
    bl_idname = "node.hot_node_texture_save"
    bl_label = "Save Texture Rule"
    bl_description = "Save rules of auto searching texture when apply preset. Note that you should do a save preset action and keep the last saved preset selected to save texture rules"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return properties.allow_tex_save
    
    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        scene = context.scene
        presets = scene.hot_node_presets
        preset_selected_idx = scene.hot_node_preset_selected
        preset_selected = presets[preset_selected_idx]
        preset_name = preset_selected.name
        pack_name = properties.pack_selected
        
        open_mode = scene.hot_node_tex_preset_mode
        tex_key = scene.hot_node_tex_key

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
            file.create_preset(preset_name, cpreset)
            self.report({'INFO'}, f"Texture saved.")
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_confirm:
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
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        packs = properties.packs
        new_full_name = utils.ensure_unique_name("Pack", -1, packs)
        packs.append(new_full_name)
        # select newly created pack
        length = len(packs)
        properties.pack_selected = packs[length - 1]

        file.create_pack(new_full_name)
        select_pack(context, new_full_name)
        
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
        if not ensure_sync(self, context):
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

        select_pack(context, pack_name)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if context.scene.hot_node_confirm:
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
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        # if not ensure_pack_sync(self, context):
        #     return {'CANCELLED'}
        select_pack(context, self.pack)
        
        return {'FINISHED'}
    
    
class HOTNODE_OT_pack_import(bpy.types.Operator):
    bl_idname = "import.hot_node_pack_import"
    bl_label = "Import Pack"
    bl_description = "Import hot node preset pack with .zip suffix"
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
        return poll_preset_ops(context)
    
    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        
        length = len(self.files)
        backslash_idx = self.filepath.rfind("\\")
        dir_path = self.filepath[:backslash_idx]
        success_num = 0
        for i in range(length):
            file_name = self.files[i].name
            file_path = "\\".join((dir_path, file_name))
            
            if file_name == ".zip" or file_name == "":
                self.report({'ERROR'}, f"\"{file_name}\" failed to import: Pack name cannot be empty.")
                continue
            
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
                
        if success_num > 0:
            properties.read_packs()
            select_pack(context, pack_name)
            if success_num == length:
                self.report({'INFO'}, "Import successed.")
            else:
                self.report({'INFO'}, f"Imported {success_num} packs of all {length} packs. The others were failed to import, see the previous error infos.")
        elif length > 1:
            self.report({'ERROR'}, f"Failed to import. See the previous error infos.")
            
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_pack_export(bpy.types.Operator):
    bl_idname = "export.hot_node_pack_export"
    bl_label = "Export Pack"
    bl_description = "Export hot node preset pack with .zip suffix"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return poll_preset_ops(context)
    
    # path of selected file
    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore
    # name of selected file with suffix
    filename: bpy.props.StringProperty(subtype="FILE_NAME") # type: ignore
    # filter suffix in file select window
    filter_glob : StringProperty(default= "*.zip", options = {'HIDDEN'}) # type: ignore
    # selected files
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    def execute(self, context):
        if not ensure_sync(self, context):
            return {'CANCELLED'}
        
        to_file_path = utils.ensure_has_suffix(self.filepath, ".zip")
        if self.filename == ".zip" or self.filename == "":
            self.report({'ERROR'}, "Export Failed: Pack name cannot be empty.")
            return {'CANCELLED'}
            
        file.export_pack(to_file_path)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filename = ".".join((properties.pack_selected, "zip"))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    

class HOTNODE_OT_refresh(Operator):
    bl_idname = "node.hot_node_refresh"
    bl_label = "Refresh Presets & Packs"
    bl_description = "Refresh presets and packs, useful for cross-file sync"
    bl_options = {'REGISTER'}

    def execute(self, context):
        sync_data(context)
        self.report({'INFO'}, "Presets & packs refreshed")
        return {'FINISHED'}


classes = (
    HOTNODE_OT_preset_clear,
    HOTNODE_OT_preset_create,
    HOTNODE_OT_preset_delete,
    HOTNODE_OT_preset_move,
    HOTNODE_OT_preset_save,
    HOTNODE_OT_preset_apply,
    HOTNODE_OT_texture_save,
    HOTNODE_OT_pack_create,
    HOTNODE_OT_pack_delete,
    HOTNODE_OT_pack_select,
    HOTNODE_OT_pack_import,
    HOTNODE_OT_pack_export,
    HOTNODE_OT_refresh,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)