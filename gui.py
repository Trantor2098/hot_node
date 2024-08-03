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
from bpy.props import StringProperty

import time

from . import properties, file


type_icon = {
    "ShaderNodeTree": 'NODE_MATERIAL',
    "GeometryNodeTree": 'GEOMETRY_NODES',
    "CompositorNodeTree": 'NODE_COMPOSITING',
    "TextureNodeTree": 'NODE_TEXTURE',
}

last_darw_time = 0.0


# Sync Functions, will be called in draw()
def _execute_refresh():
    bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')


def _sync_by_gui_idle_time():
    global last_darw_time
    current_time = time.time()
    if current_time - last_darw_time > 1.0:
        if not file.check_sync_by_mtime():
            bpy.app.timers.register(_execute_refresh, first_interval=0.01)
    last_darw_time = current_time
    

class HOTNODE_MT_pack_select(Menu):
    bl_label = "Packs"
    
    def draw(self, context):
        layout = self.layout
        packs = properties.packs
        for pack in packs:
            layout.operator("node.hot_node_pack_select", text=pack).pack = pack


class HOTNODE_MT_specials(Menu):
    bl_label = "Node Preset Specials"
    
    def draw(self, context):
        props = context.scene.hot_node_props
        layout = self.layout
        
        # Refresh
        layout.operator("node.hot_node_refresh", icon='FILE_REFRESH')

        # Move top / bottom
        layout.separator()
        layout.operator("node.hot_node_preset_move", icon='TRIA_UP_BAR', text="Move to Top").direction = 'TOP'
        layout.operator("node.hot_node_preset_move", icon='TRIA_DOWN_BAR', text="Move to Bottom").direction = 'BOTTOM'
        
        # Clear Presets
        layout.separator()
        layout.operator("node.hot_node_preset_clear", icon='PANEL_CLOSE', text="Delete All Presets")
        
        # Some Bool Options
        layout.separator()
        layout.prop(props, "overwrite_tree_io")
        layout.prop(props, "extra_confirm")

        # Texture Default Mode
        layout.separator()
        layout.prop(props, "tex_default_mode", icon='PREFERENCES', text="")
        
        
class HOTNODE_MT_nodes_add_specials(Menu):
    bl_label = "Quick Menu"
    
    def draw(self, context):
        props = context.scene.hot_node_props
        layout = self.layout
        layout.operator("node.hot_node_refresh", icon='FILE_REFRESH')
        layout.menu("HOTNODE_MT_pack_select", icon='OUTLINER_COLLECTION')
        layout.separator()
        layout.prop(props, "fast_create_preset_name", icon='ADD', text="", placeholder="Fast Create Preset")
        
        
class HOTNODE_MT_nodes_add_all(Menu):
    bl_label = "All Nodes"
    
    def draw(self, context):
        layout = self.layout
        tree_type = context.space_data.tree_type
        packs = properties.packs
        packs_num = len(packs)
        use_overlay = packs_num >= 10
        
        overlay_num = 0
        row = layout.row()
        if use_overlay:
            col = row.column()
        for pack in packs:
            pack_presets, tree_types = file.read_presets(pack_name=pack)
            preset_num = len(pack_presets)
            if preset_num != 0:
                if use_overlay:
                    if overlay_num >= packs_num + 2:
                        col = row.column()
                        overlay_num = 0
                    overlay_num += 1
                    col.label(text=pack, icon='DISCLOSURE_TRI_DOWN')
                else:
                    col = row.column()
                    col.label(text=pack)
                    col.separator()
                # col.separator()
                for i in range(preset_num):
                    preset_name = pack_presets[i]
                    tree_type = tree_types[preset_name]
                    if tree_type == tree_type:
                        if use_overlay:
                            if overlay_num >= packs_num + 2:
                                col = row.column()
                                overlay_num = 0
                            overlay_num += 1
                        ops = col.operator("node.hot_node_nodes_add", text=preset_name)
                        ops.preset_name = preset_name
                        ops.pack_name = pack
                        ops.tree_type = tree_type
                        
        
class HOTNODE_MT_nodes_add(Menu):
    bl_label = "Nodes"
    
    def draw(self, context):
        layout = self.layout
        tree_type = context.space_data.tree_type
        props = context.scene.hot_node_props
        presets = props.presets
        pack_selected = properties.pack_selected
        
        row = layout.row()
        col = row.column()
        col.menu("HOTNODE_MT_nodes_add_all")
        col.separator()
        # col.label(text=pack_selected, icon='DISCLOSURE_TRI_DOWN')
        for preset in presets:
            if preset.type == tree_type:
                preset_name = preset.name
                # layout.operator("node.hot_node_nodes_add", text=preset_name, icon=type_icon[preset.type]).preset_name = preset_name
                ops = col.operator("node.hot_node_nodes_add", text=preset_name)
                ops.preset_name = preset_name
                ops.pack_name = pack_selected
                ops.tree_type = tree_type
        

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
        
        layout = self.layout
        props = context.scene.hot_node_props
        presets = props.presets
        
        # Preset Usage UI
        # col = layout.column(align=True)
        # row = col.row(align=True)
        row = layout.row(align=True)
        row.operator("node.hot_node_preset_apply", text="Apply")
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
        row.prop(props, "pack_selected_name", text="")
        row.operator("node.hot_node_pack_create", icon='ADD', text="")
        row.operator("node.hot_node_pack_delete", icon='TRASH', text="")
        
        # Prompt Message
        if properties.pack_selected == "":
            row = layout.row()
            row.label(text="Select a pack or refresh to use", icon="INFO")
        if context.space_data.edit_tree is None:
            row = layout.row()
            row.label(text="Open a node tree in editor to use", icon="INFO")
        
        _sync_by_gui_idle_time()
   
   
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
        
        
def ex_shift_a_nodes_add(self, context):
    self.layout.separator()
    self.layout.menu(HOTNODE_MT_nodes_add.__name__, text="Nodes")
    
    
def ex_right_click_create(self, context):
    self.layout.separator()
    self.layout.prop(context.scene.hot_node_props, "fast_create_preset_name", text="", placeholder="       Save Nodes As")


classes = (
    HOTNODE_MT_pack_select,
    HOTNODE_MT_specials,
    HOTNODE_MT_nodes_add_specials,
    HOTNODE_MT_nodes_add_all,
    HOTNODE_MT_nodes_add,
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
        
    bpy.types.NODE_MT_add.append(ex_shift_a_nodes_add)
    bpy.types.NODE_MT_context_menu.append(ex_right_click_create)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        
    bpy.types.NODE_MT_add.remove(ex_shift_a_nodes_add)
    bpy.types.NODE_MT_context_menu.remove(ex_right_click_create)