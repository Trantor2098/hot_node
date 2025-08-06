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
    bl_label = "add_all_nodes_to_edit_tree"
    bl_description = "add_all_nodes_to_edit_tree"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        dev_utils.add_all_nodes_to_edit_tree(context)
        
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
    bl_label = "Print Current Blender Version"
    bl_description = "extract_selected_nodes_unique_attr_type"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        print(constants.BLENDER_VERSION_STR)

        return {'FINISHED'}


class HOTNODE_OT_dev_run4(Operator):
    bl_idname = "hotnode.dev_run4"
    bl_label = "find_nodes_having_dynamic_inputs"
    bl_description = "find_nodes_having_dynamic_inputs"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        pass
        
        return {'FINISHED'}


class HOTNODE_OT_dev_run5(Operator):
    bl_idname = "hotnode.dev_run5"
    bl_label = "Try Report Using Context Ops"
    bl_description = "extract_tree_unique_attr_type"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        
        print("[HOT NODE] Trying to report using context ops...")
        from ..utils.reporter import Reporter
        Reporter.report_finish("This is a test report using context ops.")
        
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
    bl_label = "Auto Save"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..services.autosave import AutosaveService
        AutosaveService.autosave_packs()

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
    bl_label = "load_preset"
    bl_options = {'REGISTER'}
    
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
    
    def execute(self, context):
        
        tree = context.space_data.edit_tree
        deser_manager = dev_func.load_preset(context)
        # call translate ops for moving nodes. escaping select NodeFrames because parent's movement will be applied to the child nodes,
        # which would make child nodes move times far, and cause frame shake. reselect them later.
        selected_node_frames = []
        for node in deser_manager.deser_context.newed_main_tree_nodes:
            if node.bl_idname == "NodeFrame":
                selected_node_frames.append(node)
                node.select = False
                
        bpy.ops.node.translate_attach_remove_on_cancel('INVOKE_DEFAULT')
        
        # reselect the NodeFrames after nodes that should be translated are assigned to the ops, so the selection will only affect deletion, not movement.
        for node in selected_node_frames:
            node.select = True
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.store_mouse_cursor(context, event)
        return self.execute(context)


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