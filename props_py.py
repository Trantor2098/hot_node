# ======== About Packs & Presets
# TODO put presets in packs
class Pack():
    
    def __init__(self, name):
        self.name = name
        
# packs will be loaded once the blender open
gl_packs = {}
# for script to get current selected pack, for CRUDing it.
gl_pack_selected: Pack = None

def get_gl_pack_selected_name():
    return gl_pack_selected.name if gl_pack_selected is not None else ""

# only for checking rename as a name cache, wont be used to get preset
gl_preset_selected = ""


# ======== About Operators
# When invoking helper ops, these will be passed into the helper to decide helper's actions.
helper_mode = 'NONE'
helper_param = None
report_type = ''
report_message = ""
gui_info = ""


# ======== About History
# for undo_post and redo_post not to sync the checker and the checker cache
skip_step_checker_update = False


# ======== About Hot Node Props
skip_pack_rename_callback = False
skip_preset_rename_callback = False
skip_fast_create_preset_name_callback = False
skip_preset_selected_callback = False