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
from bpy.types import Menu, Panel, UIList

import time

from . import file, props_py, sync


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

last_darw_time = 0.0

gui_info = None
gui_info_duration = 3.0
gui_info_icon = None
gui_info_born_time = 0.0


def add_gui_infos(message: list[str], duration: float=3.0, icon: str|None=None):
    global gui_info, gui_info_duration, gui_info_icon, gui_info_born_time
    gui_info = message
    gui_info_duration = duration
    gui_info_icon = icon
    gui_info_born_time = time.time()


def draw_nodes_add_menus(self: Menu, context: bpy.types.Context):
    sync.ensure_sync(context, from_gui=True)
    # TODO reduce empty pack
    edit_tree = context.space_data.edit_tree
    if edit_tree is None:
        return
    if props_py.gl_packs != {}:
        first_draw = True
        for pack_name in props_py.gl_packs.keys():
            if edit_tree.bl_idname in file.get_pack_types(pack_name):
                if first_draw:
                    self.layout.separator()
                    first_draw = False
                self.layout.menu(packs_Menus[pack_name].__name__)
            
            
def create_pack_menu_class(pack_name: str):
    global _pack_menu_num
    _pack_menu_num += 1
    Menu_name = f"HOTNODE_MT_pack_menu_{_pack_menu_num}"
    Menu = type(Menu_name, (HOTNODE_MT_nodes_add, ), {"bl_label": pack_name})
    packs_Menus[pack_name] = Menu
    return Menu


def _register_menus():
    for Menu in new_Menus:
        bpy.utils.register_class(Menu)
    

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
    bpy.app.timers.register(_register_menus)
            
        
# Sync Functions, will be called in draw()
def _ensure_sync_by_gui_idle_time(context):
    global last_darw_time
    current_time = time.time()
    if current_time - last_darw_time > 0.7:
        sync.ensure_sync(context, from_gui=True)
    last_darw_time = current_time
    

class HOTNODE_MT_pack_select(Menu):
    bl_label = "Packs"
    
    def draw(self, context):
        layout = self.layout
        for pack_name in props_py.gl_packs.keys():
            # TODO use pack rather than pack name
            layout.operator("node.hot_node_pack_select", text=pack_name).pack_name = pack_name


class HOTNODE_MT_specials(Menu):
    bl_label = "Node Preset Specials"
    
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
        
        # User Utils
        layout.separator()
        layout.operator("node.hot_node_preset_clear", icon='PANEL_CLOSE', text="Delete All Presets")
        
        # Nodes Settings
        layout.separator()
        layout.prop(addon_prefs, "overwrite_tree_io")
        layout.prop(addon_prefs, "tex_default_mode", icon='PREFERENCES', text="")
        
        # Add-on Settings
        layout.separator()
        layout.prop(addon_prefs, "in_one_menu")
        layout.prop(addon_prefs, "extra_confirm")
                     
        
class HOTNODE_MT_nodes_add(Menu):
    '''A menu shows a pack's presets.'''
    # Take bl_label as pack name
    bl_label = ""
    
    @classmethod
    def set_pack(cls, pack_name):
        cls.bl_label = pack_name
    
    def draw(self, context):
        layout = self.layout
        tree_type = context.space_data.tree_type
        # TODO transfer all packs to presets_cache rather than read presets.
        preset_names, tree_types = file.read_presets(self.bl_label)
        
        row = layout.row()
        col = row.column()
        col.separator()
        for preset_name in preset_names:
            if tree_types[preset_name] == tree_type:
                # layout.operator("node.hot_node_nodes_add", text=preset_name, icon=type_icon[preset.type]).preset_name = preset_name
                ops = col.operator("node.hot_node_nodes_add", text=preset_name)
                ops.preset_name = preset_name
                ops.pack_name = self.bl_label
                ops.tree_type = tree_type
                
                
class HOTNODE_MT_nodes_add_in_one(Menu):
    bl_label = "Nodes"
    def draw(self, context):
        draw_nodes_add_menus(self, context)


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
    
    
class HOTNODE_PT_nodes(HOTNODE_PT_parent, Panel):
    bl_label = "Nodes"
    bl_idname = "HOTNODE_PT_nodes"

    def draw(self, context):
        global gui_info, gui_info_icon
        _ensure_sync_by_gui_idle_time(context)
        # once packs changed, pack menu will be updated
        layout = self.layout
        props = context.scene.hot_node_props
        presets = props.presets
        
        # Preset Usage UI
        # col = layout.column(align=True)
        # row = col.row(align=True)
        row = layout.row(align=True)
        row.operator("node.hot_node_preset_apply", text="Apply").preset_name = ""
        row.operator("node.hot_node_preset_save", text="Save")
        # row.separator(factor=1.45)
        # col = row.column()
        # col.operator("node.hot_node_refresh", icon='FILE_REFRESH', text="")

        # Preset Select UI
        rows = 3
        if presets:
            rows = 5

        layout.separator(factor=0.1)
        row = layout.row()
        row.template_list("HOTNODE_UL_presets", "", props, "presets",
                          props, "preset_selected", rows=rows)
        
        col = row.column(align=True)
        col.operator("node.hot_node_preset_create", icon='ADD', text="")
        col.operator("node.hot_node_preset_delete", icon='REMOVE', text="")
        col.separator()
        
        # Special options menu
        col.menu("HOTNODE_MT_specials", icon='DOWNARROW_HLT', text="")
        
        # Move up & down
        if presets:
            col.separator()
            col.operator("node.hot_node_preset_move", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("node.hot_node_preset_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

        # Pack Select UI
        row = layout.row(align=True)
        row.menu("HOTNODE_MT_pack_select", icon='OUTLINER_COLLECTION', text="")
        row.prop(props, "pack_selected_name", text="", placeholder="Select a pack")
        row.operator("node.hot_node_pack_create", icon='ADD', text="")
        row.operator("node.hot_node_pack_delete", icon='TRASH', text="")
        
        # Prompts
        # if context.space_data.edit_tree is None:
        #     row = layout.row()
        #     row.label(text="Open a node tree to start", icon="INFO")
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
    bl_label = "Textures"
    bl_idname = "HOTNODE_PT_texture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass
        
        
class HOTNODE_PT_texture_apply(HOTNODE_PT_parent, Panel):
    bl_label = "Apply"
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
        row.prop(props, "tex_dir_path", text="Folder Path")

   
class HOTNODE_PT_texture_save(HOTNODE_PT_parent, Panel):
    bl_label = "Save"
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
        row.operator("node.hot_node_texture_save", text="Save Texture")
        
        row = layout.row()
        row.prop(props, "tex_preset_mode", text="Mode")
        
        if mode == 'KEYWORD':
            row = layout.row()
            row.prop(props, "tex_key", text="Key", placeholder="Key1 / Key2 / ...")
            
            
class HOTNODE_PT_pack_import_export(HOTNODE_PT_parent, Panel):
    bl_label = "Pack Import Export"
    bl_idname = "HOTNODE_PT_pack_import_export"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Import & Export Packs
        row = layout.row()
        col = row.column(align=True)
        col.operator("import.hot_node_pack_import", icon="IMPORT", text="Import").is_recovering = False
        col.operator("import.hot_node_pack_import", icon="IMPORT", text="Recover").is_recovering = True
        col = row.column(align=True)
        col.operator("export.hot_node_pack_export", icon="EXPORT", text="Export")
        col.operator("export.hot_node_pack_export_all", icon="EXPORT", text="Export All")
        
        
def draw_ex_nodes_add_menu(self, context):
    if context.preferences.addons[__package__].preferences.in_one_menu:
        self.layout.separator()
        self.layout.menu("HOTNODE_MT_nodes_add_in_one", text="Nodes")
    else:
        draw_nodes_add_menus(self, context)
    
    
def draw_ex_fast_create_preset(self, context):
    self.layout.separator()
    self.layout.prop(context.scene.hot_node_props, "fast_create_preset_name", text="", placeholder="       Save Nodes As")


classes = (
    HOTNODE_MT_pack_select,
    HOTNODE_MT_specials,
    HOTNODE_MT_nodes_add_in_one,
    HOTNODE_UL_presets,
    HOTNODE_PT_nodes,
    HOTNODE_PT_texture,
    HOTNODE_PT_texture_apply,
    HOTNODE_PT_texture_save,
    HOTNODE_PT_pack_import_export,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.NODE_MT_add.append(draw_ex_nodes_add_menu)
    bpy.types.NODE_MT_context_menu.append(draw_ex_fast_create_preset)


def unregister():
    global packs_Menus
    for cls in classes:
        bpy.utils.unregister_class(cls)
    for Menu in packs_Menus.values():
        bpy.utils.unregister_class(Menu)
        
    bpy.types.NODE_MT_add.remove(draw_ex_nodes_add_menu)
    bpy.types.NODE_MT_context_menu.remove(draw_ex_fast_create_preset)
    
    packs_Menus.clear()