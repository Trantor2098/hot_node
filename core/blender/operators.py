import bpy
import addon_utils
from bpy.types import Operator
from bpy.app.translations import (
    pgettext_iface as iface_,
    pgettext_rpt as rpt_,
    contexts as i18n_contexts,
)
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatVectorProperty,
    StringProperty,
    IntProperty,
    PointerProperty,
)

from ..context.context import Context
from ...services.autosave import AutosaveService as AS
from ...services.history import HistoryService as HS
from ...services.sync import SyncService as SS
from ...services.versioning import VersioningService as VS
from .ui_context import UIContext
from ...utils import utils
from ...utils import constants
from ...utils.reporter import Reporter

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..context.pack import Pack
    from ..context.preset import Preset


class HOTNODE_OT_add_preset(Operator):
    bl_idname = "hotnode.add_preset"
    bl_label = "Add Nodes Preset"
    bl_description = "Create a new preset with selected nodes."
    bl_translation_context = i18n_contexts.default
    # bl_options = {'REGISTER'}
    bl_options = {'REGISTER'}
    
    pack_name: StringProperty(name="Pack of preset", default="", options={'HIDDEN'}) # type: ignore
    preset_name: StringProperty(name="New Preset Name", default="") # type: ignore

    # duplicate the given preset
    is_duplicate: BoolProperty(name="Is Duplicate", default=False, options={'HIDDEN'}) # type: ignore

    @staticmethod
    def undo(uic: UIContext, pack_name, preset_name, idx_before):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        pack.remove_preset(preset_name) # this will save pack meta
        pack.save_metas()
        Context.select_preset(idx_before)
        uic.remove_preset(uic, len(uic.presets) - 1)
        uic.select_preset(uic, idx_before)
        
    @staticmethod
    def redo(uic: UIContext, pack_name, preset_name):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        preset = pack.create_preset(preset_name)
        pack.add_preset(preset)
        pack.load_preset(preset)
        pack.save_metas()
        Context.select_preset(preset)
        uic.add_preset(uic, preset)
        uic.select_preset(uic, len(pack.presets) - 1)

    @classmethod
    def poll(cls, context):
        return Context.packs != {}

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack = Context.get_pack(self.pack_name)
        
        if not Context.is_pack_selected(pack):
            pack = Context.select_pack(pack)
            uic.select_pack(uic, pack)
        idx_before = uic.preset_selected_idx
        
        if self.is_duplicate:
            preset = pack.duplicate_preset(self.preset_name)
        else:
            if self.preset_name == "":
                new_name = utils.get_user_prefs(context).default_preset_name
            else:
                new_name = self.preset_name
            new_name = utils.delete_slash_anti_slash_in_string(new_name)
            new_name = utils.ensure_unique_name_for_item(new_name, pack.ordered_presets)
            
            preset = pack.create_preset(new_name)
            pack.add_preset(preset)
            
            # change preset name if only one node is selected
            if getattr(context.space_data, "edit_tree") is not None:
                pack.overwrite_preset(preset, context)
                preset_name_when_only_one_node = Context.ser_context.preset_name_when_only_one_node
                if preset_name_when_only_one_node is not None:
                    new_name = utils.ensure_unique_name_for_item(preset_name_when_only_one_node, pack.ordered_presets)
                    pack.rename_preset(preset, new_name)
            else:
                pack.save_preset(preset) # create json
        pack.save_metas()
        
        uic.add_preset(uic, preset)
        Context.select_preset(preset)
        
        step = HS.step(self.bl_label, self)
        HS.set_changed_paths(step, pack.meta_path)
        HS.set_created_paths(step, preset.path)
        
        HS.set_undo(step, self.undo, pack.name, preset.name, idx_before)
        HS.set_redo(step, self.redo, pack.name, preset.name)
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return self.execute(context)
    

class HOTNODE_OT_remove_preset(Operator):
    bl_idname = "hotnode.remove_preset"
    bl_label = "Remove Nodes Preset"
    bl_description = "Delete selected preset from the pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    pack_name: StringProperty(name="Pack of preset", default="", options={'HIDDEN'}) # type: ignore
    preset_name: StringProperty(name="New Preset Name", default="") # type: ignore
    
    @staticmethod
    def undo(uic: UIContext, pack_name, preset_name, idx_before):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        preset = pack.create_preset(preset_name)
        pack.add_preset(preset, idx_before)
        pack.save_metas()
        Context.select_preset(preset_name)
        uic.add_preset(uic, preset, dst_idx=idx_before)
        
    @staticmethod
    def redo(uic: UIContext, pack_name, idx_before, idx_after):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        pack.remove_preset_from_pack(idx_before)
        pack.save_metas()
        Context.select_preset(idx_after)
        uic.remove_preset(uic, idx_before)
        uic.select_preset(uic, idx_after)
        
    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None and len(Context.get_pack_selected().presets) > 0

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack = Context.packs.get(self.pack_name)
        preset = pack.get_preset(self.preset_name)
        
        step = HS.step(self.bl_label, self)
        HS.set_deleted_paths(step, preset.path)
        HS.set_changed_paths(step, pack.meta_path)
        
        pack.remove_preset(preset)
        pack.save_metas()
        
        if not Context.is_pack_selected(pack):
            Context.select_pack(pack)
            uic.select_pack(uic, pack)
            
        idx_before = uic.preset_selected_idx
        uic.remove_preset_selected(uic)
        idx_after = uic.preset_selected_idx # idx after removing
        Context.select_preset(idx_after)
        
        HS.set_undo(step, self.undo, pack.name, preset.name, idx_before)
        HS.set_redo(step, self.redo, pack.name, idx_before, idx_after)
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}

class HOTNODE_OT_clear_presets(Operator):
    bl_idname = "hotnode.clear_presets"
    bl_label = "Remove All Presets"
    bl_description = "Delete all presets in the current selected pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    @staticmethod
    def undo(uic: UIContext, pack_name, ordered_preset_names: list[str], idx_before):
        pack = Context.get_pack(pack_name)
        Context.select_pack(pack)
        presets = pack.create_presets(ordered_preset_names)
        pack.add_presets(presets)
        pack.save_metas()
        Context.select_preset(idx_before)
        uic.select_pack(uic, pack) # this loads presets to uic anyway
        uic.select_preset(uic, idx_before)

    @staticmethod
    def redo(uic: UIContext, pack_name: str):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        pack.clear_presets()
        pack.save_metas()
        Context.select_preset(None)
        uic.clear_presets(uic)
    
    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None and len(Context.get_pack_selected().presets) > 0

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack = Context.get_pack_selected()
        
        step = HS.step(self.bl_label, self)
        HS.set_deleted_paths(step, *[preset.path for preset in pack.ordered_presets])
        HS.set_changed_paths(step, pack.meta_path)
        HS.set_undo(step, self.undo, pack.name, pack.meta.ordered_preset_names, uic.preset_selected_idx)
        HS.set_redo(step, self.redo, pack.name)
        
        pack.clear_presets()
        pack.save_metas()
        uic.clear_presets(uic)
        Context.select_preset(None)
        
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}

class HOTNODE_OT_order_preset(Operator):
    bl_idname = "hotnode.order_preset"
    bl_label = "Move Preset"
    bl_description = "Move the selected preset up or down in the list."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    direction: StringProperty(
        name='direction',
        default='UP'
    ) # type: ignore
    
    @staticmethod
    def undo(uic: UIContext, pack_name, src_idx: int, dst_idx: int):
        pack = Context.select_pack(pack_name)
        Context.select_preset(dst_idx)
        pack.order_preset(dst_idx, src_idx)
        pack.save_metas()
        if uic.is_pack_selected(uic, pack):
            uic.order_preset(uic, src_idx, dst_idx)
        else:
            uic.select_pack(uic, pack)
        uic.select_preset(uic, src_idx)
        
    @staticmethod
    def redo(uic: UIContext, pack_name, src_idx: int, dst_idx: int):
        pack = Context.select_pack(pack_name)
        Context.select_preset(src_idx)
        pack.order_preset(src_idx, dst_idx)
        pack.save_metas()
        if uic.is_pack_selected(uic, pack):
            uic.order_preset(uic, src_idx, dst_idx)
        else:
            uic.select_pack(uic, pack)
        uic.select_preset(uic, dst_idx)
    
    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None and len(Context.get_pack_selected().presets) > 0

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack = Context.get_pack_selected()
        
        length = len(pack.presets)
        if length < 2:
            return {'CANCELLED'}
        
        src_idx = uic.preset_selected_idx
        if self.direction == 'UP':
            if src_idx == 0:
                dst_idx = length - 1
            else:
                dst_idx = src_idx - 1
        elif self.direction == 'DOWN':
            if src_idx == length - 1:
                dst_idx = 0
            else:
                dst_idx = src_idx + 1
        elif self.direction == 'TOP':
            dst_idx = 0
        elif self.direction == 'BOTTOM':
            dst_idx = length - 1
            
        step = HS.step(self.bl_label, self)
        HS.set_undo(step, self.undo, pack.name, src_idx, dst_idx)
        HS.set_redo(step, self.redo, pack.name, src_idx, dst_idx)
        
        Context.get_pack_selected().order_preset(src_idx, dst_idx)
        Context.get_pack_selected().save_metas()
        uic.order_preset(uic, src_idx, dst_idx)

        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}

class HOTNODE_OT_overwrite_preset_with_selected_nodes(Operator):
    bl_idname = "hotnode.overwrite_preset_with_selection"
    bl_label = "Overwrite Preset"
    bl_description = "Overwrite the selected preset with the currently selected nodes."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    preset_name: StringProperty(
        name="preset_name",
        default=""
    ) # type: ignore
    
    pack_name: StringProperty(
        name="pack_name",
        default=""
    ) # type: ignore
    
    @staticmethod
    def undo_redo(uic: UIContext, pack_name):
        pack = Context.select_pack(pack_name)
        uic.select_pack(uic, pack)
        pack.update_meta_tree_types()
    
    @classmethod
    def poll(cls, context):
        # we should have a right click menu, so escape presets check... if len == 0, just create
        return Context.get_pack_selected() is not None and getattr(context.space_data, "edit_tree") is not None

    def execute(self, context):
        Reporter.set_active_ops(self)
        pack = Context.packs[self.pack_name]
        preset = pack.get_preset(self.preset_name)
        if preset is None:
            bpy.ops.hotnode.add_preset('INVOKE_DEFAULT', preset_name=self.preset_name, pack_name=self.pack_name)
            return {'FINISHED'}
        
        step = HS.step(self.bl_label, self)
        HS.set_changed_paths(step, pack.meta_path, preset.path)
        HS.set_undo_redo(step, self.undo_redo, pack.name)
        
        pack.overwrite_preset(preset, context)
        pack.save_metas()
        
        HS.save_step(step)
        Reporter.report_finish(iface_("Overwrite") + " \"" + preset.name + "\"")
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return self.execute(context)
    
class HOTNODE_OT_add_preset_nodes_to_tree(Operator):
    bl_idname = "hotnode.add_preset_nodes_to_tree"
    bl_label = "Get Nodes"
    bl_description = "Get nodes from preset and add to the node tree."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER', 'UNDO'}
    
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
    
    new_tree: BoolProperty(
        name="new_tree",
        default=False
    ) # type: ignore
    
    @staticmethod
    def store_mouse_cursor(context: bpy.types.Context, event):
        space: bpy.types.SpaceNodeEditor = context.space_data
        tree = space.edit_tree

        if context.region.type == 'WINDOW':
            # convert mouse position to the View2D for later node placement
            # this can help cursor location to be accurate. 
            # if we dont do this, the cursor location will be affected by the zoom level and pan position based on region coordinates.
            space.cursor_location_from_region(event.mouse_region_x, event.mouse_region_y)
        else:
            space.cursor_location = tree.view_center
    
    @classmethod
    def poll(cls, context):
        return isinstance(context.space_data, bpy.types.SpaceProperties) or getattr(context.space_data, "edit_tree") is not None
    
    def execute(self, context):
        '''Add nodes to the node tree.'''
        Reporter.set_active_ops(self)
        uic = context.window_manager.hot_node_ui_context
        pack = Context.packs[self.pack_name]
        preset = pack.get_preset(self.preset_name)
            
        edit_tree: bpy.types.NodeTree = context.space_data.edit_tree
        if preset.meta.tree_type != edit_tree.bl_idname and preset.meta.tree_type != constants.UNIVERSAL_NODE_TREE_IDNAME:
            Reporter.report_warning(iface_("The preset tree type does not match the current node tree type."))
            Reporter.set_active_ops(None)
            return {'CANCELLED'}
        
        if pack.is_preset_file_exist(preset):
            try:
                pack.add_preset_nodes_to_tree(context, preset)
            except RuntimeError as e:
                SS.sync()
                Reporter.report_warning(f"{e} Hot Node refreshed.")
                Reporter.set_active_ops(None)
                return {'CANCELLED'}
        else:
            SS.sync()
            Reporter.report_warning("The preset file does not exist. Hot Node refreshed.")
            Reporter.set_active_ops(None)
            return {'CANCELLED'}
            
        # call translate ops for moving nodes. escaping select NodeFrames because they will cause bugs in move ops. reselect them later.
        newed_node_frames = []
        deser_context = preset.get_deser_context()
        for node in deser_context.newed_main_tree_nodes:
            if node.select and node.bl_idname == "NodeFrame":
                newed_node_frames.append(node)
                node.select = False
                
        bpy.ops.node.translate_attach_remove_on_cancel('INVOKE_DEFAULT')
            
        for node in newed_node_frames:
            node.select = True
            
        if len(deser_context.newed_main_tree_nodes) == 1:
            edit_tree.nodes.active = deser_context.newed_main_tree_nodes[0]
            
        Reporter.set_active_ops(None)
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.new_tree:
            self.store_mouse_cursor(context, event)
        return self.execute(context)
    
class HOTNODE_OT_transfer_preset_to_pack(Operator):
    bl_idname = "hotnode.transfer_preset_to_pack"
    bl_label = "Transfer Preset to Pack"
    bl_description = "Copy or move a preset to another pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    src_pack_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    dst_pack_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    preset_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    # move or copy
    is_move: BoolProperty(
        default=False,
        options={'HIDDEN'}
    ) # type: ignore
    
    @staticmethod
    def undo(
        uic: UIContext,
        src_pack_name: str,
        dst_pack_name: str,
        preset_name: str,
        is_move: bool,
    ):
        src_pack = Context.get_pack(src_pack_name)
        dst_pack = Context.get_pack(dst_pack_name)
        dst_pack.load()
        if is_move:
            src_pack.load()
        
        Context.select_pack(src_pack)
        Context.select_preset(preset_name)
        uic.select_pack(uic, src_pack)
        uic.select_preset(uic, preset_name)
        
    @staticmethod
    def redo(
        uic: UIContext,
        src_pack_name: str,
        dst_pack_name: str,
        is_move: bool,
        idx_after: int
    ):
        src_pack = Context.get_pack(src_pack_name)
        dst_pack = Context.get_pack(dst_pack_name)
        dst_pack.load()
        if is_move:
            src_pack.load()
        
        Context.select_pack(src_pack)
        Context.select_preset(idx_after)
        uic.select_pack(uic, src_pack)
        uic.select_preset(uic, idx_after)

    @classmethod
    def poll(self, context):
        return Context.get_pack_selected() is not None and Context.get_preset_selected()
    
    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        idx_before_transfer = self.src_pack.get_preset_idx(self.preset)
        is_src_pack_selected = self.src_pack is Context.get_pack_selected()
        is_dst_pack_selected = self.dst_pack is Context.get_pack_selected()
        
        step = HS.step(self.bl_label, self)
        
        if self.is_overwriting:
            preset_to_overwrite = self.dst_pack.get_preset(self.preset_name)
            HS.add_changed_paths(step, preset_to_overwrite.path)
            self.dst_pack.remove_preset(preset_to_overwrite)
        
        idx_after = 0 if self.src_pack.presets else -1
        if self.is_move:
            HS.add_changed_paths(step, self.src_pack.meta_path, self.dst_pack.meta_path)
            HS.add_deleted_paths(step, self.preset.path)
            self.src_pack.remove_preset(self.preset)
            self.dst_pack.add_preset(self.preset) # add_preset will change preset path
            self.dst_pack.save_preset(self.preset)
            self.dst_pack.save_metas()
            HS.add_created_paths(step, self.preset.path)
            
            # handle idx change if the preset is in the current pack
            if is_src_pack_selected:
                uic.remove_preset(uic, idx_before_transfer)
                idx_after = uic.preset_selected_idx
                Context.select_preset(idx_after)
        else:
            HS.add_changed_paths(step, self.dst_pack.meta_path)
            copied_preset = self.preset.deepcopy()
            self.dst_pack.add_preset(copied_preset)
            self.dst_pack.save_preset(copied_preset)
            self.dst_pack.save_metas()
            HS.add_created_paths(step, copied_preset.path)

            if is_src_pack_selected:
                idx_after = uic.preset_selected_idx
                
        if is_dst_pack_selected:
            uic.add_preset(uic, self.preset_name)

        HS.set_undo(step, self.undo, self.src_pack_name, self.dst_pack_name, self.preset_name, self.is_move)
        HS.set_redo(step, self.redo, self.src_pack_name, self.dst_pack_name, self.is_move, idx_after)
        
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        uic: UIContext = context.window_manager.hot_node_ui_context
        preset_name = uic.presets[uic.preset_selected_idx].name
        self.src_pack = Context.packs[self.src_pack_name]
        self.dst_pack = Context.packs[self.dst_pack_name]
        self.preset = self.src_pack.get_preset(preset_name)
        if self.preset.name in self.dst_pack.meta.ordered_preset_names:
            wm = context.window_manager
            result = wm.invoke_confirm(
                self, 
                event=event, 
                title="Preset Already Existed", 
                confirm_text="Overwrite",
                message="The preset already exists in the pack. Do you want to overwrite it?"
            )
            self.is_overwriting = True
            return result
        self.is_overwriting = False
        return self.execute(context)


class HOTNODE_OT_create_pack(Operator):
    bl_idname = "hotnode.create_pack"
    bl_label = "Create Pack"
    bl_description = "Create a new pack"
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    pack_name: StringProperty(
        name="Pack Name",
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    @staticmethod
    def undo(uic: UIContext, new_pack_name, prev_pack_selected_name, idx_before):
        if Context.get_pack_selected_name() == new_pack_name:
            pack = Context.select_pack(prev_pack_selected_name)
            uic.select_pack(uic, pack)
            if pack:
                Context.select_preset(idx_before)
                uic.select_preset(uic, idx_before)
        Context.remove_pack(new_pack_name)
        
    @staticmethod
    def redo(uic: UIContext, new_pack_name):
        pack = Context.load_pack(new_pack_name)
        Context.add_pack(pack)
        Context.select_pack(pack)
        uic.select_pack(uic, pack)

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        new_pack_name = utils.ensure_unique_name(self.pack_name, list(Context.packs.keys()))
        prev_pack_selected_name = Context.get_pack_selected_name()
        idx_before = uic.preset_selected_idx
        
        pack = Context.create_pack(new_pack_name)
        Context.add_pack(pack)
        Context.select_pack(pack)
        uic.select_pack(uic, pack)
        
        step = HS.step(self.bl_label, self)
        HS.set_created_paths(step, pack.pack_dir)
        HS.set_undo(step, self.undo, new_pack_name, prev_pack_selected_name, idx_before)
        HS.set_redo(step, self.redo, new_pack_name)
        
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}


class HOTNODE_OT_remove_pack(Operator):
    bl_idname = "hotnode.remove_pack"
    bl_label = "Remove Pack"
    bl_description = "Delete the selected pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    pack_name: StringProperty(
        name="Pack Name",
        default="",
        options={'HIDDEN'}
    ) # type: ignore

    @staticmethod
    def undo(uic: UIContext, pack_name: str, is_pack_selected, idx_before: int):
        """Undo function for removing a pack."""
        pack = Context.load_pack(pack_name)
        Context.add_pack(pack)
        if is_pack_selected:
            Context.select_pack(pack)
            Context.select_preset(idx_before)
            uic.select_pack(uic, pack)
            uic.select_preset(uic, idx_before)

    @staticmethod
    def redo(uic: UIContext, pack_name: str, is_pack_selected, pack_after_name: str):
        """Redo function for removing a pack."""
        Context.remove_pack(pack_name)
        if is_pack_selected:
            pack_after = Context.select_pack(pack_after_name)
            uic.select_pack(uic, pack_after)

    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack = Context.get_pack(self.pack_name)
        is_pack_selected = Context.is_pack_selected(pack)
        user_prefs = utils.get_user_prefs(context)
        space_tree_type = context.space_data.tree_type if context.space_data and hasattr(context.space_data, "tree_type") else None
        
        if user_prefs.is_filter_pack_by_tree_type and space_tree_type is not None:
            packs = Context.get_ordered_packs_by_tree_type(space_tree_type)
            # no pack in this type after deletion, show all packs
            if len(packs) == 1 and packs[0] is pack:
                packs = Context.ordered_packs
        else:
            packs = Context.ordered_packs
        
        step = HS.step(self.bl_label, self)
        HS.set_deleted_paths(step, pack.pack_dir)

        if is_pack_selected:
            pack_after = Context.get_next_pack(pack, packs)
            if pack_after is None:
                pack_after = Context.get_prev_pack(pack, packs)
            Context.select_pack(pack_after)
            uic.select_pack(uic, pack_after)
        else:
            pack_after = Context.get_pack_selected()
        pack_after_name = pack_after.name if pack_after else ""
        
        Context.remove_pack(pack)
        
        HS.set_undo(step, self.undo, pack.name, is_pack_selected, uic.preset_selected_idx)
        HS.set_redo(step, self.redo, pack.name, is_pack_selected, pack_after_name)

        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return self.execute(context)
    
class HOTNODE_OT_select_pack(Operator):
    bl_idname = "hotnode.select_pack"
    bl_label = "Select Pack"
    bl_description = "Select a pack for editing."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    pack_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    mode: StringProperty(
        name="mode",
        default='BYNAME'
    ) # type: ignore

    @classmethod
    def poll(cls, context):
        return len(Context.get_packs()) > 0

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        user_prefs = utils.get_user_prefs(context)
        old_pack = Context.get_pack_selected()
        space_tree_type = context.space_data.tree_type if context.space_data and hasattr(context.space_data, "tree_type") else None
        
        if user_prefs.is_filter_pack_by_tree_type and space_tree_type is not None:
            packs = Context.get_ordered_packs_by_tree_type(space_tree_type)
        else:
            packs = Context.ordered_packs

        if self.mode == 'PREV':
            dst_pack = Context.get_prev_pack(old_pack, packs)
        elif self.mode == 'NEXT':
            dst_pack = Context.get_next_pack(old_pack, packs)
        elif self.mode == 'BYNAME':
            dst_pack = Context.get_pack(self.pack_name)
            
        if old_pack is not None and old_pack is dst_pack:
            Reporter.set_active_ops(None)
            return {'CANCELLED'}
        
        Context.select_pack(dst_pack)
        uic.select_pack(uic, dst_pack)
        
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    
class HOTNODE_OT_set_pack_icon(Operator):
    bl_idname = "hotnode.set_pack_icon"
    bl_label = "Set Pack Icon"
    bl_description = "Set the icon for the selected pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    pack_name: StringProperty(
        default="",
        options={'HIDDEN'}
    ) # type: ignore
    
    icon: StringProperty(
        name="icon",
        default='OUTLINER_COLLECTION',
        options={'HIDDEN'}
    ) # type: ignore
    
    @staticmethod
    def undo(uic: UIContext, pack_name: str, icon: str):
        """Undo function for setting pack icon."""
        pack = Context.get_pack(pack_name)
        pack.set_meta_icon(icon)
        pack.save_metas()
        uic.select_pack(uic, pack)
        
    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None
    
    def execute(self, context):
        Reporter.set_active_ops(self)
        pack = Context.get_pack(self.pack_name)
        
        step = HS.step(self.bl_label, self)
        HS.set_undo(step, self.undo, pack.name, pack.meta.icon)
        HS.set_redo(step, self.undo, pack.name, self.icon)

        pack.set_meta_icon(self.icon)
        pack.save_metas()
        
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    
class HOTNODE_OT_import_pack(bpy.types.Operator):
    bl_idname = "hotnode.import_pack"
    bl_label = "Import Pack"
    bl_description = "Import preset pack(s) from zip file."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    # Blender's prop templete for file selector
    # directory path of file selector
    directory: StringProperty(subtype="DIR_PATH") # type: ignore
    # path of selected file
    filepath: StringProperty(subtype="FILE_PATH") # type: ignore
    # name of selected file with suffix
    filename: StringProperty(subtype="FILE_NAME") # type: ignore
    # filter suffix in file select window
    filter_glob: StringProperty(default= "*.zip", options = {'HIDDEN'}) # type: ignore
    # selected file names
    files : CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    
    # if recovering, open the system's temp folder
    is_recovering: BoolProperty(default=False, options = {'HIDDEN'}) # type: ignore
    
    @staticmethod
    def undo(uic: UIContext, new_pack_names, pack_name_before, idx_before):
        if Context.get_pack_selected_name() in new_pack_names:
            pack = Context.select_pack(pack_name_before)
            uic.select_pack(uic, pack)
            if pack:
                Context.select_preset(idx_before)
                uic.select_preset(uic, idx_before)
        for pack_name in new_pack_names:
            Context.remove_pack(pack_name)

    @staticmethod
    def redo(uic: UIContext, import_pack_names):
        for pack_name in import_pack_names:
            pack = Context.load_pack(pack_name)
            Context.add_pack(pack)
        pack = Context.select_pack(pack_name)
        uic.select_pack(uic, pack)

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic: UIContext = context.window_manager.hot_node_ui_context
        pack_before = Context.get_pack_selected()
        idx_before = uic.preset_selected_idx
        
        src_dir = Context.fm.str_to_path(self.directory)
        
        file_num = len(self.files)
        last_imported_pack = None
        imported_packs: list[Pack] = []
        import_pack_names = []
        
        # import every selected file
        for i in range(file_num):
            file_name = self.files[i].name
            src_zip_path = src_dir / file_name
            
            # name checking
            if file_name == ".zip" or file_name == "":
                msg = iface_("Failed to import because the pack name is empty: ") + file_name
                self.report({'ERROR'}, msg)
                continue
            if self.is_recovering:
                timestemp_str, pack_name = AS.parse_autosave_zip_path(src_zip_path)
                pack_name = pack_name + " (Recovered)"
                pack_name = utils.ensure_unique_name(pack_name, list(Context.packs.keys()))
            else:
                pack_name = file_name[:-4]
                if Context.get_pack(pack_name) is not None:
                    pack_name = utils.ensure_unique_name(pack_name, list(Context.packs.keys()))

            # do import
            dst_pack_dir = Context.fm.packs_dir / pack_name
            Context.fm.unzip_to(src_zip_path, dst_pack_dir)
            
            # detect and convert legacy pack
            legacy_pack_meta_path = dst_pack_dir / ".metadata.json"
            if legacy_pack_meta_path.exists():
                pack = Context.create_pack(pack_name)
                failed_preset_names, legacy_meta = VS.convert_pack_of_0_X_X(context, pack)
                if failed_preset_names:
                    Reporter.report_warning("Failed to update presets: [" + pack_name + "] " + ", ".join(failed_preset_names))
                legacy_ordered_preset_names = legacy_meta.get("order", [])
                pack.try_match_order(legacy_ordered_preset_names)
            else:
                pack = Context.load_pack(pack_name)
            Context.add_pack(pack)
            
            imported_packs.append(pack)
            import_pack_names.append(pack_name)
            last_imported_pack = pack
                
        imported_num = len(imported_packs)
        # count import infos
        if imported_num > 0:
            Context.select_pack(last_imported_pack)
            uic.select_pack(uic, last_imported_pack)
            if imported_num == file_num:
                if self.is_recovering:
                    self.report({'INFO'}, "Recovered successfully.")
                else:
                    self.report({'INFO'}, "Imported successfully.")
            else:
                self.report({'INFO'}, "Partially imported successfully.")
        elif file_num > 1:
            # no success but the user do selected file(s)
            self.report({'WARNING'}, "None of the selected packs were imported. See the previous infos.")
            Reporter.set_active_ops(None)
            return {'CANCELLED'}
        
        step = HS.step(self.bl_label, self)
        HS.set_created_paths(step, *[pack.pack_dir for pack in imported_packs])
        HS.set_undo(step, self.undo, [pack.name for pack in imported_packs], pack_before.name if pack_before else None, idx_before)
        HS.set_redo(step, self.redo, import_pack_names)
        
        HS.save_step(step)
        Reporter.set_active_ops(None)
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.is_recovering:
            self.directory = str(Context.fm.autosave_dir)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    
class HOTNODE_OT_export_pack(bpy.types.Operator):
    bl_idname = "hotnode.export_pack"
    bl_label = "Export Pack"
    bl_description = "Export the selected pack."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    # path of selected folder
    filepath: StringProperty(subtype="DIR_PATH") # type: ignore
    filename: StringProperty(subtype="FILE_NAME", default="") # type: ignore
    
    is_overwrite_if_exist: BoolProperty(
        name="Overwrite if Exist", 
        description="Overwrite existing files if they exist. If not checked, the re-named pack will get an unique name.",
        default=False
    ) # type: ignore

    def get_pack_enums(self, context):
        return ((name, name, "") for name in Context.packs.keys())
    
    packs_to_export: EnumProperty(
        name="Packs to Export",
        description="Select packs to export",
        items=get_pack_enums,
        options={'ENUM_FLAG'},
    ) # type: ignore

    @classmethod
    def poll(cls, context):
        return Context.get_pack_selected() is not None
    
    def execute(self, context):
        Reporter.set_active_ops(self)
        dst_dir = Context.fm.ensure_path_is_dir(self.filepath)
        existing_pack_names = Context.fm.read_dir_file_names(dst_dir, ".zip", cull_suffix=False)
        
        for pack_name in self.packs_to_export:
            pack = Context.get_pack(pack_name)
            if not self.is_overwrite_if_exist:
                pack_name = utils.ensure_unique_name(pack_name, existing_pack_names)
            dst_zip_path = dst_dir / f"{pack_name}.zip"
            Context.fm.zip_to(pack.pack_dir, dst_zip_path)
                
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.packs_to_export = set([Context.get_pack_selected().name])
        self.filename = ""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        row = layout.row()
        col = row.column()
        col.prop(self, "is_overwrite_if_exist")
        col.prop(self, "packs_to_export", text="Packs to Export")
        
        
class HOTNODE_OT_update_legacy_packs(Operator):
    bl_idname = "hotnode.update_legacy_packs"
    bl_label = "Update Legacy Packs"
    bl_description = "Load and update all packs saved with previous versions of Hot Node."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}
    
    @staticmethod
    def undo(uic: UIContext, pack_name_after, pack_name_before, idx_before):
        SS.sync() # using sync is very shuang O(∩_∩)O~
        if Context.get_pack_selected_name() == pack_name_after:
            pack = Context.select_pack(pack_name_before)
            uic.select_pack(uic, pack)
            if pack:
                Context.select_preset(idx_before)
                uic.select_preset(uic, idx_before)

    @staticmethod
    def redo(uic: UIContext, pack_name_after):
        SS.sync()
        pack = Context.select_pack(pack_name_after)
        uic.select_pack(uic, pack)

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic = context.window_manager.hot_node_ui_context
        pack_name_before = Context.get_pack_selected_name()
        idx_before = uic.preset_selected_idx
        
        autosave_packs_dir = Context.fm.autosave_dir
        zip_names = Context.fm.read_dir_file_names(autosave_packs_dir, ".zip", cull_suffix=False)
        legacy_autosave_zip_names = [name for name in zip_names if "_autosave_" in name]

        converted_packs = []
        for zip_name in legacy_autosave_zip_names:
            pack_name = utils.get_string_between_words(zip_name, None, ("_autosave_",))
            if pack_name is not None:
                src_zip_path = autosave_packs_dir / zip_name
                pack_name = utils.ensure_unique_name_for_item(pack_name, Context.ordered_packs)
                
                # unzip to new packs dir
                dst_pack_dir = Context.fm.packs_dir / pack_name
                Context.fm.unzip_to(src_zip_path, dst_pack_dir)
                
                # convert pack
                pack = Context.create_pack(pack_name)
                failed_preset_names, legacy_meta = VS.convert_pack_of_0_X_X(context, pack)
                if failed_preset_names:
                    Reporter.report_warning("Failed to update presets: [" + pack_name + "] " + ", ".join(failed_preset_names))
                legacy_ordered_preset_names = legacy_meta.get("order", [])
                pack.try_match_order(legacy_ordered_preset_names)
                Context.add_pack(pack)
                converted_packs.append(pack)

        if not converted_packs:
            Reporter.report_finish("No legacy packs found to update.")
            Reporter.set_active_ops(None)
            return {'CANCELLED'}
        
        Context.select_pack(converted_packs[-1])
        uic.select_pack(uic, converted_packs[-1])
        
        step = HS.step(self.bl_label, self)
        HS.set_created_paths(step, *[pack.pack_dir for pack in converted_packs])
        HS.set_undo(step, self.undo, converted_packs[-1].name, pack_name_before, idx_before)
        HS.set_redo(step, self.redo, converted_packs[-1].name)
        HS.save_step(step)
        
        Reporter.report_finish(
            f"All packs are updated.",
            f"Packs are partially updated, please check the previous reports for details."
        )
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    
    
class HOTNODE_OT_show_user_prefs(bpy.types.Operator):
    bl_idname = "hotnode.show_user_prefs"
    bl_label = "Hot Node Preferences"
    bl_description = "Open Blender's user preferences to the Hot Node addon section."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    def execute(self, context):
        Reporter.set_active_ops(self)
        try:
            bpy.data.window_managers["WinMan"].addon_search = "Hot Node"
        except Exception:
            pass
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT', section='ADDONS')
        
        addon_module = utils.get_addon_module()
        if addon_module is not None:
            bl_info = addon_utils.module_bl_info(addon_module)
            if not bl_info.get("show_expanded", True):
                bpy.ops.preferences.addon_expand(module=addon_module.__name__)
            
        Reporter.set_active_ops(None)
        return {'FINISHED'}
    

class HOTNODE_OT_refresh(Operator):
    bl_idname = "hotnode.refresh"
    bl_label = "Refresh"
    bl_description = "Refresh and load all packs and presets."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    def execute(self, context):
        Reporter.set_active_ops(self)
        SS.sync()
        Reporter.report_finish("Hot Node Refreshed.")
        Reporter.set_active_ops(None)
        return {'FINISHED'}


class HOTNODE_OT_undo(bpy.types.Operator):
    bl_idname = "hotnode.undo"
    bl_label = "Undo"
    bl_description = "Undo the last action. Hot Node history is isolated from Blender's history and shared across sessions."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return HS.has_steps()

    def execute(self, context):
        Reporter.set_active_ops(self)
        uic = context.window_manager.hot_node_ui_context
        
        try:
            step = HS.undo(uic)
        except Exception as e:
            Reporter.report_error("History data un-matched. History cleared.")
            HS.discard_jsteps(HS.jsteps)
            Reporter.set_active_ops(None)
            return {'CANCELLED'}

        Reporter.report_finish("Undo: " + step.name)
        Reporter.set_active_ops(None)
        return {'FINISHED'}


class HOTNODE_OT_redo(bpy.types.Operator):
    bl_idname = "hotnode.redo"
    bl_label = "Redo"
    bl_description = "Redo the last undone action. Hot Node history is isolated from Blender's history and shared across sessions."
    bl_translation_context = i18n_contexts.default
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return HS.has_undone_steps()

    def execute(self, context):
        Reporter.set_active_ops(self)
        
        uic = context.window_manager.hot_node_ui_context
        try:
            step = HS.redo(uic)
        except Exception as e:
            Reporter.report_error("History data un-matched. History cleared.")
            HS.discard_jsteps(HS.jundone_steps)
            Reporter.set_active_ops(None)
            return {'CANCELLED'}

        Reporter.report_finish("Redo: " + step.name)

        Reporter.set_active_ops(None)
        return {'FINISHED'}


classes = (
    HOTNODE_OT_clear_presets,
    HOTNODE_OT_add_preset,
    HOTNODE_OT_remove_preset,
    HOTNODE_OT_order_preset,
    HOTNODE_OT_overwrite_preset_with_selected_nodes,
    HOTNODE_OT_add_preset_nodes_to_tree,
    HOTNODE_OT_transfer_preset_to_pack,
    HOTNODE_OT_create_pack,
    HOTNODE_OT_remove_pack,
    HOTNODE_OT_select_pack,
    HOTNODE_OT_set_pack_icon,
    HOTNODE_OT_import_pack,
    HOTNODE_OT_export_pack,
    HOTNODE_OT_update_legacy_packs,
    HOTNODE_OT_show_user_prefs,
    HOTNODE_OT_refresh,
    HOTNODE_OT_undo,
    HOTNODE_OT_redo,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass


def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass