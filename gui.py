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

from . import properties


type_icon = {
    "ShaderNodeTree": 'NODE_MATERIAL',
    "GeometryNodeTree": 'GEOMETRY_NODES',
    "CompositorNodeTree": 'NODE_COMPOSITING',
    "TextureNodeTree": 'NODE_TEXTURE',
}


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
        layout.prop(props, "tex_default_mode", text="")
        

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
    
    
class HOTNODE_PT_main(HOTNODE_PT_parent, Panel):
    bl_label = "Node Preset"
    bl_idname = "HOTNODE_PT_main"

    def draw(self, context):
        
        layout = self.layout
        props = context.scene.hot_node_props
        presets = props.presets
        
        # layout.label(text="Node Presets")
        
        # Preset Usage UI
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("node.hot_node_preset_apply", text="Apply")
        row.operator("node.hot_node_preset_save", text="Save")

        # Preset Select UI
        rows = 3
        if presets:
            rows = 5

        row = layout.row()
        row.template_list("HOTNODE_UL_presets", "", props, "presets",
                          props, "preset_selected", rows=rows)
        
        col = row.column(align=True)
        col.operator("node.hot_node_preset_create", icon='ADD', text="")
        col.operator("node.hot_node_preset_delete", icon='REMOVE', text="")
        col.separator()
        # special options menu
        col.menu("HOTNODE_MT_specials", icon='DOWNARROW_HLT', text="")
        # move up & down
        if presets:
            col.separator()

            col.operator("node.hot_node_preset_move", icon='TRIA_UP', text="").direction = 'UP'
            col.operator("node.hot_node_preset_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

        # Pack Select UI
        row = layout.row(align=True)
        row.menu("HOTNODE_MT_pack_select", icon='OUTLINER_COLLECTION', text="")
        row.prop(props, "pack_selected_name")
        row.operator("node.hot_node_pack_create", icon='ADD', text="")
        row.operator("node.hot_node_pack_delete", icon='TRASH', text="")

        
class HOTNODE_PT_texture(HOTNODE_PT_parent, Panel):
    bl_label = "Textures"
    bl_idname = "HOTNODE_PT_texture"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass
        # layout = self.layout
        # scene = context.scene
        # mode = scene.hot_node_tex_preset_mode
        
        # layout.use_property_split = True
        # layout.use_property_decorate = False
        
        # # Texture Apply
        # layout.label(text="Apply Settings")
        # row = layout.row()
        # row.prop(scene, "hot_node_compare_tolerance", text="Tolerance")
        # row = layout.row()
        # row.prop(scene, "hot_node_tex_dir_path", text="Folder")
        
        # # Texture Save
        # layout.separator()
        # layout.label(text="Save Texture")
        # row = layout.row()
        # row.operator("node.hot_node_texture_save", text="Save Texture")
        
        # row = layout.row()
        # row.prop(scene, "hot_node_tex_preset_mode", text="Mode")
        
        # if mode == 'KEYWORD':
        #     row = layout.row()
        #     row.prop(scene, "hot_node_tex_key", text="Key", placeholder="Key1 / Key2 / ...")
        
        
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
            
            
class HOTNODE_PT_pack_sharing(HOTNODE_PT_parent, Panel):
    bl_label = "Pack Sharing"
    bl_idname = "HOTNODE_PT_pack_sharing"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        
        # Import / Export
        col = layout.column()
        # row = col.row()
        # row.label(text="Packs")
        row = col.row(align=True)
        row.operator("import.hot_node_pack_import", icon="IMPORT", text="Import")
        row.operator("export.hot_node_pack_export", icon="EXPORT", text="Export")


classes = (
    HOTNODE_MT_pack_select,
    HOTNODE_MT_specials,
    HOTNODE_UL_presets,
    HOTNODE_PT_main,
    HOTNODE_PT_texture,
    HOTNODE_PT_texture_apply,
    HOTNODE_PT_texture_save,
    HOTNODE_PT_pack_sharing,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)