# ======== About Packs & Presets
# TODO put presets in packs
class Pack():
    
    def __init__(self, name, icon='NONE', show_icon=False):
        self.name = name
        self.icon = icon
        self.show_icon = show_icon
        
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
setter_bug_infos = []


# ======== About History
# for undo_post and redo_post not to sync the checker and the checker cache
skip_step_checker_update = False


# ======== About Hot Node Props
skip_pack_rename_callback = False
skip_preset_rename_callback = False
skip_fast_create_preset_name_callback = False
skip_preset_selected_callback = False


# ======== About Hot Node GUI
pack_name_of_fast_create = ""
pack_with_icon_num = 0

def update_pack_with_icon_num():
    global pack_with_icon_num
    pack_with_icon_num = 0
    for pack in gl_packs.values():
        if pack.icon != 'NONE':
            pack_with_icon_num += 1


# ======== About Hot Node Setter
# if the ng failed to be re-used, the newly getted ng will be used to compare with the later ngs. 
# refresh everytime the re-usage failed. <preset_name: actually getted ng name in blender>
# getted_ng_names = {}

# ======== About Enums
# 'NONE' is a special value, means no icon
pack_icons = ('OUTLINER_COLLECTION',
              'COLLECTION_COLOR_01', 'COLLECTION_COLOR_02', 'COLLECTION_COLOR_03', 'COLLECTION_COLOR_04',
              'COLLECTION_COLOR_05', 'COLLECTION_COLOR_06', 'COLLECTION_COLOR_07', 'COLLECTION_COLOR_08',
              'SNAP_FACE',
              'SEQUENCE_COLOR_01', 'SEQUENCE_COLOR_02', 'SEQUENCE_COLOR_03', 'SEQUENCE_COLOR_04',
              'SEQUENCE_COLOR_05', 'SEQUENCE_COLOR_06', 'SEQUENCE_COLOR_07', 'SEQUENCE_COLOR_08',
              'EVENT_A', 'EVENT_B', 'EVENT_C', 'EVENT_D', 'EVENT_E', 'EVENT_F', 'EVENT_G', 'EVENT_H',
              'EVENT_I', 'EVENT_J', 'EVENT_K', 'EVENT_L', 'EVENT_M', 'EVENT_N', 'EVENT_O', 'EVENT_P',
              'EVENT_Q', 'EVENT_R', 'EVENT_S', 'EVENT_T', 'EVENT_U', 'EVENT_V', 'EVENT_W', 'EVENT_X',
              'EVENT_Y', 'EVENT_Z',
              'EVENT_ZEROKEY', 'EVENT_ONEKEY', 'EVENT_TWOKEY', 'EVENT_THREEKEY', 'EVENT_FOURKEY', 'EVENT_FIVEKEY',
              'EVENT_SIXKEY', 'EVENT_SEVENKEY', 'EVENT_EIGHTKEY', 'EVENT_NINEKEY',
              'NODE_MATERIAL', 'GEOMETRY_NODES', 'NODE_COMPOSITING', 'NODE_TEXTURE', 'FILE_IMAGE', 'LIGHT', 'SCENE', 'FUND')

pack_icons1 = ('OUTLINER_COLLECTION',
               'COLLECTION_COLOR_01', 'COLLECTION_COLOR_02', 'COLLECTION_COLOR_03', 'COLLECTION_COLOR_04',
               'COLLECTION_COLOR_05', 'COLLECTION_COLOR_06', 'COLLECTION_COLOR_07', 'COLLECTION_COLOR_08')
pack_icons2 = ('SNAP_FACE',
               'SEQUENCE_COLOR_01', 'SEQUENCE_COLOR_02', 'SEQUENCE_COLOR_03', 'SEQUENCE_COLOR_04',
               'SEQUENCE_COLOR_05', 'SEQUENCE_COLOR_06', 'SEQUENCE_COLOR_07', 'SEQUENCE_COLOR_08')
pack_icons3 = ('EVENT_A', 'EVENT_B', 'EVENT_C', 'EVENT_D', 'EVENT_E', 'EVENT_F', 'EVENT_G', 'EVENT_H',
               'EVENT_I', 'EVENT_J', 'EVENT_K', 'EVENT_L', 'EVENT_M', 'EVENT_N', 'EVENT_O', 'EVENT_P',
               'EVENT_Q', 'EVENT_R', 'EVENT_S', 'EVENT_T', 'EVENT_U', 'EVENT_V', 'EVENT_W', 'EVENT_X',
               'EVENT_Y', 'EVENT_Z', 
               'EVENT_ZEROKEY', 'EVENT_ONEKEY', 'EVENT_TWOKEY', 'EVENT_THREEKEY', 'EVENT_FOURKEY', 'EVENT_FIVEKEY',
               'EVENT_SIXKEY', 'EVENT_SEVENKEY', 'EVENT_EIGHTKEY', 'EVENT_NINEKEY')
pack_icons4 = ('NODE_MATERIAL', 'GEOMETRY_NODES', 'NODE_COMPOSITING', 'NODE_TEXTURE', 'FILE_IMAGE', 'LIGHT', 'SCENE', 'FUND')