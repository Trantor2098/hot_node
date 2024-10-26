import bpy
from bpy.types import Menu, Panel, UIList

import time

from . import file, props_py, sync, i18n


type_icon = {
    "ShaderNodeTree": 'NODE_MATERIAL',
    "GeometryNodeTree": 'GEOMETRY_NODES',
    "CompositorNodeTree": 'NODE_COMPOSITING',
    "TextureNodeTree": 'NODE_TEXTURE',
}

# menu pool, <pack name>: <Menu name>
packs_Menus = {}
new_Menus = []
_pack_menu_num = 0

pack_menus_mode = 'ADD_NODES'

last_darw_time = 0.0

gui_info = None
gui_info_duration = 3.0
gui_info_icon = None
gui_info_born_time = 0.0


def set_gui_info(messages: list[str], duration: float=3.0, icon: str|None=None):
    global gui_info, gui_info_duration, gui_info_icon, gui_info_born_time
    gui_info = messages
    gui_info_duration = duration
    gui_info_icon = icon
    gui_info_born_time = time.time()
    
    
# draw ex > draw MT_packs > draw menus > draw MT_pack > draw menu
def draw_ex_nodes_add_menu(self, context):
    global pack_menus_mode
    pack_menus_mode = 'ADD_NODES'
    if context.preferences.addons[__package__].preferences.in_one_menu:
        self.layout.separator()
        self.layout.menu("HOTNODE_MT_packs", text=i18n.msg["Nodes"])
    else:
        draw_nodes_add_menus(self, context)
        
        
def draw_ex_geo_add_menu(self, context):
    global pack_menus_mode
    pack_menus_mode = 'ADD_GEO'
    self.layout.separator()
    self.layout.menu("HOTNODE_MT_packs", icon='GEOMETRY_NODES', text=i18n.msg["Nodes"])
    
    
def draw_ex_nodes_save_menu(self, context):
    global pack_menus_mode
    pack_menus_mode = 'SAVE_NODES'
    self.layout.separator()
    self.layout.menu("HOTNODE_MT_packs", icon='FILE_TICK', text=i18n.msg["Save Nodes"])
        
        
def draw_nodes_save_menus(self: Menu, context: bpy.types.Context):
    edit_tree = context.space_data.edit_tree
    if edit_tree is None:
        return
    if props_py.gl_packs != {}:
        for pack_name in props_py.gl_packs.keys():
            pack_Menu = packs_Menus.get(pack_name, None)
            self.layout.menu(pack_Menu.__name__, text=pack_name, translate=False)
                
                
def draw_nodes_add_menus(self: Menu, context: bpy.types.Context):
    edit_tree = context.space_data.edit_tree
    if edit_tree is None:
        return
    if props_py.gl_packs != {}:
        top_one = True
        # bpy.app.timers.register(_register_existing_menus)
        for pack_name in props_py.gl_packs.keys():
            if edit_tree.bl_idname in file.get_pack_types(pack_name):
                if top_one:
                    self.layout.separator()
                    top_one = False
                pack_Menu = packs_Menus.get(pack_name, None)
                self.layout.menu(pack_Menu.__name__, text=pack_name, translate=False)
                
                
def draw_geo_add_menus(self: Menu, context: bpy.types.Context):
    sync.ensure_sync(context, from_gui=True)
    if props_py.gl_packs != {}:
        top_one = True
        # bpy.app.timers.register(_register_existing_menus)
        for pack_name in props_py.gl_packs.keys():
            if "GeometryNodeTree" in file.get_pack_types(pack_name):
                if top_one:
                    self.layout.separator()
                    top_one = False
                pack_Menu = packs_Menus.get(pack_name, None)
                self.layout.menu(pack_Menu.__name__, text=pack_name, translate=False)
                
                
def draw_nodes_add_menu(self: Menu, context: bpy.types.Context):
    layout = self.layout
    space_data = context.space_data
    new_tree = False
    if isinstance(space_data, bpy.types.SpaceNodeEditor):
        tree_type = space_data.tree_type
    elif isinstance(space_data, bpy.types.SpaceProperties):
        tree_type = "GeometryNodeTree"
        new_tree = True
    # TODO transfer all packs to presets_cache rather than read presets.
    preset_names, tree_types = file.read_presets(self.bl_label)
    
    row = layout.row()
    col = row.column()
    col.separator()
    for preset_name in preset_names:
        # if preset_name == "--------":
        #     col.separator()
        if tree_types[preset_name] == tree_type:
            # layout.operator("node.hot_node_nodes_add", text=preset_name, icon=type_icon[preset.type]).preset_name = preset_name
            ops = col.operator("node.hot_node_nodes_add", text=preset_name, translate=False)
            ops.preset_name = preset_name
            ops.pack_name = self.bl_label
            ops.tree_type = tree_type
            ops.new_tree = new_tree
            
            
def draw_nodes_save_menu(self: Menu, context: bpy.types.Context):
    layout = self.layout
    space_data = context.space_data
    props = context.scene.hot_node_props
    if isinstance(space_data, bpy.types.SpaceNodeEditor):
        tree_type = space_data.tree_type
    # TODO transfer all packs to presets_cache rather than read presets.
    preset_names, tree_types = file.read_presets(self.bl_label)
    
    row = layout.row()
    col = row.column()
    col.separator()
    for preset_name in preset_names:
        if tree_types[preset_name] == tree_type:
            # layout.operator("node.hot_node_nodes_add", text=preset_name, icon=type_icon[preset.type]).preset_name = preset_name
            ops = col.operator("node.hot_node_preset_save", text=preset_name, translate=False)
            ops.preset_name = preset_name
            ops.pack_name = self.bl_label
    props_py.pack_name_of_fast_create = self.bl_label
    col.prop(props, "fast_create_preset_name", icon='BLANK1', text="", placeholder="".join(("  ", i18n.msg["Save Nodes As"], "...")))
    
    
def draw_pack_icons(layout: bpy.types.UILayout, icons, separate=True, use_enter=True):
        item_num = 0
        if separate:
            layout.separator(type='SPACE')
        row = layout.row(align=True)
        row.label(icon='BLANK1', text="")
        row.label(icon='BLANK1', text="")
        # row.scale_x = 1.12
        for icon in icons:
            if use_enter:
                if item_num >= 9:
                    item_num = 1
                    layout.separator(type='SPACE')
                    row = layout.row(align=True)
                    # row.scale_x = 1.12
                else:
                    item_num += 1
            row.operator("node.hot_node_pack_icon_set", text="", icon=icon).icon = icon
                
            
def create_pack_menu_class(pack_name: str):
    global _pack_menu_num
    _pack_menu_num += 1
    Menu_name = f"HOTNODE_MT_pack_menu_{_pack_menu_num}"
    Menu = type(Menu_name, (HOTNODE_MT_pack, ), {"bl_label": pack_name})
    packs_Menus[pack_name] = Menu
    return Menu


def create_key_map(context: bpy.types.Context):
    kc = context.window_manager.keyconfigs
    context.window_manager.keyconfigs.addon.keymaps.new(name="Node Editor", space_type='NODE_EDITOR')


def _register_new_menus():
    for Menu in new_Menus:
        bpy.utils.register_class(Menu)
        
        
def _register_existing_menus():
    for Menu in packs_Menus.values():
        try:
            bpy.utils.register_class(Menu)
        except ValueError:
            pass
            # print("_register_existing_menus failed")
            
    

def ensure_existing_pack_menu(pack_name: str|None=None):
    '''Create menu classes for the pack(s) which are not appeared before.
    
    - pack_name: The pack that may needs creating menu. Keep None for checking all packs.
    '''
    global packs_Menus, new_Menus
    new_Menus.clear()
    # Here we create class for every appeared pack name, then the name is in the pool and we can reuse them when next time the name appears.
    # We will ungister them when blender is closed. Just like an obj pool.
    pack_names = packs_Menus.keys()
    if pack_name is None:
        for pack_name in props_py.gl_packs.keys():
            if pack_name not in pack_names:
                new_Menus.append(create_pack_menu_class(pack_name))
    elif pack_name not in pack_names:
        new_Menus.append(create_pack_menu_class(pack_name))
    # XXX More cost but safer
    # bpy.app.timers.register(_register_new_menus)
    bpy.app.timers.register(_register_existing_menus)
            
        
# Sync Functions, will be called in draw()
def _ensure_sync_by_gui_idle_time(context):
    global last_darw_time
    current_time = time.time()
    if current_time - last_darw_time > 0.7:
        sync.ensure_sync(context, from_gui=True)
    last_darw_time = current_time


class HOTNODE_MT_pack_select(Menu):
    bl_label = i18n.msg["Packs"]
    
    def draw(self, context):
        layout = self.layout
        for pack in props_py.gl_packs.values():
            if pack.icon == 'NONE':
                icon = 'OUTLINER_COLLECTION'
            else:
                icon = pack.icon
            layout.operator("node.hot_node_pack_select", icon=icon, text=pack.name, translate=False).pack_name = pack.name
            
            
class HOTNODE_MT_preset_copy_to_pack(Menu):
    bl_label = i18n.msg["Copy to Pack"]
    bl_description = i18n.msg["desc_copy_to_pack"]
    
    is_move = False
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=i18n.msg["Copy to Pack"])
        layout.separator()
        for pack_name in props_py.gl_packs.keys():
            if pack_name != props_py.gl_pack_selected.name:
                ops = layout.operator("node.hot_node_preset_to_pack", icon='OUTLINER_COLLECTION', text=pack_name, translate=False)
                ops.pack_name = pack_name
                ops.is_move = self.is_move
            
            
class HOTNODE_MT_preset_move_to_pack(Menu):
    bl_label = i18n.msg["Move to Pack"]
    bl_description = i18n.msg["desc_move_to_pack"]
    
    is_move = True
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=i18n.msg["Move to Pack"])
        layout.separator()
        for pack_name in props_py.gl_packs.keys():
            if pack_name != props_py.gl_pack_selected.name:
                ops = layout.operator("node.hot_node_preset_to_pack", icon='OUTLINER_COLLECTION', text=pack_name, translate=False)
                ops.pack_name = pack_name
                ops.is_move = self.is_move


class HOTNODE_MT_specials(Menu):
    bl_label = i18n.msg["Node Preset Specials"]
    
    def draw(self, context):
        addon_prefs = context.preferences.addons[__package__].preferences
        props = context.scene.hot_node_props
        layout = self.layout
        
        # Refresh
        layout.operator("node.hot_node_refresh", icon='FILE_REFRESH')
        # layout.operator("node.hot_node_repair_corruption", icon='FILE_REFRESH')

        # Move top / bottom
        layout.separator()
        layout.operator("node.hot_node_preset_move", icon='TRIA_UP_BAR', text="Move to Top").direction = 'TOP'
        layout.operator("node.hot_node_preset_move", icon='TRIA_DOWN_BAR', text="Move to Bottom").direction = 'BOTTOM'
        
        # Preset to Pack
        layout.separator()
        layout.menu("HOTNODE_MT_preset_copy_to_pack", icon='FILE')
        layout.menu("HOTNODE_MT_preset_move_to_pack", icon='FILE_HIDDEN')
        # ops = layout.operator("node.hot_node_preset_to_pack", icon='FILE', text=i18n.msg["Copy to Pack"])
        # ops.pop_menu = True
        # ops = layout.operator("node.hot_node_preset_to_pack", icon='FILE_HIDDEN', text=i18n.msg["Move to Pack"])
        # ops.pop_menu = True
        # ops.is_move = True
        
        # User Utils
        layout.separator()
        layout.operator("node.hot_node_preset_clear", icon='PANEL_CLOSE', text=i18n.msg["Delete All Presets"])
        
        # Nodes Settings
        layout.separator()
        layout.prop(addon_prefs, "overwrite_tree_io")
        layout.prop_menu_enum(addon_prefs, "tex_default_mode", icon='FILE_IMAGE')
        
        # # Add-on UI Settings
        # layout.separator()
        # layout.prop(addon_prefs, "in_one_menu")
        # layout.prop(addon_prefs, "focus_on_get")
        # layout.prop(addon_prefs, "extra_confirm")
        # # Utilities & settings Bar
        # layout.prop(addon_prefs, "settings_bar")
        # layout.prop(addon_prefs, "utilities_bar")
        layout.separator()
        layout.menu("HOTNODE_MT_ui_preferences", icon='PREFERENCES')
        # layout.popover("HOTNODE_MT_ui_preferences", icon='PREFERENCES')
        
        
class HOTNODE_MT_pack(Menu):
    '''(Will be dynamatically regisited) A menu shows a pack's presets for user to get / modify / create / ...'''
    bl_label = i18n.msg["Nodes"]
    def draw(self, context):
        if pack_menus_mode == 'ADD_NODES':
            draw_nodes_add_menu(self, context)
        elif pack_menus_mode == 'SAVE_NODES':
            draw_nodes_save_menu(self, context)
        elif pack_menus_mode == 'ADD_GEO':
            draw_nodes_add_menu(self, context)
            
            
class HOTNODE_MT_pack_specials(Menu):
    '''(Will be dynamatically regisited) A menu shows a pack's presets for user to get / modify / create / ...'''
    bl_label = "Pack Specials"
    
    def draw(self, context):
        layout = self.layout
        icon = props_py.gl_pack_selected.icon if props_py.gl_pack_selected.icon != 'NONE' else 'OUTLINER_COLLECTION'
        layout.menu("HOTNODE_MT_pack_icons", icon=icon, text=i18n.msg["Set Icon"])
        draw_pack_icons(layout, props_py.pack_icons1)
        layout.separator()
        layout.operator("node.hot_node_pack_delete", icon='PANEL_CLOSE', text=i18n.msg["Delete Pack"])
            
            
class HOTNODE_MT_nodes_add_in_one(Menu):
    '''Nodes add menu, for short keys'''
    bl_label = i18n.msg["Add Nodes"]
    def draw(self, context):
        global pack_menus_mode
        pack_menus_mode = 'ADD_NODES'
        draw_nodes_add_menus(self, context)
        
        
class HOTNODE_MT_nodes_save_in_one(Menu):
    '''Nodes save menu, for short keys'''
    bl_label = i18n.msg["Save Nodes"]
    def draw(self, context):
        global pack_menus_mode
        pack_menus_mode = 'SAVE_NODES'
        draw_nodes_save_menus(self, context)
                
        
class HOTNODE_MT_packs(Menu):
    '''A menu shows all packs to access their presets for user to get / modify / create / ...'''
    bl_label = i18n.msg["Nodes"]
    def draw(self, context):
        if pack_menus_mode == 'ADD_NODES':
            draw_nodes_add_menus(self, context)
        elif pack_menus_mode == 'SAVE_NODES':
            draw_nodes_save_menus(self, context)
        elif pack_menus_mode == 'ADD_GEO':
            draw_geo_add_menus(self, context)
            
            
class HOTNODE_MT_pack_icons(Menu):
    '''A menu shows all icons that could be set to the pack'''
    bl_label = i18n.msg["Pack Icon"]
    
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
            row.operator("node.hot_node_pack_icon_set", text="", icon=icon).icon = icon
    
    def draw(self, context):
        layout = self.layout
        
        self.draw_pack_icons(props_py.pack_icons1, separate=False)
        # self.draw_pack_icons(props_py.pack_icons2)
        self.draw_pack_icons(props_py.pack_icons3, use_enter=True)
        self.draw_pack_icons(props_py.pack_icons4)
            
        layout.separator()
        row = layout.row()
        row.scale_x = 1.12
        row.operator("node.hot_node_pack_icon_set", text=i18n.msg["Do Not Use Icon"], icon='X').icon = 'NONE'


class HOTNODE_UL_presets(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        preset = item

        layout.emboss = 'NONE'
        
        icon = type_icon[preset.type]
        layout.prop(preset, "name", text="", emboss=False, icon=icon)
        

class HOTNODE_PT_parent(Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Hot Node"
    
    
# class HOTNODE_MT_ui_preferences(HOTNODE_PT_parent):
class HOTNODE_MT_ui_preferences(Menu):
    bl_label = i18n.msg["UI Preferences"]
    bl_description = i18n.msg["desc_ui_preferences"]
    # bl_options = {'DEFAULT_CLOSED'}
    # bl_order = 999
    
    def draw(self, context):
        # Add-on UI Settings
        addon_prefs = context.preferences.addons[__package__].preferences
        layout = self.layout
        # layout.alignment = 'CENTER'
        # layout.label(text=i18n.msg["UI Preferences"])
        # layout.separator()
        layout.prop(addon_prefs, "in_one_menu")
        layout.prop(addon_prefs, "focus_on_get")
        layout.prop(addon_prefs, "extra_confirm")
        # Utilities & settings Bar
        # layout.prop(addon_prefs, "pack_icon_bar")
        layout.prop(addon_prefs, "settings_bar")
        layout.prop(addon_prefs, "utilities_bar")
    
    
class HOTNODE_PT_nodes(HOTNODE_PT_parent):
    bl_label = i18n.msg["Nodes"]
    bl_idname = "HOTNODE_PT_nodes"

    def draw(self, context):
        global gui_info, gui_info_icon
        _ensure_sync_by_gui_idle_time(context)
        # once packs changed, pack menu will be updated
        layout = self.layout
        addon_prefs = context.preferences.addons[__package__].preferences
        props = context.scene.hot_node_props
        presets = props.presets
        pack_selected = props_py.gl_pack_selected
        
        # Pack Select UI
        
        row = layout.row(align=True)
        row.scale_x = 1.75
        icon = pack_selected.icon if pack_selected is not None and pack_selected.icon != 'NONE' else 'OUTLINER_COLLECTION'
        # row.menu("HOTNODE_MT_pack_select", icon=icon, text="")
        row.menu("HOTNODE_MT_pack_select", icon='OUTLINER_COLLECTION', text="")
        row.scale_x = 1.0
        row.prop(props, "pack_selected_name", text="", placeholder=i18n.msg["Select a pack"])
        row.operator("node.hot_node_pack_create", icon='COLLECTION_NEW', text="")
        # row.prop(addon_prefs, "more_pack_ops", icon='TRIA_DOWN', text="")
        # more pack operations
        # if addon_prefs.more_pack_ops:
        #     row = layout.row(align=True)
        #     row.operator("wm.call_menu", icon='PREFERENCES', text="").name = "HOTNODE_MT_pack_icons"
        #     row.operator("node.hot_node_pack_delete", icon='TRASH', text="")
        # row.operator("wm.call_menu", icon='COLLAPSEMENU', text="").name = "HOTNODE_MT_pack_specials"
        # row.menu("HOTNODE_MT_pack_specials", icon='DOWNARROW_HLT', text="")
        # row.operator("wm.call_menu", icon='PREFERENCES', text="").name = "HOTNODE_MT_pack_icons"
        row.operator("node.hot_node_pack_delete", icon='TRASH', text="")
        
        rows = 5
        # if addon_prefs.pack_icon_bar:
        #     rows += props_py.pack_with_icon_num
        if addon_prefs.utilities_bar:
            rows += 2
        if addon_prefs.settings_bar:
            rows += 2

        layout.separator(factor=0.1)
        row = layout.row()
        row.template_list("HOTNODE_UL_presets", "", props, "presets",
                          props, "preset_selected", rows=rows)
        
        # Side Bar =====
        col = row.column(align=True)
        col.operator("node.hot_node_preset_create", icon='ADD', text="")
        col.operator("node.hot_node_preset_delete", icon='REMOVE', text="")
        col.separator()
        
        # Special options menu
        col.menu("HOTNODE_MT_specials", icon='DOWNARROW_HLT', text="")
        
        # Move up & down
        # if presets:
        col.separator()
        col.operator("node.hot_node_preset_move", icon='TRIA_UP', text="").direction = 'UP'
        col.operator("node.hot_node_preset_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
        
        # Pack Icon Bar
        # if addon_prefs.pack_icon_bar:
        #     draw_separator = True
        #     # pack_selected_name = props_py.gl_pack_selected.name if props_py.gl_pack_selected is not None else ""
        #     for pack in props_py.gl_packs.values():
        #         if pack.icon != 'NONE':
        #             if draw_separator:
        #                 col.separator()
        #                 draw_separator = False
        #             # if pack_selected_name == pack.name:
        #             #     depress = True
        #             # else:
        #             #     depress = False
        #             col.operator("node.hot_node_pack_select", icon=pack.icon, text="", depress=False).pack_name = pack.name
            
        # Utilities & Preferences Bar
        if addon_prefs.settings_bar:
            col.separator()
            col.prop(addon_prefs, "overwrite_tree_io", icon='NODETREE', text="")
        if addon_prefs.utilities_bar:
            col.separator()
            col.menu("HOTNODE_MT_preset_copy_to_pack", icon='FILE', text="")
            col.menu("HOTNODE_MT_preset_move_to_pack", icon='FILE_HIDDEN', text="")
            # wm.call_manu has some flaws.
            # col.operator("wm.call_menu", icon='FILE', text="").name = "HOTNODE_MT_preset_copy_to_pack"
            # col.operator("wm.call_menu", icon='FILE_HIDDEN', text="").name = "HOTNODE_MT_preset_move_to_pack"
            
        # Preset Usage UI
        layout.separator(factor=0.1)
        if addon_prefs.focus_on_get:
            row = layout.row()
            # row.scale_y = 1.25
            row.operator("node.hot_node_preset_apply", text=i18n.msg["Get"]).preset_name = ""
            row.operator("node.hot_node_preset_save", icon='CURRENT_FILE', text="")
        else:
            row = layout.row(align=True)
            row.operator("node.hot_node_preset_apply", text=i18n.msg["Get"]).preset_name = ""
            row.operator("node.hot_node_preset_save", text=i18n.msg["Set"])

        # Prompts
        if gui_info is not None:
            if time.time() - gui_info_born_time < gui_info_duration:
                for i, info in enumerate(gui_info):
                    row = layout.row()
                    if i == 0:
                        row.label(text=info, icon=gui_info_icon)
                    else:
                        row.label(text=info, icon='BLANK1')
            else:
                gui_info = None
                gui_info_icon = None
   
   
class HOTNODE_PT_texture(HOTNODE_PT_parent, Panel):
    bl_label = i18n.msg["Textures"]
    bl_idname = "HOTNODE_PT_texture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass
        
        
class HOTNODE_PT_texture_load(HOTNODE_PT_parent, Panel):
    bl_label = i18n.msg["Load"]
    bl_parent_id = "HOTNODE_PT_texture"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        
        layout = self.layout
        props = context.scene.hot_node_props
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        # Texture Apply
        row = layout.row()
        row.prop(props, "compare_tolerance", text="Tolerance")
        row = layout.row()
        row.prop(props, "tex_dir_path", text=i18n.msg["Folder Path"])

   
class HOTNODE_PT_texture_save(HOTNODE_PT_parent, Panel):
    bl_label = i18n.msg["Set"]
    bl_parent_id = "HOTNODE_PT_texture"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.hot_node_props
        mode = props.tex_preset_mode
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        # Texture Save
        row = layout.row()
        row.operator("node.hot_node_texture_save", text=i18n.msg["Set Texture"])
        
        row = layout.row()
        row.prop(props, "tex_preset_mode", text="Mode")
        
        if mode == 'KEYWORD':
            row = layout.row()
            row.prop(props, "tex_key", text=i18n.msg["Name Key"], placeholder=i18n.msg["Key1 / Key2 / ..."])
            
            
class HOTNODE_PT_pack_import_export(HOTNODE_PT_parent, Panel):
    bl_label = i18n.msg["Pack Import Export"]
    bl_idname = "HOTNODE_PT_pack_import_export"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Import & Export Packs
        row = layout.row()
        col = row.column(align=True)
        col.operator("import.hot_node_pack_import", icon="IMPORT", text="Import").is_recovering = False
        col.operator("import.hot_node_pack_import", icon="IMPORT", text=i18n.msg["Recover"]).is_recovering = True
        col = row.column(align=True)
        col.operator("export.hot_node_pack_export", icon="EXPORT", text="Export")
        col.operator("export.hot_node_pack_export_all", icon="EXPORT", text="Export All")
        

classes = (
    HOTNODE_MT_pack_select,
    HOTNODE_MT_preset_copy_to_pack,
    HOTNODE_MT_preset_move_to_pack,
    HOTNODE_MT_ui_preferences,
    HOTNODE_MT_specials,
    HOTNODE_MT_nodes_add_in_one,
    HOTNODE_MT_nodes_save_in_one,
    HOTNODE_MT_pack_specials,
    HOTNODE_MT_packs,
    HOTNODE_MT_pack_icons,
    HOTNODE_UL_presets,
    HOTNODE_PT_nodes,
    HOTNODE_PT_texture,
    HOTNODE_PT_texture_load,
    HOTNODE_PT_texture_save,
    HOTNODE_PT_pack_import_export,
    )


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        # already registered
        except ValueError:
            pass
        
    bpy.types.NODE_MT_add.append(draw_ex_nodes_add_menu)
    # bpy.types.OBJECT_MT_modifier_add.append(draw_ex_geo_add_menu)
    bpy.types.NODE_MT_context_menu.append(draw_ex_nodes_save_menu)


def unregister():
    global packs_Menus
    for cls in classes:
        bpy.utils.unregister_class(cls)
    for Menu in packs_Menus.values():
        try:
            bpy.utils.unregister_class(Menu)
        except RuntimeError:
            pass
        
    bpy.types.NODE_MT_add.remove(draw_ex_nodes_add_menu)
    # bpy.types.OBJECT_MT_modifier_add.remove(draw_ex_geo_add_menu)
    bpy.types.NODE_MT_context_menu.remove(draw_ex_nodes_save_menu)
    
    packs_Menus.clear()