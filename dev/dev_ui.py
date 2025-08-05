import bpy
from bpy.types import Menu, Panel, UIList
from . import dev_ops
from ..core.context.context import Context

class HOTNODE_PT_dev_run(Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Hot Node"
    bl_label = "Developer Tools"
    bl_idname = "HOTNODE_PT_developer_tools"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        col = row.column(align=True)
        
        # Show Dev Ops
        col.operator(f"hotnode.dev_reload", icon='FILE_REFRESH')
        col.separator()
        for ops in dev_ops.classes:
            if ops.bl_idname.startswith("hotnode.dev_run"):
                col.operator(ops.bl_idname)
            
        # Image Test
        tex = bpy.data.textures.get("HotNodeDevImg")
        if tex:
            col.template_preview(tex, show_buttons=False, preview_id="hotnode.preset_preview")
        # Show Context
        row = layout.row()
        col = row.column()
        col.label(text="Context:")
        col.label(text=f"Pack: {Context.pack_selected.name if Context.pack_selected else ''}")
        col.label(text=f"Preset: {Context.preset_selected.name if Context.preset_selected else ''}")
        col.label(text=f"Presets:")
        if Context.pack_selected is not None:
            for preset in Context.pack_selected.ordered_presets:
                col.label(text=f"  {preset.name}")
        col.label(text=f"Packs:")
        if Context.packs is not None:
            for pack_name in Context.packs.keys():
                col.label(text=f"  {pack_name}")
        else:
            col.label(text="  None")
            
        # When reloading the uic may not be set yet, which will crashes blender
        uic = context.window_manager.hot_node_ui_context
        col = row.column()
        col.label(text="UI Context:")
        col.label(text=f"Pack: {uic.pack_selected_name}")
        col.label(text=f"Preset: {uic.presets[uic.preset_selected_idx].name if uic.presets else ''}")
        col.label(text=f"Presets:")
        for preset in uic.presets:
            col.label(text=f"  {preset.name}")

classes = (
    HOTNODE_PT_dev_run,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass