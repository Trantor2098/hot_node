import time

import bpy
from bpy.types import Menu, Panel, UIList, UILayout
from bpy.app.translations import (
    pgettext_iface as iface_,
    contexts as i18n_contexts,
)

from ..context.context import Context
from ...services.sync import SyncService as SS
from ...utils import constants
from ...utils import utils
from .ui_context import UIContext, UIPreset


class HOTNODE_MT_merged_add_nodes_packs(Menu):
    """A menu shows a pack's presets for user to get / modify / create / ..."""
    bl_label = "Add Nodes"
    
    def draw(self, context):
        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            return
        SS.ensure_sync_on_interval()
        for pack in Context.ordered_packs:
            if edit_tree.bl_idname in pack.meta.tree_types:
                pack_menu_cls = PackMenuManager.get_pack_menu_cls(pack.name)
                pack_menu_cls.mode = 'ADD_NODES'
                self.layout.menu(pack_menu_cls.__name__, text=pack.name, translate=False)
            
            
class HOTNODE_MT_merged_save_nodes_packs(Menu):
    """A menu shows a pack's presets for user to get / modify / create / ..."""
    bl_label = "Save Nodes"
    
    def draw(self, context):
        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            return
        SS.ensure_sync_on_interval()
        for pack in Context.ordered_packs:
            pack_menu_cls = PackMenuManager.get_pack_menu_cls(pack.name)
            pack_menu_cls.mode = 'SAVE_NODES'
            self.layout.menu(pack_menu_cls.__name__, text=pack.name, translate=False)


class HOTNODE_MT_pack(Menu):
    """(Will be dynamatically regisited) A menu shows a pack's presets for user to get / modify / create / ..."""
    bl_label = "Nodes"
    
    mode = 'ADD_NODES'  # ADD_NODES / SAVE_NODES
    
    def draw_add_nodes_ops(self, col: UILayout, preset_name):
        ops = col.operator("hotnode.add_preset_nodes_to_tree", text=preset_name, translate=False)
        ops.preset_name = preset_name
        ops.pack_name = self.bl_label
        
    def draw_save_nodes_ops(self, col: UILayout, preset_name):
        ops = col.operator("hotnode.overwrite_preset_with_selection", text=preset_name, translate=False)
        ops.preset_name = preset_name
        ops.pack_name = self.bl_label
        
    def draw_save_nodes_last_line_ops(self, col: UILayout, uic):
        col.prop(uic, "preset_name_for_creation", icon='BLANK1', text="", placeholder="  Save Nodes As...")
        
    def draw_presets_menu(self, context, draw_ops_func, draw_last_line_func = None):
        layout = self.layout
        space_data = context.space_data
        uic = context.window_manager.hot_node_ui_context
        new_tree = False
        if isinstance(space_data, bpy.types.SpaceNodeEditor):
            space_tree_type = space_data.tree_type
        elif isinstance(space_data, bpy.types.SpaceProperties):
            space_tree_type = "GeometryNodeTree"
            new_tree = True
        pack = Context.get_pack(self.bl_label)
        Context.current_pack_for_menu_drawing = pack # for fast preset creating
        
        row = layout.row()
        col = row.column()
        col.separator()
        for preset in pack.ordered_presets:
            if preset.meta.is_separator:
                col.separator()
            elif preset.meta.tree_type == space_tree_type or preset.meta.tree_type == constants.UNIVERSAL_NODE_TREE_IDNAME:
                draw_ops_func(col, preset.name)
        if draw_last_line_func is not None:
            draw_last_line_func(col, uic)
        
    def draw(self, context):
        if self.mode == 'ADD_NODES':
            self.draw_presets_menu(context, self.draw_add_nodes_ops)
        elif self.mode == 'SAVE_NODES':
            self.draw_presets_menu(context, self.draw_save_nodes_ops, self.draw_save_nodes_last_line_ops)
        # elif PackMenuManager.mode == 'ADD_GEO':
        #     self.draw_presets_menu_to_apply_geo(self, context)


class PackMenuManager:
    pack_menu_clses: dict[str, Menu] = {} # menu pool, <pack name>: <menu_cls>
    new_pack_menu_clses = []
    pack_menu_num = 0
    
    is_list_add_nodes_pack_menu_appended = False
    is_list_save_nodes_pack_menu_appended = False
    is_merged_add_nodes_packs_menu_appended = False
    is_merged_save_nodes_packs_menu_appended = False

    @staticmethod
    def draw_list_add_nodes_pack_menu(self: Menu, context):
        user_prefs = utils.get_user_prefs(context)
        if user_prefs.add_nodes_menu_mode == 'LIST':
            SS.ensure_sync_on_interval()
            self.layout.separator()
            for pack_name, pack_menu_cls in PackMenuManager.pack_menu_clses.items():
                pack_menu_cls.mode = 'ADD_NODES'
                self.layout.menu(pack_menu_cls.__name__, text=pack_name, translate=False)
                
    @staticmethod
    def draw_list_save_nodes_pack_menu(self: Menu, context):
        user_prefs = utils.get_user_prefs(context)
        if user_prefs.add_nodes_menu_mode == 'LIST':
            SS.ensure_sync_on_interval()
            self.layout.separator()
            for pack_name, pack_menu_cls in PackMenuManager.pack_menu_clses.items():
                pack_menu_cls.mode = 'SAVE_NODES'
                self.layout.menu(pack_menu_cls.__name__, icon='FILE_TICK', text=pack_name, translate=False)
       
    @staticmethod
    def draw_merged_add_nodes_packs_menu(self: Menu, context):
        user_prefs = utils.get_user_prefs(context)
        if user_prefs.add_nodes_menu_mode == 'MERGE':
            self.layout.separator()
            self.layout.menu("HOTNODE_MT_merged_add_nodes_packs", text=user_prefs.merged_add_nodes_menu_label)

    @staticmethod
    def draw_merged_save_nodes_packs_menu(self: Menu, context):
        user_prefs = utils.get_user_prefs(context)
        if user_prefs.save_nodes_menu_mode == 'MERGE':
            self.layout.separator()
            self.layout.menu("HOTNODE_MT_merged_save_nodes_packs", icon='FILE_TICK', text=user_prefs.merged_save_nodes_menu_label)

    @classmethod
    def on_register(cls):
        user_prefs = utils.get_user_prefs()
        cls.pack_menu_clses.clear()
        cls.new_pack_menu_clses.clear()
        cls.pack_menu_num = 0
        Context.add_packs_changed_listener(cls.ensure_existing_pack_menu)
        
        if user_prefs.add_nodes_menu_mode == 'LIST':
            cls.append_list_add_nodes_pack_menu()
        elif user_prefs.add_nodes_menu_mode == 'MERGE':
            cls.append_merged_add_nodes_packs_menu()
        if user_prefs.save_nodes_menu_mode == 'LIST':
            cls.append_list_save_nodes_pack_menu()
        elif user_prefs.save_nodes_menu_mode == 'MERGE':
            cls.append_merged_save_nodes_packs_menu()
        
        cls.ensure_existing_pack_menu()
        
    @classmethod
    def on_unregister(cls):
        Context.remove_packs_changed_listener(cls.ensure_existing_pack_menu)
        cls.remove_list_add_nodes_pack_menu()
        cls.remove_list_save_nodes_pack_menu()
        cls.remove_merged_add_nodes_packs_menu()
        cls.remove_merged_save_nodes_packs_menu()
        
    @classmethod
    def register_new_pack_menus(cls):
        for menu_cls in cls.new_pack_menu_clses:
            if not hasattr(bpy.types, menu_cls.__name__):
                try:
                    bpy.utils.register_class(menu_cls)
                except ValueError:
                    pass

    @classmethod
    def register_pack_menus(cls):
        for menu_cls in cls.pack_menu_clses.values():
            if not hasattr(bpy.types, menu_cls.__name__):
                try:
                    bpy.utils.register_class(menu_cls)
                except ValueError:
                    pass
                
    @classmethod
    def unregister_pack_menus(cls):
        for pack_menu_cls in cls.pack_menu_clses.values():
            try:
                bpy.utils.unregister_class(pack_menu_cls)
            except RuntimeError:
                pass
        cls.pack_menu_clses.clear()

    @classmethod
    def ensure_existing_pack_menu(cls, pack_name: str|None = None):
        ''' Ensure the pack menu class exists in the pool. Will check all packs if no pack_name is given. '''
        cls.new_pack_menu_clses.clear()
        # Here we create class for every appeared pack name, then the name is in the pool and we can reuse them when next time the name appears.
        # We will unregister them when blender is closed.
        pack_names = cls.pack_menu_clses.keys()
        if pack_name is None:
            for pack in Context.ordered_packs:
                if pack.name not in pack_names:
                    cls.new_pack_menu_clses.append(cls.create_pack_menu_cls(pack.name))
        elif pack_name not in pack_names:
            cls.new_pack_menu_clses.append(cls.create_pack_menu_cls(pack_name))
        # bpy.app.timers.register(_register_new_menus)
        # XXX More cost but safer
        bpy.app.timers.register(cls.register_pack_menus)
    
    @classmethod
    def create_pack_menu_cls(cls, pack_name: str) -> type[HOTNODE_MT_pack]:
        cls.pack_menu_num += 1
        menu_cls_name = f"HOTNODE_MT_pack_menu_{cls.pack_menu_num}"
        menu_cls = type(menu_cls_name, (HOTNODE_MT_pack,), {"bl_label": pack_name})
        cls.pack_menu_clses[pack_name] = menu_cls
        return menu_cls

    @classmethod
    def get_pack_menu_cls(cls, pack_name: str) -> type[Menu]|None:
        """Get the menu class name for a given pack."""
        return cls.pack_menu_clses.get(pack_name, None)
    
    @classmethod
    def append_list_add_nodes_pack_menu(cls):
        if cls.is_list_add_nodes_pack_menu_appended:
            return
        try:
            bpy.types.NODE_MT_add.append(cls.draw_list_add_nodes_pack_menu)
            cls.is_list_add_nodes_pack_menu_appended = True
        except ValueError:
            pass
        
    @classmethod
    def append_list_save_nodes_pack_menu(cls):
        if cls.is_list_save_nodes_pack_menu_appended:
            return
        try:
            bpy.types.NODE_MT_context_menu.append(cls.draw_list_save_nodes_pack_menu)
            cls.is_list_save_nodes_pack_menu_appended = True
        except ValueError:
            pass

    @classmethod
    def append_merged_add_nodes_packs_menu(cls):
        if cls.is_merged_add_nodes_packs_menu_appended:
            return
        try:
            bpy.types.NODE_MT_add.append(cls.draw_merged_add_nodes_packs_menu)
            cls.is_merged_add_nodes_packs_menu_appended = True
        except ValueError:
            pass
        
    @classmethod
    def append_merged_save_nodes_packs_menu(cls):
        if cls.is_merged_save_nodes_packs_menu_appended:
            return
        try:
            bpy.types.NODE_MT_context_menu.append(cls.draw_merged_save_nodes_packs_menu)
            cls.is_merged_save_nodes_packs_menu_appended = True
        except ValueError:
            pass
        
    @classmethod
    def remove_list_add_nodes_pack_menu(cls):
        if not cls.is_list_add_nodes_pack_menu_appended:
            return
        try:
            bpy.types.NODE_MT_add.remove(cls.draw_list_add_nodes_pack_menu)
            cls.is_list_add_nodes_pack_menu_appended = False
        except ValueError:
            pass
        
    @classmethod
    def remove_list_save_nodes_pack_menu(cls):
        if not cls.is_list_save_nodes_pack_menu_appended:
            return
        try:
            bpy.types.NODE_MT_context_menu.remove(cls.draw_list_save_nodes_pack_menu)
            cls.is_list_save_nodes_pack_menu_appended = False
        except ValueError:
            pass
    
    @classmethod
    def remove_merged_add_nodes_packs_menu(cls):
        if not cls.is_merged_add_nodes_packs_menu_appended:
            return
        try:
            bpy.types.NODE_MT_add.remove(cls.draw_merged_add_nodes_packs_menu)
            cls.is_merged_add_nodes_packs_menu_appended = False
        except ValueError:
            pass
    
    @classmethod
    def remove_merged_save_nodes_packs_menu(cls):
        if not cls.is_merged_save_nodes_packs_menu_appended:
            return
        try:
            bpy.types.NODE_MT_context_menu.remove(cls.draw_merged_save_nodes_packs_menu)
            cls.is_merged_save_nodes_packs_menu_appended = False
        except ValueError:
            pass
        # bpy.types.OBJECT_MT_modifier_add.remove(draw_ex_geo_add_menu)


class HOTNODE_MT_select_pack(Menu):
    bl_label = "Packs"
    
    def draw(self, context):
        uic = context.window_manager.hot_node_ui_context
        user_prefs = utils.get_user_prefs(context)
        space_tree_type = context.space_data.tree_type if context.space_data else None
        layout = self.layout
        if user_prefs.is_filter_pack_by_tree_type:
            packs = Context.get_ordered_packs_by_tree_type(space_tree_type)
        else:
            packs = Context.get_ordered_packs()
        for pack in packs:
            row = layout.row(align=True)
            col = row.column(align=True)
            col.scale_x = 0.1
            col.label(icon='BLANK1', text="")
            col = row.column(align=True)
            icon = pack.meta.icon
            ops = col.operator("hotnode.select_pack", icon=icon, text=pack.name, translate=False)
            ops.pack_name = pack.name
            ops.mode = 'BYNAME'


def draw_menu_transfer_preset_to_pack(menu: Menu, is_move: bool = False):
    layout = menu.layout
    layout.separator()
    for pack_name in Context.packs.keys():
        # if pack_name != Context.pack_selected.name:
        ops = layout.operator("hotnode.transfer_preset_to_pack", icon='OUTLINER_COLLECTION', text=pack_name, translate=False)
        ops.src_pack_name = Context.pack_selected.name
        ops.dst_pack_name = pack_name
        ops.preset_name = Context.preset_selected.name
        ops.is_move = is_move
    # TODO Non-selected pack...

         
class HOTNODE_MT_copy_preset_to_pack(Menu):
    bl_label = "Copy to Pack"
    bl_description = "Copy preset to another pack."

    def draw(self, context):
        draw_menu_transfer_preset_to_pack(self, is_move=False)
            
            
class HOTNODE_MT_move_preset_to_pack(Menu):
    bl_label = "Move to Pack"
    bl_description = "Move preset to another pack."
    
    def draw(self, context):
        draw_menu_transfer_preset_to_pack(self, is_move=True)


class HOTNODE_MT_pack_options(Menu):
    bl_label = "Pack Options"
    
    def draw(self, context):
        user_prefs = utils.get_user_prefs(context)
        uic: UIContext = context.window_manager.hot_node_ui_context
        preset = Context.preset_selected
        layout = self.layout
        
        row = layout.row(align=True)
        col = row.column(align=True)
        col.operator("hotnode.create_pack", icon='ADD').pack_name = iface_(user_prefs.default_pack_name)
        col.operator("hotnode.remove_pack", icon='REMOVE').pack_name = Context.get_pack_selected_name()
        
        if Context.get_pack_selected():
            col.separator()
            col.menu("HOTNODE_MT_pack_icons", icon='TAG', text="Choose an Icon...")
        
        col.separator()
        col.operator("hotnode.import_pack", text="Recover...").is_recovering = True
        col.operator("hotnode.import_pack", icon='IMPORT', text="Import Packs...")
        col.operator("hotnode.export_pack", icon='EXPORT', text="Export Packs...")


class HOTNODE_MT_preset_options(Menu):
    bl_label = "Preset Options"
    
    def draw(self, context):
        user_prefs = utils.get_user_prefs(context)
        uic: UIContext = context.window_manager.hot_node_ui_context
        preset = Context.preset_selected
        layout = self.layout

        # Refresh
        # layout.operator("hotnode.refresh", icon='FILE_REFRESH')
        # layout.operator("hotnode.repair_corruption", icon='FILE_REFRESH')

        # Move top / bottom
        # layout.separator()
        layout.operator("hotnode.order_preset", icon='TRIA_UP_BAR', text="Move to Top").direction = 'TOP'
        layout.operator("hotnode.order_preset", icon='TRIA_DOWN_BAR', text="Move to Bottom").direction = 'BOTTOM'

        # Preset to Pack
        if preset:
            preset_short_name = utils.ellipsis_with_tail_kept(preset.name)
            copy_text = iface_("Copy")
            move_text = iface_("Move")
            to_text = iface_("to")
            layout.separator()
            ops = layout.operator("hotnode.add_preset", icon='DUPLICATE', text="Duplicate")
            ops.preset_name = preset.name
            ops.pack_name = Context.get_pack_selected_name()
            ops.is_duplicate = True

            layout.menu("HOTNODE_MT_copy_preset_to_pack", icon='FILE', text=f"{copy_text} \"{preset_short_name}\" {to_text}")
            layout.menu("HOTNODE_MT_move_preset_to_pack", icon='FILE_HIDDEN', text=f"{move_text} \"{preset_short_name}\" {to_text}")

        # User Utils
        layout.separator()
        layout.operator("hotnode.clear_presets", icon='PANEL_CLOSE')


class HOTNODE_MT_pack_icons(Menu):
    '''A menu shows all icons that could be set to the pack'''
    bl_label = "Pack Icon"
    
    def draw_pack_icons(self, icons, separate=True, use_enter=True):
        layout = self.layout
        item_num = 0
        if separate:
            layout.separator(type='SPACE')
        row = layout.row(align=True)
        row.label(icon='BLANK1', text="")
        row.label(icon='BLANK1', text="")
        row.scale_x = 1.12
        for icon in icons:
            if use_enter:
                if item_num >= 9:
                    item_num = 1
                    layout.separator(type='SPACE')
                    row = layout.row(align=True)
                    row.label(icon='BLANK1', text="")
                    row.label(icon='BLANK1', text="")
                    row.scale_x = 1.12
                else:
                    item_num += 1
            if constants.BLENDER_ICONS.get(icon) is None:
                icon = 'BLANK1'
            ops = row.operator("hotnode.set_pack_icon", text="", icon=icon)
            ops.icon = icon
            ops.pack_name = Context.pack_selected.name
    
    def draw(self, context):
        layout = self.layout
        
        self.draw_pack_icons(constants.PACK_ICONS, separate=False)


class HOTNODE_UL_presets(UIList):
    
    def draw_item(self, context, layout: UILayout, data, item, icon, active_data, active_propname, index):
        ui_preset: UIPreset = item
        preset = Context.pack_selected.get_preset(ui_preset.name)
        
        if preset is None:
            layout.prop(ui_preset, "name", text="", emboss=False, icon='ERROR')
            return
        
        icon = constants.ICON_BY_TREE_TYPE_IDNAME.get(preset.meta.tree_type, 'NODETREE')
        layout.prop(ui_preset, "name", text="", emboss=False, icon=icon, translate=False)

    
class HOTNODE_PT_main(Panel):
    bl_label = "Hot Node"
    bl_idname = "HOTNODE_PT_main"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Hot Node"
    bl_translation_context = i18n_contexts.default

    # dy_info: str|None = None
    # dy_info_icon: str|None = None
    # dy_sub_infos: tuple[str]|None = None
    # dy_info_born_time = 0.0
    # dy_info_duration = 3.0
    
    # @classmethod
    # def set_dynamic_info(cls, info: str, main_icon: str|None = None, sub_infos: tuple[str]|None = None, duration: float = 3.0):
    #     cls.dy_info = info
    #     cls.dy_info_icon = main_icon
    #     cls.dy_sub_infos = sub_infos
    #     cls.dy_info_born_time = time.time()
    #     cls.dy_info_duration = duration
        
    # @classmethod
    # def get_or_expire_dynamic_info(cls):
    #     if cls.dy_info is None:
    #         return None, None, None
    #     if time.time() - cls.dy_info_born_time > cls.dy_info_duration:
    #         cls.dy_info = None
    #         cls.dy_info_icon = None
    #         cls.dy_sub_infos = None
    #         return None, None, None
    #     return cls.dy_info, cls.dy_info_icon, cls.dy_sub_infos

    def draw(self, context):
        SS.ensure_sync_on_interval()
        layout = self.layout
        uic = context.window_manager.hot_node_ui_context
        user_prefs = utils.get_user_prefs(context)
        pack = Context.get_pack_selected()
        preset = Context.get_preset_selected()
        preset_name = Context.preset_selected.name if Context.preset_selected is not None else ""
        pack_name = Context.pack_selected.name if Context.pack_selected is not None else ""
        
        # Pack Bar
        row = layout.row(align=True)
        
        if pack:
            row.scale_x = 1.75 # this helps to show the dropdown icon
            row.menu("HOTNODE_MT_select_pack", icon=pack.meta.icon if pack is not None else 'OUTLINER_COLLECTION', text="")
            row.scale_x = 1.0
            row.prop(uic, "pack_selected_name", text="", placeholder="Select a pack...", translate=False)
            row.menu("HOTNODE_MT_pack_options", icon='DOWNARROW_HLT', text="")
            row.separator(factor=1.5)
            row.popover("HOTNODE_PT_edit", icon='COLLAPSEMENU', text="")
            
            # Filter pack by tree type
            if (
                user_prefs.is_filter_pack_by_tree_type 
                and pack 
                and preset 
                and context.space_data.tree_type not in pack.meta.tree_types 
                and constants.UNIVERSAL_NODE_TREE_IDNAME not in pack.meta.tree_types
            ):
                packs_in_type = Context.get_ordered_packs_by_tree_type(context.space_data.tree_type)
                utils.late_select_pack(packs_in_type[0].name if packs_in_type else "")
        else:
            row.operator("hotnode.create_pack", icon='ADD').pack_name = iface_(user_prefs.default_pack_name)
            row.menu("HOTNODE_MT_pack_options", icon='DOWNARROW_HLT', text="")
            row.separator(factor=1.5)
            row.popover("HOTNODE_PT_edit", icon='COLLAPSEMENU', text="")
            
            if user_prefs.is_show_load_legacy_packs_button:
                layout.separator()
                row = layout.row(align=True)
                row.operator("hotnode.update_legacy_packs", text="Load & Update Legacy Packs")
                row = layout.row(align=True)
                row.prop(user_prefs, "is_show_load_legacy_packs_button", text="Show this button")
            return
        
        # Presets List
        layout.separator(factor=0.1)
        row = layout.row()
        
        # For UI list
        lcol = row.column(align=True)
        rows = 3 if len(pack.presets) < 2 else 5
        
        # Add / Remove Preset
        rcol = row.column(align=True)
        ops = rcol.operator("hotnode.add_preset", icon='ADD', text="")
        ops.pack_name = pack_name
        ops.preset_name = iface_(user_prefs.default_preset_name)
        ops.is_duplicate = False
        ops = rcol.operator("hotnode.remove_preset", icon='REMOVE', text="")
        ops.pack_name = pack_name
        ops.preset_name = preset_name
        rcol.separator()
        
        # Specials Menu
        rcol.menu("HOTNODE_MT_preset_options", icon='DOWNARROW_HLT', text="")
        
        if 'OVERWRITE_TREE_IO' in user_prefs.sidebar_items:
            rows += 2
            rcol.separator(factor=1.5)
            rcol.separator()
            rcol.prop(user_prefs, "is_overwrite_tree_io", icon='NODE', text="")
        if 'PACKS' in user_prefs.sidebar_items:
            rows += len(Context.get_ordered_packs()) + 1
            rcol.separator(factor=1.5)
            for pack in Context.get_ordered_packs():
                icon = pack.meta.icon
                ops = rcol.operator("hotnode.select_pack", icon=icon, text="")
                ops.pack_name = pack.name
                ops.mode = 'BYNAME'
        if 'TRANSFER_PRESET' in user_prefs.sidebar_items:
            rows += 4
            rcol.separator(factor=1.5)
            ops = rcol.operator("hotnode.add_preset", icon='DUPLICATE', text="")
            ops.preset_name = preset.name if preset else ""
            ops.pack_name = Context.get_pack_selected_name()
            ops.is_duplicate = True
            rcol.operator("wm.call_menu", icon='FILE', text="").name = "HOTNODE_MT_copy_preset_to_pack"
            rcol.operator("wm.call_menu", icon='FILE_HIDDEN', text="").name = "HOTNODE_MT_move_preset_to_pack"
        if 'UNDO_REDO' in user_prefs.sidebar_items:
            rows += 3
            rcol.separator(factor=1.5)
            rcol.operator("hotnode.undo", icon='LOOP_BACK', text="")
            rcol.operator("hotnode.redo", icon='LOOP_FORWARDS', text="")
        if 'REFRESH' in user_prefs.sidebar_items:
            rows += 1
            rcol.separator(factor=1.5)
            rcol.operator("hotnode.refresh", icon='FILE_REFRESH', text="")
        if 'PREFERENCES' in user_prefs.sidebar_items:
            rows += 2
            rcol.separator(factor=1.5)
            rcol.operator("hotnode.show_user_prefs", icon='PREFERENCES', text="")
            
        rows = max(rows, user_prefs.min_ui_list_length)
        
        # Move up & down
        if rows >= 5:
            rcol.separator()
            rcol.operator("hotnode.order_preset", icon='TRIA_UP', text="").direction = 'UP'
            rcol.operator("hotnode.order_preset", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        # Draw UI list
        lcol.template_list(
            "HOTNODE_UL_presets", "", 
            uic, "presets",
            uic, "preset_selected_idx", 
            rows=rows
        )
           
        # Preset Usage UI
        layout.separator(factor=0.1)
        row = layout.row()
        # row.scale_y = 1.25
        ops = row.operator("hotnode.add_preset_nodes_to_tree", text="Get")
        ops.preset_name = preset_name
        ops.pack_name = pack_name
        
        ops = row.operator("hotnode.overwrite_preset_with_selection", icon='GREASEPENCIL', text="")
        ops.preset_name = preset_name
        ops.pack_name = pack_name

        # Dynamic Info
        # dy_info, dy_info_icon, dy_sub_infos = self.get_or_expire_dynamic_info()
        # if dy_info is not None:
        #     if time.time() - self.dy_info_born_time < self.dy_info_duration:
        #         row = layout.row()
        #         row.label(text=dy_info, icon=dy_info_icon)
        #         if dy_sub_infos is not None:
        #             for info in dy_sub_infos:
        #                 row = layout.row()
        #                 row.label(text=info, icon='BLANK1')


class HOTNODE_PT_edit(Panel):
    bl_label = "Edit"
    bl_idname = "HOTNODE_PT_edit"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Hot Node"
    bl_options = {'INSTANCED'}
    
    def draw(self, context):
        uic = context.window_manager.hot_node_ui_context
        user_prefs = utils.get_user_prefs(context)
        layout = self.layout
        # layout.use_property_split = True
        # layout.use_property_decorate = False
        
        col = layout.column()
        
        row = col.row(align=True)
        row.operator("hotnode.undo", icon='LOOP_BACK')
        # row.operator("hotnode.refresh", icon='FILE_REFRESH', text="")
        row.operator("hotnode.redo", icon='LOOP_FORWARDS')
        
        # Preset Usage
        col.separator(factor=2)
        col.label(text="Node Tree")
        col.prop(user_prefs, "is_overwrite_tree_io")
        row = col.row(align=True)
        row.prop(user_prefs, "node_tree_reuse_mode", expand=True)
        
        col.separator(factor=2)
        col.label(text="Image")
        sub = col.column(align=True)
        iii = sub.row(align=True)
        iii.prop(user_prefs, "dir_to_match_image", text="", icon='FILE_IMAGE', placeholder="Directory to match images")
        iii = sub.row(align=True)
        iii.active = user_prefs.dir_to_match_image != ""
        iii.prop(user_prefs, "image_name_filter", text="", icon='FILTER', placeholder="Image Name Filter")
        
        # Data
        col.separator(factor=2)
        col.label(text="Data")
        col.prop(user_prefs, "data_dir", icon='ASSET_MANAGER', text="")
        
        # Others
        col.separator(factor=2)
        col.label(text="Others")
        row = col.row(align=True)
        row.operator("hotnode.refresh", icon='FILE_REFRESH', text="")
        row.operator("hotnode.show_user_prefs", icon='PREFERENCES', text="")


classes = (
    HOTNODE_MT_select_pack,
    HOTNODE_MT_copy_preset_to_pack,
    HOTNODE_MT_move_preset_to_pack,
    HOTNODE_MT_preset_options,
    HOTNODE_MT_merged_add_nodes_packs,
    HOTNODE_MT_merged_save_nodes_packs,
    HOTNODE_MT_pack_options,
    HOTNODE_MT_pack_icons,
    HOTNODE_UL_presets,
    HOTNODE_PT_main,
    HOTNODE_PT_edit,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass # already registered
        
    PackMenuManager.on_register()


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    PackMenuManager.on_unregister()
