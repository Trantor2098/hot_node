import bpy

from . import props_py


def call_helper_ops_directly():
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')


def call_helper_ops(mode: str, param):
    '''Call helpder ops, pass <mode> <param> into the ops.
    
    - mode: Enum in 'PACK_RENAME', 'PACK_SELECT'.'''
    props_py.helper_mode = mode
    props_py.helper_param = param
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')
    
    
def addon_expand():
    bpy.ops.preferences.addon_expand(module=__package__)
    
    
def late_call_helper_ops(mode, param):
    props_py.helper_mode = mode
    props_py.helper_param = param
    bpy.app.timers.register(call_helper_ops_directly)


def refresh():
    bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')

    
def late_refresh(interval=0.0):
    bpy.app.timers.register(refresh, first_interval=interval)
    
    
def late_undo(interval=0.0):
    bpy.app.timers.register(bpy.ops.ed.undo, first_interval=interval)
    
    
def late_addon_expand(interval=0.0):
    bpy.app.timers.register(addon_expand, first_interval=interval)
    
    
def update_pack_menu_for_pack_renaming(new_pack_name):
    props_py.helper_mode = 'PACK_RENAME'
    props_py.helper_param = new_pack_name
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')