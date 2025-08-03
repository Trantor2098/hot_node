import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    IntProperty,
)
from bpy.app.translations import (
    pgettext_iface as iface_,
)

from ..context.context import Context
from ...services.history import HistoryService as HS
from ...utils import utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..context.pack import Pack
    from ..context.preset import Preset

class UpdateHandler():
    
    is_skip_pack_rename_callback = False
    is_skip_preset_rename_callback = False
    is_skip_preset_name_for_creation_callback = False
    is_skip_pack_name_for_creation_callback = False
    is_skip_preset_selected_idx_callback = False
    is_skip_step_flag_update = False
    
    @staticmethod
    def set_all_skip_flags(is_skip_all: bool):
        """Skip all update handlers."""
        UpdateHandler.is_skip_pack_rename_callback = is_skip_all
        UpdateHandler.is_skip_preset_rename_callback = is_skip_all
        UpdateHandler.is_skip_preset_name_for_creation_callback = is_skip_all
        UpdateHandler.is_skip_preset_selected_idx_callback = is_skip_all
        UpdateHandler.is_skip_step_flag_update = is_skip_all
        
    @staticmethod
    def preset_name_update_undo_redo(uic: 'UIContext', pack_name, old_name, new_name, idx):
        pack = Context.get_pack(pack_name)
        if not Context.is_pack_selected(pack):
            Context.select_pack(pack)
            uic.select_pack(pack)
            
        UpdateHandler.is_skip_preset_rename_callback = True
        uic.presets[idx].name = old_name
        UpdateHandler.is_skip_preset_rename_callback = False
        
        preset = pack.get_preset(new_name)
        pack.rename_preset(preset, old_name)
        pack.set_preset_separator(preset, utils.is_str_only_dash(old_name))
        Context.pack_selected.save_metas()
    
    @staticmethod
    def preset_name_update(ui_preset: 'UIPreset', context):
        # callback when user changed the preset name, but skip if we are moving position / creating new preset
        if UpdateHandler.is_skip_preset_rename_callback:
            return
        
        preset = Context.get_preset_selected()
        if preset is None:
            return
        pack = Context.get_pack_selected()
        old_name = preset.name
        ordered_names = pack.meta.ordered_preset_names
        
        uic: UIContext = context.window_manager.hot_node_ui_context
        ui_presets: bpy.types.CollectionProperty = uic.presets
        
        if ui_preset != ui_presets[uic.preset_selected_idx]:
            # if user is setting a name that is not selected (UI bug of blender), select the preset that is being renamed first
            for i, preset_name in enumerate(ui_presets.keys()):
                if preset_name == ui_preset.name and i != uic.preset_selected_idx:
                    # now i is the index of the preset that is being renamed
                    UpdateHandler.is_skip_preset_selected_idx_callback = True
                    uic.preset_selected_idx = i
                    UpdateHandler.is_skip_preset_selected_idx_callback = False
                    Context.select_preset(ordered_names[i])
                    break
        
        new_name = utils.delete_slash_anti_slash_in_string(ui_preset.name)
        
        if new_name == "":
            uic.rename_preset_selected(uic, old_name)
            return
        
        if pack.name == new_name:
            return
        
        # Do rename
        pack.set_preset_separator(preset, utils.is_str_only_dash(new_name))
        new_name = utils.ensure_unique_name(new_name, ordered_names, uic.preset_selected_idx)
        uic.rename_preset_selected(uic, new_name)
        
        pack.rename_preset(Context.preset_selected, new_name)
        pack.save_metas()
        
        step = HS.step("Rename Preset", UpdateHandler)
        HS.set_undo(step, UpdateHandler.preset_name_update_undo_redo, pack.name, old_name, new_name, uic.preset_selected_idx)
        HS.set_redo(step, UpdateHandler.preset_name_update_undo_redo, pack.name, new_name, old_name, uic.preset_selected_idx)
        HS.save_step(step)
        
    @staticmethod
    def preset_selected_idx_update(uic: 'UIContext', context: bpy.types.Context):
        """Update the preset selected index."""
        if UpdateHandler.is_skip_preset_selected_idx_callback:
            return
        if len(uic.presets) > 0:
            Context.select_preset(uic.presets[uic.preset_selected_idx].name)
        else:
            Context.select_preset(None)
            
    @staticmethod
    def pack_selected_name_undo_redo(uic: 'UIContext', old_name, new_name):
        pack = Context.get_pack(new_name)
        if not Context.is_pack_selected(pack):
            Context.select_pack(pack)
            uic.select_pack(uic, pack)
            
        Context.rename_pack(pack, old_name)
        uic.rename_pack_selected(uic, old_name)
        
    @staticmethod
    def pack_selected_name_update(uic: 'UIContext', context: bpy.types.Context):
        if UpdateHandler.is_skip_pack_rename_callback:
            return
        
        if Context.pack_selected is None:
            # no pack selected, keep name socket empty
            uic.rename_pack_selected(uic, "")
            return
        
        new_name = uic.pack_selected_name
        new_name = utils.delete_slash_anti_slash_in_string(new_name)
        old_name = Context.pack_selected.name
        
        if Context.pack_selected.name == new_name:
            return
        if new_name == "":
            # empty name is not allowed, reset to old name
            uic.rename_pack_selected(old_name)
            return
        
        # do rename
        pack_names = list(Context.packs.keys())
        old_name_idx = pack_names.index(old_name)
        new_name = utils.ensure_unique_name(new_name, pack_names, old_name_idx)
        Context.rename_pack_selected(new_name)
        
        step = HS.step(iface_("Rename Pack"), UpdateHandler)
        HS.set_undo(step, UpdateHandler.pack_selected_name_undo_redo, old_name, new_name)
        HS.set_redo(step, UpdateHandler.pack_selected_name_undo_redo, new_name, old_name)
        HS.save_step(step)
        
    @staticmethod
    def preset_name_for_creation_update_undo(uic: 'UIContext', pack_name, preset_name, idx_before):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        pack.remove_preset(preset_name) # this will save pack meta
        pack.save_metas()
        Context.select_preset(idx_before)
        uic.remove_preset(uic, len(uic.presets) - 1)
        uic.select_preset(uic, idx_before)
    
    @staticmethod
    def preset_name_for_creation_update_redo(uic: 'UIContext', pack_name, preset_name):
        pack = Context.select_pack(pack_name)
        if not uic.is_pack_selected(uic, pack):
            uic.select_pack(uic, pack)
        preset = pack.create_preset(preset_name)
        pack.add_preset(preset)
        pack.save_metas()
        Context.select_preset(preset_name)
        uic.add_preset(uic, preset)
        uic.select_preset(uic, len(pack.presets) - 1)
        
    @staticmethod
    def preset_name_for_creation_update(uic: 'UIContext', context):
        if UpdateHandler.is_skip_preset_name_for_creation_callback:
            return
        
        pack = Context.current_pack_for_menu_drawing
        new_name = utils.delete_slash_anti_slash_in_string(uic.preset_name_for_creation)
        new_name = utils.ensure_unique_name_for_item(new_name, pack.ordered_presets)
        
        if new_name == "":
            uic.reset_preset_name_for_creation()
            return
        
        if not Context.is_pack_selected(pack):
            Context.select_pack(pack)
            uic.select_pack(uic, pack)
            
        idx_before = uic.preset_selected_idx
        preset = pack.create_preset(new_name)
        pack.add_preset(preset)
        uic.add_preset(uic, preset)
        Context.select_preset(preset)
        
        step = HS.step(iface_("Create Preset"), UpdateHandler)
        HS.set_changed_paths(step, pack.meta_path)
        HS.set_created_paths(step, preset.path)
        
        pack.overwrite_preset(preset, context)
        pack.save_metas()
        
        HS.set_undo(step, UpdateHandler.preset_name_for_creation_update_undo, pack.name, preset.name, idx_before)
        HS.set_redo(step, UpdateHandler.preset_name_for_creation_update_redo, pack.name, preset.name)
        HS.save_step(step)
        
    @staticmethod
    def pack_name_for_creation_update_undo(uic: 'UIContext', new_pack_name, prev_pack_selected_name, idx_before):
        if Context.get_pack_selected_name() == new_pack_name:
            pack = Context.select_pack(prev_pack_selected_name)
            uic.select_pack(uic, pack)
            if pack:
                Context.select_preset(idx_before)
                uic.select_preset(uic, idx_before)
        Context.remove_pack(new_pack_name)
        
    @staticmethod
    def pack_name_for_creation_update_redo(uic: 'UIContext', new_pack_name):
        pack = Context.load_pack(new_pack_name)
        Context.add_pack(pack)
        Context.select_pack(pack)
        uic.select_pack(uic, pack)
        
    @staticmethod
    def pack_name_for_creation_update(uic: 'UIContext', context):
        if UpdateHandler.is_skip_pack_name_for_creation_callback:
            return
        
        new_name = uic.pack_name_for_creation
        if new_name == "":
            uic.reset_pack_name_for_creation(uic)
            return
        
        prev_pack_selected_name = Context.get_pack_selected_name()
        idx_before = uic.preset_selected_idx
        new_name = utils.ensure_unique_name_for_item(new_name, Context.get_ordered_packs())
        pack = Context.create_pack(new_name)
        Context.add_pack(pack)
        Context.select_pack(pack)
        uic.select_pack(uic, pack)
        uic.reset_pack_name_for_creation(uic)

        step = HS.step(iface_("Create Pack"), UpdateHandler)
        HS.set_undo(step, UpdateHandler.pack_name_for_creation_update_undo, new_name, prev_pack_selected_name, idx_before)
        HS.set_redo(step, UpdateHandler.pack_name_for_creation_update_redo, new_name)
        HS.save_step(step)
        
class UIPreset(bpy.types.PropertyGroup):
    '''Info class of node preset, will be used for UI, OPS'''
    name: StringProperty(
        name="Node Preset",
        default="Preset",
        update=UpdateHandler.preset_name_update
    ) # type: ignore
            
class UIContext(bpy.types.PropertyGroup):
    """Data in the UI that exposed to the user which can be changed. Our logic gets user input from this class."""
    
    # preset in pack_selected, For listing presets in the template_list UI
    presets: CollectionProperty(
        name="Presets",
        type=UIPreset,
    ) # type: ignore

    # For recording the current preset selected index in the right panel's template_list UI
    preset_selected_idx: IntProperty(
        name="Preset Selected Index",
        update=UpdateHandler.preset_selected_idx_update,
    ) # type: ignore
        
    # for user to change pack name. Empty str "" means no pack selected.
    pack_selected_name: StringProperty(
        name="Pack Selected Name",
        description="The name of the currently selected pack.",
        default=Context.pack_selected.name if Context.pack_selected is not None else "",
        update=UpdateHandler.pack_selected_name_update,
    ) # type: ignore
    
    # for user to fast create preset.
    preset_name_for_creation: StringProperty(
        name="Preset Name for Creation",
        default="",
        description="Preset name for creation, will be used when creating a new preset",
        update=UpdateHandler.preset_name_for_creation_update,
    ) # type: ignore
    
    pack_name_for_creation: StringProperty(
        name="Pack Name for Creation",
        default="",
        description="Pack name for creation, will be used when creating a new preset",
        update=UpdateHandler.pack_name_for_creation_update,
    ) # type: ignore
    
    @staticmethod
    def initialize():
        """
        CALL THIS AFTER the Context was loaded. Sync the UI context with the current context when blender started. 
        Use app.timers to ensure the context is ready.
        """
        uic: UIContext = bpy.context.window_manager.hot_node_ui_context
        UpdateHandler.set_all_skip_flags(True) # skip all update handlers
        uic.clear_presets(uic)
        uic.pack_selected_name = ""
        UpdateHandler.set_all_skip_flags(False) # skip all update handlers
        uic.select_pack(uic, Context.pack_selected)
    
    # NOTE ACCESSING Context IN THIS CLASS IS NOT ALLOWED
    # NOTE Pass uic (comes from operator context) instead of using self so that the undo/redo can br applied to the uic by blender
    @staticmethod
    def add_preset(uic: 'UIContext', preset: 'Preset', dst_idx: int|None = None, is_select: bool = True):
        """Add a preset to the current pack. Will select it."""
        uic_presets = uic.presets
        uic_presets.add()
        last_idx = len(uic_presets) - 1
        if dst_idx is None:
            dst_idx = last_idx
        else:
            uic.order_preset(uic, last_idx, dst_idx)
        UpdateHandler.is_skip_preset_rename_callback = True
        uic_presets[dst_idx].name = preset.name
        UpdateHandler.is_skip_preset_rename_callback = False
        if is_select:
            UpdateHandler.is_skip_preset_selected_idx_callback = True
            uic.preset_selected_idx = dst_idx
            UpdateHandler.is_skip_preset_selected_idx_callback = False
            
    @staticmethod
    def rename_preset_selected(uic: 'UIContext', new_name):
        UpdateHandler.is_skip_preset_rename_callback = True
        uic.presets[uic.preset_selected_idx].name = new_name
        UpdateHandler.is_skip_preset_rename_callback = False
        
    @staticmethod
    def select_preset(uic: 'UIContext', preset: 'str|int|Preset|None'):
        """Idx is faster"""
        UpdateHandler.is_skip_preset_selected_idx_callback = True
        if preset is None:
            uic.preset_selected_idx = -1
        if isinstance(preset, int):
            uic.preset_selected_idx = preset
        elif isinstance(preset, str):
            for idx, ui_preset in enumerate(uic.presets):
                if ui_preset.name == preset:
                    uic.preset_selected_idx = idx
                    break
        else:
            for idx, ui_preset in enumerate(uic.presets):
                if ui_preset.name == preset.name:
                    uic.preset_selected_idx = idx
                    break
        UpdateHandler.is_skip_preset_selected_idx_callback = False
        
    @staticmethod
    def remove_preset(uic: 'UIContext', preset: 'Preset|str|int'):
        if isinstance(preset, int):
            uic.remove_preset_by_idx(uic, preset)
        elif isinstance(preset, str):
            uic.remove_preset_by_name(uic, preset)
        else:
            uic.remove_preset_by_name(uic, preset.name)

    @staticmethod
    def remove_preset_by_idx(uic: 'UIContext', idx: int):
        """Remove a preset from the current pack by index."""
        length = len(uic.presets)
        if idx == length - 1:
            UpdateHandler.is_skip_preset_selected_idx_callback = True
            uic.preset_selected_idx -= 1
            UpdateHandler.is_skip_preset_selected_idx_callback = False
        uic.presets.remove(idx)
        
    @staticmethod
    def remove_preset_by_name(uic: 'UIContext', preset_name: str):
        """Remove a preset from the current pack."""
        for idx, preset in enumerate(uic.presets):
            if preset.name == preset_name:
                uic.remove_preset_by_idx(uic, idx)
                return
        
    @staticmethod
    def remove_preset_selected(uic: 'UIContext'):
        length = len(uic.presets)
        if length <= 0:
            return 
        idx = uic.preset_selected_idx
        uic.presets.remove(idx)
        if idx == length - 1:
            UpdateHandler.is_skip_preset_selected_idx_callback = True
            uic.preset_selected_idx -= 1
            UpdateHandler.is_skip_preset_selected_idx_callback = False
            
    @staticmethod
    def clear_presets(uic: 'UIContext'):
        """Clear all presets in the current pack."""
        uic.presets.clear()
        uic.preset_selected_idx = -1
    
    @staticmethod
    def order_preset(uic: 'UIContext', src_idx: int, dst_idx: int):
        """Order the preset in the current pack."""
        UpdateHandler.is_skip_preset_rename_callback = True
        UpdateHandler.is_skip_preset_selected_idx_callback = True
        ui_preset: UIPreset = uic.presets[src_idx]
        # uic.presets.move(src_idx, dst_idx)
        src_name = ui_preset.name
        if src_idx > dst_idx:
            for i in range(src_idx - dst_idx):
                uic.presets[src_idx - i].name = uic.presets[src_idx - i - 1].name
        elif src_idx < dst_idx:
            for i in range(src_idx, dst_idx):
                uic.presets[i].name = uic.presets[i + 1].name
        else:
            UpdateHandler.is_skip_preset_selected_idx_callback = False
            UpdateHandler.is_skip_preset_rename_callback = False
            return
        uic.presets[dst_idx].name = src_name
        uic.preset_selected_idx = dst_idx
        UpdateHandler.is_skip_preset_selected_idx_callback = False
        UpdateHandler.is_skip_preset_rename_callback = False
        
    @staticmethod
    def reset_preset_name_for_creation(uic: 'UIContext'):
        UpdateHandler.is_skip_preset_name_for_creation_callback = True
        uic.pack_name_for_creation = ""
        UpdateHandler.is_skip_preset_name_for_creation_callback = False
        
    @staticmethod
    def rename_pack_selected(uic: 'UIContext', new_name):
        UpdateHandler.is_skip_pack_rename_callback = True
        uic.pack_selected_name = new_name
        UpdateHandler.is_skip_pack_rename_callback = False
    
    @staticmethod   
    def select_pack(uic: 'UIContext', pack: 'Pack|None'):
        """Select a pack and load it's presets to ui, None to deselect."""
        uic.presets.clear()
        if pack:
            pack_name = pack.name
            for preset in pack.ordered_presets:
                uic.add_preset(uic, preset, is_select=False)
            uic.preset_selected_idx = 0 if pack.ordered_presets else -1
        else:
            pack_name = ""
            uic.preset_selected_idx = -1
        UpdateHandler.is_skip_pack_rename_callback = True
        uic.pack_selected_name = pack_name
        UpdateHandler.is_skip_pack_rename_callback = False
        
    @staticmethod   
    def is_pack_selected(uic: 'UIContext', pack: 'Pack|str|None'):
        """Select a pack and load it's presets to ui, None to deselect."""
        if pack is None and uic.pack_selected_name == "":
            return True
        pack_name = pack if isinstance(pack, str) else pack.name
        if pack_name == uic.pack_selected_name:
            return True
        return False
    
    @staticmethod
    def reset_pack_name_for_creation(uic: 'UIContext'):
        UpdateHandler.is_skip_pack_name_for_creation_callback = True
        uic.pack_name_for_creation = ""
        UpdateHandler.is_skip_pack_name_for_creation_callback = False
    
classes = (
    UIPreset,
    UIContext,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            # already registered
            pass
    
    bpy.types.WindowManager.hot_node_ui_context = bpy.props.PointerProperty(
        name="Hot Node UI Context",
        type=UIContext
    ) # type: ignore
    # bpy.types.Scene.hot_node_ui_context = bpy.props.PointerProperty(
    #     name="Hot Node UI Context",
    #     type=UIContext
    # ) # type: ignore
    
    bpy.app.timers.register(UIContext.initialize)
    

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        
    if hasattr(bpy.types.Scene, "hot_node_ui_context"):
        del bpy.types.WindowManager.hot_node_ui_context
        # del bpy.types.Scene.hot_node_ui_context