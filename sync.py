import bpy

from . import file, props_py, props_bl, gui, ops_invoker


def sync(props, from_gui=False):
    # file.refresh_root_meta_cache()
    file.ensure_pack_root()
    pack_names = file.load_packs()
    file.refresh_root_meta_cache()
    pack_selected = props_py.gl_pack_selected
    if pack_selected is None or not pack_selected.name in pack_names:
        pack_selected_name = file.root_meta_cache["pack_selected"]
        pack_selected = props_py.gl_pack_selected = props_py.gl_packs.get(pack_selected_name, None)
    # we can't modify the bl props via gui's context. invoke ops instead to do it in another thread.
    if from_gui:
        ops_invoker.late_call_helper_ops('PACK_SELECT', pack_selected.name)
    else:
        props_bl.select_pack(props, pack_selected)
    gui.ensure_existing_pack_menu()
    
    
def ensure_sync(context: bpy.types.Context|None=None, ops: bpy.types.Operator|None=None, from_gui=False):
    ensure_ui_pack_name_sync(context.scene.hot_node_props, late_ensure=from_gui)
    if not file.check_sync():
        from . history import discard_steps
        discard_steps()
        sync(context.scene.hot_node_props, from_gui=from_gui)
        # we cant modify context when gui is drawing, so do it later
        if from_gui:
            ops_invoker.late_refresh()
        if ops is not None:
            ops.report({'WARNING'}, "Out of sync, nothing happend but auto refreshing. Now it's READY!")
        return False
    return True


def ensure_ui_pack_name_sync(hot_node_props, late_ensure=False):
    real_pack_selected_name = props_py.get_gl_pack_selected_name()
    if hot_node_props.pack_selected_name != real_pack_selected_name:
        if late_ensure:
            ops_invoker.late_call_helper_ops('PACK_NAME_SYNC', None)
        else:
            props_py.skip_pack_rename_callback = True
            hot_node_props.pack_selected_name = real_pack_selected_name
            props_py.skip_pack_rename_callback = False