import os
import mathutils

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.app.translations import pgettext_iface as _


from . import dev_func, dev_utils, dev_reload, dev_ui
from ..core.context.context import Context
from ..utils import constants


class HOTNODE_OT_dev_reload(Operator):
    bl_idname = "hotnode.dev_reload"
    bl_label = "Dev Reload"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..core.blender import ui, ui_context, operators, user_pref
        
        dev_ui.unregister()
        ui.unregister()
        
        def unregister():
            operators.unregister()
            ui_context.unregister()
            user_pref.unregister()
            
        def register():
            user_pref.register()
            operators.register()
            ui_context.register()
            
        def register_ui():
            ui.register()
            
        def reset_classes():
            # reset the context to ensure it is re-initialized and sm, ser, deser singletons is reset.
            Context.reset()

        bpy.app.timers.register(unregister, first_interval=0.1)
        bpy.app.timers.register(dev_reload.dev_reload, first_interval=0.2)
        bpy.app.timers.register(register, first_interval=0.3)
        bpy.app.timers.register(register_ui, first_interval=0.4)
        
        return {'FINISHED'}


class HOTNODE_OT_dev_run1(Operator):
    bl_idname = "hotnode.dev_run1"
    bl_label = "Open Addon Data Directory"
    bl_description = "Open the addon data directory"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        os.startfile(Context.fm.app_data_dir)
        return {'FINISHED'}


class HOTNODE_OT_dev_run2(Operator):
    bl_idname = "hotnode.dev_run2"
    bl_label = "Add a Node to Edit Center"
    bl_description = "extract_active_node_hierarchy"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        edit_tree = context.space_data.edit_tree
        if edit_tree:
            node = edit_tree.nodes.new("NodeReroute")
        
        return {'FINISHED'}


class HOTNODE_OT_dev_run3(Operator):
    bl_idname = "hotnode.dev_run3"
    bl_label = "Print Socket Identifier"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        for node in context.selected_nodes:
            print(f"Node: {node.name}, Type: {node.bl_idname}")
            print("Inputs:")
            for socket in node.inputs:
                print(f"{socket.name}: {socket.identifier}")
            print("Outputs:")
            for socket in node.outputs:
                print(f"{socket.name}: {socket.identifier}")

        return {'FINISHED'}


class HOTNODE_OT_dev_run4(Operator):
    bl_idname = "hotnode.dev_run4"
    bl_label = "Set Node Location"
    bl_options = {'REGISTER'}
    
    x: bpy.props.FloatProperty(
        name="Location X",
        description="Set the X location of the selected nodes",
        default=0.0
    ) # type: ignore
    
    y: bpy.props.FloatProperty(
        name="Location Y",
        description="Set the Y location of the selected nodes",
        default=0.0
    ) # type: ignore
    
    is_abs: bpy.props.BoolProperty(
        name="Absolute Location",
        description="Use absolute location instead of relative",
        default=False
    ) # type: ignore

    def execute(self, context):
        
        for node in context.space_data.edit_tree.nodes:
            if node.select:
                if self.is_abs:
                    node.location_absolute = mathutils.Vector((self.x, self.y))
                else:
                    node.location = mathutils.Vector((self.x, self.y))
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "x")
        row.prop(self, "y")
        layout.prop(self, "is_abs")


class HOTNODE_OT_dev_run5(Operator):
    bl_idname = "hotnode.dev_run5"
    bl_label = "Print Node Location"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        for node in context.space_data.edit_tree.nodes:
            if node.select:
                if constants.IS_NODE_HAS_LOCATION_ABSOLUTE:
                    print(f"{node.location} {node.location_absolute} {node.name}")
                else:
                    print(f"{node.location} {node.name}")
        
        return {'FINISHED'}


class HOTNODE_OT_dev_run6(Operator):
    bl_idname = "hotnode.dev_run6"
    bl_label = "Load Image"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        img = bpy.data.images.load(r"E:\.temp\HotNodeImageTest\t1.png")
        tex: bpy.types.ImageTexture = bpy.data.textures.new("HotNodeDevImg", type='IMAGE')
        tex.image = img
        tex.extension = 'CLIP'
        # tex.preview
            
        return {'FINISHED'}


class HOTNODE_OT_dev_run7(Operator):
    bl_idname = "hotnode.dev_run7"
    bl_label = "Set Preset Indent"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        Context.pack_selected.save_preset(Context.preset_selected)
        return {'FINISHED'}


class HOTNODE_OT_dev_run8(Operator):
    bl_idname = "hotnode.dev_run8"
    bl_label = "Add All Nodes"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        dev_utils.add_all_nodes_to_edit_tree(context)
        
        return {'FINISHED'}


class HOTNODE_OT_dev_run9(Operator):
    bl_idname = "hotnode.dev_run9"
    bl_label = "Add Slot For File Output"
    bl_options = {'REGISTER'}
    
    def execute(self, context):

        node = context.active_node
        node.file_output_items.new("Test Slot")
        return {'FINISHED'}


class HOTNODE_OT_dev_run10(Operator):
    bl_idname = "hotnode.dev_run10"
    bl_label = "Open Addon Data Directory"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        fm = Context.fm
        fm.open_path_with_default_browser(fm.app_data_dir)
        return {'FINISHED'}
    
classes = (
    HOTNODE_OT_dev_reload,
    HOTNODE_OT_dev_run1,
    HOTNODE_OT_dev_run2,
    HOTNODE_OT_dev_run3,
    HOTNODE_OT_dev_run4,
    HOTNODE_OT_dev_run5,
    HOTNODE_OT_dev_run6,
    HOTNODE_OT_dev_run7,
    HOTNODE_OT_dev_run8,
    HOTNODE_OT_dev_run9,
    HOTNODE_OT_dev_run10,
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