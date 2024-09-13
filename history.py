import bpy

from collections import deque

from . import file, ops_invoker, props_py, gui, i18n


step_checker_cache = True

# For syncing history between two thread.
# Sometimes between two hot node steps there is a blender step changes our values. 
# This helps us to do one more sync when undo to ensure the values won't be changed.
last_undo_redo_excuted = 0


class Step():
    
    def __init__(self, context: bpy.types.Context, name: str, refresh: bool=True,
                 deleted_paths: list=[], changed_paths: list=[], created_paths: list=[],
                 undo_callback=None, redo_callback=None, 
                 undo_callback_param=None, redo_callback_param=None):
        '''Push a step into history.
        
        - context: Context to get registered properties.
        - name: Step's name, will be used to show infos to the user.
        - deleted_paths: Paths of files that will be deleted in this step. Set it when newing step!
        - changed_paths: Paths of files that will be changed in this step. Set it when newing step!
        - created_paths: Paths of files that will be created in this step. Set it after changes werfe made.
        
        - undo_callback: Callback function(s) that will be invoked when this step undos. 
          Receive two params: scene, undo_callback_param. You can pass multiple callbacks with tuple like (callback1, callback2), 
          then pass multiple undo_callback_param (param1, param2), the callback1 will use the param1, callback2 will use the param2.
        
        - redo_callback: Just like the undo_callback, will be invoked when redo.
        - undo_callback_param: Param(s) invoked by undo_callback.
        - undo_callback_param: Param(s) invoked by redo_callback.'''
        
        global steps, undid_steps, step_num
        self.name = name
        self.refresh = refresh
        self.deleted_paths = deleted_paths
        self.his_deleted_paths = file.push_history(deleted_paths, "delete")
        self.changed_paths = changed_paths
        self.his_changed_paths = file.push_history(changed_paths, "change")
        self.created_paths = created_paths
        self.his_created_paths = []
        self.undo_callback = undo_callback
        self.redo_callback = redo_callback
        self.undo_callback_param = undo_callback_param
        self.redo_callback_param = redo_callback_param
        # used to undo "undo" when undo unsynced steps, protecting props from being modified by user undo.
        self.discarded = False
        
        if step_num >= 192:
            del_step_paths(steps[191])
        else:
            step_num += 1
            
        steps.appendleft(self)
        for step in undid_steps:
            del_step_paths(step)
            
        undid_steps.clear()
        
        context.scene.hot_node_props.step_checker = not context.scene.hot_node_props.step_checker
    
    def undo(self, scene: bpy.types.Scene):
        global last_undo_redo_excuted, step_num
        if not file.check_sync():
            discard_steps()
        from . sync import sync
        if self.discarded:
            sync(scene.hot_node_props)
            last_undo_redo_excuted = 3
            infos = [i18n.msg["gui_info_undo_skip"].format(step_name=self.name), i18n.msg["gui_info_undo_redo_skip_reason"]]
            gui.set_gui_info(infos, 3.0, 'LINK_BLEND')
        else:
            # Create Undo
            self.his_created_paths = file.push_history(self.created_paths, "create")
            file.del_paths(self.created_paths)
            # Delete Undo
            file.pull_history(self.deleted_paths, self.his_deleted_paths)
            # Change Undo
            new_his_changed_paths = file.push_history(self.changed_paths)
            file.pull_history(self.changed_paths, self.his_changed_paths)
            self.his_changed_paths = new_his_changed_paths
            
            if self.refresh:
                sync(scene.hot_node_props)
            if self.undo_callback is not None:
                if isinstance(self.undo_callback, tuple):
                    for i, callback in enumerate(self.undo_callback):
                        callback(scene, self.undo_callback_param[i])
                else:
                    self.undo_callback(scene, self.undo_callback_param)
            gui.set_gui_info([i18n.msg["gui_info_undo_step"].format(step_name=self.name)], 2.0, 'LOOP_BACK')
        step_num -= 1
        
    def redo(self, scene: bpy.types.Scene):
        global last_undo_redo_excuted, step_num
        if not file.check_sync():
            discard_steps()
        from . sync import sync
        if self.discarded:
            sync(scene.hot_node_props)
            last_undo_redo_excuted = 3
            infos = [i18n.msg["gui_info_redo_skip"].format(step_name=self.name), i18n.msg["gui_info_undo_redo_skip_reason"]]
            gui.set_gui_info(infos, 3.0, 'LINK_BLEND')
        else:
            # Create Redo
            file.pull_history(self.created_paths, self.his_created_paths)
            # Delete Redo
            self.his_deleted_paths = file.push_history(self.deleted_paths, "delete")
            file.del_paths(self.deleted_paths)
            # Change Redo
            new_his_changed_paths = file.push_history(self.changed_paths)
            file.pull_history(self.changed_paths, self.his_changed_paths)
            self.his_changed_paths = new_his_changed_paths
            
            if self.refresh:
                sync(scene.hot_node_props)
            if self.redo_callback is not None:
                if isinstance(self.undo_callback, tuple):
                    for i, callback in enumerate(self.redo_callback):
                        callback(scene, self.redo_callback_param[i])
                else:
                    self.redo_callback(scene, self.redo_callback_param)
            gui.set_gui_info([i18n.msg["gui_info_redo_step"].format(step_name=self.name)], 2.0, 'LOOP_FORWARDS')
        step_num += 1


steps: deque[Step] = deque(maxlen=192)
step_num = 0
undid_steps: list[Step] = []


# Callbacks for step undo redo
def select_pack_callback(scene: bpy.types.Scene, pack_name):
    props = scene.hot_node_props
    ops_invoker.call_helper_ops('PACK_SELECT', pack_name)
    
    
def select_preset_callback(scene: bpy.types.Scene, preset_selected_idx: int):
    scene.hot_node_props.preset_selected = preset_selected_idx
    
    
def rename_pack_callback(scene: bpy.types.Scene, src_dst_names: tuple):
    props = scene.hot_node_props
    src_name, dst_name = src_dst_names
    props_py.skip_pack_rename_callback = True
    props.pack_selected_name = dst_name
    props_py.skip_pack_rename_callback = False
    file.rename_pack(props_py.gl_pack_selected.name, dst_name)
    
    
def rename_preset_callback(scene: bpy.types.Scene, presetref_srcname_dstname: tuple):
    # props = scene.hot_node_props
    preset, src_name, dst_name = presetref_srcname_dstname
    props_py.skip_preset_rename_callback = True
    preset.name = dst_name
    props_py.skip_preset_rename_callback = False
    file.rename_preset(src_name, dst_name)
    
    
def preset_move_to(scene, src_dst_idx: tuple):
    '''(selected_idx, dst_idx)'''
    presets = scene.hot_node_props.presets
    selected_idx, dst_idx = src_dst_idx
    preset = presets[selected_idx]
    name, type = preset.name, preset.type
    if selected_idx > dst_idx:
        props_py.skip_preset_rename_callback = True
        for i in range(selected_idx - dst_idx):
            presets[selected_idx - i].name = presets[selected_idx - i - 1].name
            presets[selected_idx - i].type = presets[selected_idx - i - 1].type
    elif selected_idx < dst_idx:
        props_py.skip_preset_rename_callback = True
        for i in range(selected_idx, dst_idx):
            presets[i].name = presets[i + 1].name
            presets[i].type = presets[i + 1].type
    else:
        return
    presets[dst_idx].name = name
    presets[dst_idx].type = type
    props_py.skip_preset_rename_callback = False
    
    
# Functios for modifying step states
def discard_steps():
    global steps
    global undid_steps
    for step in steps:
        step.discarded = True
    for step in undid_steps:
        step.discarded = True
        
        
def del_step_paths(step: Step):
    file.try_del_paths(step.his_changed_paths, step.his_created_paths, step.his_deleted_paths)
    

# Function to be registed
def undo_redo_pre(scene, _):
    props_py.skip_preset_rename_callback = True
    props_py.skip_step_checker_update = True
    props_py.skip_fast_create_preset_name_callback = True
    props_py.skip_preset_selected_callback = True


def undo_post(scene, _):
    global steps, step_checker_cache, last_undo_redo_excuted
    step_checker = scene.hot_node_props.step_checker
    # if we are undoing hot node's operators, the step_num will decrease by one and be detected (blender did this), 
    # which will bring us into our undo logic
    if step_checker_cache != step_checker and steps:
        step_checker_cache = step_checker
        step = steps.popleft()
        undid_steps.append(step)
        step.undo(scene)
    else:
        if last_undo_redo_excuted > 0:
            last_undo_redo_excuted -= 1
            from . sync import sync
            sync(scene.hot_node_props)
        from . sync import ensure_ui_pack_name_sync
        ensure_ui_pack_name_sync(scene.hot_node_props, late_ensure=True)
    props_py.skip_preset_rename_callback = False
    props_py.skip_step_checker_update = False
    props_py.skip_fast_create_preset_name_callback = False
    props_py.skip_preset_selected_callback = False
        
        
def redo_post(scene, _):
    global steps, step_checker_cache, last_undo_redo_excuted
    step_checker = scene.hot_node_props.step_checker
    # if we are undoing hot node's operators, the step_num will increase by one and be detected (blender did this), 
    # which will bring us into our undo logic
    if step_checker != step_checker_cache and undid_steps:
        step_checker_cache = scene.hot_node_props.step_checker
        step = undid_steps.pop()
        steps.appendleft(step)
        step.redo(scene)
    else:
        if last_undo_redo_excuted:
            last_undo_redo_excuted -= 1
            from . sync import sync
            sync(scene.hot_node_props)
        from . sync import ensure_ui_pack_name_sync
        ensure_ui_pack_name_sync(scene.hot_node_props, late_ensure=True)
    props_py.skip_preset_rename_callback = False
    props_py.skip_step_checker_update = False
    props_py.skip_fast_create_preset_name_callback = False
    props_py.skip_preset_selected_callback = False


def register():
    bpy.app.handlers.undo_pre.append(undo_redo_pre)
    bpy.app.handlers.undo_post.append(undo_post)
    bpy.app.handlers.redo_pre.append(undo_redo_pre)
    bpy.app.handlers.redo_post.append(redo_post)


def unregister():
    if undo_redo_pre in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.remove(undo_redo_pre)
    if undo_redo_pre in bpy.app.handlers.redo_pre:
        bpy.app.handlers.redo_pre.remove(undo_redo_pre)
    if undo_post in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(undo_post)
    if redo_post in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(redo_post)
    for step in steps:
        del_step_paths(step)
    for step in undid_steps:
        del_step_paths(step)