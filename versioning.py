import bpy

from . import node_parser, file
from . __init__ import bl_info


# current version
version = bl_info["version"]
blender = bpy.app.version


def ensure_preset_version(preset_name, cpreset):
    '''If trying to apply preset, CALL THIS FIRST'''
    cdata = cpreset["HN_preset_data"]
    preset_version = cdata["version"]
    if preset_version != version:
        if preset_version == [0, 1, 0]:
            cpreset = version_update_0_1_0(preset_name, cpreset)
        # we may dont have a update func between small version update, but we still update it's version data.
        cdata["version"] = version
        cdata["blender"] = blender
        file.update_preset(preset_name, cpreset)
    return cpreset


def ensure_all_pack_meta_version():
    pass
    
    
def version_update_0_1_0(preset_name, cpreset):
    cdata = cpreset["HN_preset_data"]
    pack_name = cdata["pack_name"]
    cpreset = node_parser.set_preset_data(preset_name, pack_name, cpreset=cpreset)
    return cpreset


# def version_update_0_4_X_below(preset_name, cpreset):
#     cdata = cpreset["HN_preset_data"]
#     pack_name = cdata["pack_name"]
#     cpreset = node_parser.set_preset_data(preset_name, pack_name, cpreset=cpreset)
#     return cpreset