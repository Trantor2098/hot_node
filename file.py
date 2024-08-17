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

import os, shutil, json, zipfile, tempfile, time

from . import utils, props_py
from . __init__ import bl_info


version = bl_info["version"]
blender = bl_info["blender"]

# Paths
addon_dir_path = os.path.dirname(__file__)
temp_dir_path = tempfile.gettempdir()
autosave_dir_path = os.path.join(temp_dir_path, "hot_node_autosave")
history_dir_path = os.path.join(addon_dir_path, "hot_node_history")
pack_root_dir_path = os.path.join(addon_dir_path, "preset_packs")
pack_selected_dir_path = os.path.join(pack_root_dir_path, "")
pack_selected_meta_path = ""
root_meta_path = os.path.join(pack_root_dir_path, ".metadata.json")

# Metas
last_mtime = 0.0
pack_meta_cache = {}
root_meta_cache = {"pack_selected": "", 
                   "last_mtime": 0.0}


# Initialize & finalize files when opening & closing blender
def init():
    global last_mtime
    load_packs_and_get_names()
    ensure_pack_root()
    ensure_dir_existing(history_dir_path)
    autosave_packs()
    last_mtime = refresh_root_meta_cache_and_get_mtime_data()
    pack_selected_name = root_meta_cache["pack_selected"]
    props_py.gl_pack_selected = props_py.gl_packs.get(pack_selected_name, None)
    
    
def finalize():
    autosave_packs()
    clear_outdated_autosave_packs()


# Sync & Check
def ensure_pack_root():
    '''Read root meta to global root_meta_cache, recover autosaved files when there is no pack root dir (mostly happen when updating add-on)'''
    global root_meta_cache
    if not os.path.exists(pack_root_dir_path):
        os.mkdir(pack_root_dir_path)
        auto_recover_packs()
        pack_names = load_packs_and_get_names()
        if len(pack_names) == 0:
            select_pack(None)
        else:
            select_pack(props_py.gl_packs[pack_names[0]])
    elif not os.path.exists(root_meta_path):
        pack_names = load_packs_and_get_names()
        if len(pack_names) == 0:
            select_pack(None)
        else:
            select_pack(props_py.gl_packs[pack_names[0]])
            
            
def ensure_dir_existing(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        
        
def check_sync():
    global last_mtime
    mtime_data = refresh_root_meta_cache_and_get_mtime_data()
    if mtime_data != last_mtime:
        last_mtime = mtime_data
        return False
    return True


def check_pack_existing():
    if os.path.exists(pack_selected_dir_path):
        return True
    return False


def check_preset_existing(preset_name):
    preset_path = os.path.join(pack_selected_dir_path, preset_name)
    if os.path.exists(preset_path):
        return True
    return False


# Get File Info & Path
def get_pack_selected_meta_path():
    os.path.join(pack_selected_dir_path, ".metadata.json")
    
    
def get_pack_meta_path(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    return pack_meta_path


def get_pack_path(pack_name):
    return os.path.join(pack_root_dir_path, pack_name)


def get_preset_path(preset_name):
    return os.path.join(pack_selected_dir_path, preset_name)
    
    
def get_root_meta_path():
    os.path.join(pack_root_dir_path, ".metadata.json")
    
    
def get_pack_mtime(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    return os.path.getmtime(pack_meta_path)


# Get & Set Meta
def refresh_root_meta_cache_and_get_mtime_data():
    global root_meta_cache
    root_meta_cache = read_root_meta()
    mtime_data = root_meta_cache.get("last_mtime", 0.0)
    return mtime_data


def update_root_meta_cache_mtime():
    global root_meta_cache, last_mtime
    last_mtime = time.time()
    root_meta_cache["last_mtime"] = last_mtime

    
# CRUD of Json
def write_json(file_path: str, data: dict):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=1)


def read_json(file_path) -> dict:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
    
def write_meta():
    update_root_meta_cache_mtime()
    write_json(pack_selected_meta_path, pack_meta_cache)
    write_json(root_meta_path, root_meta_cache)
    
    
def write_root_meta():
    write_json(root_meta_path, root_meta_cache)
    
    
def read_pack_meta(pack_name: str|None=None):
    if pack_name is None:
        if os.path.exists(pack_selected_meta_path):
            return read_json(pack_selected_meta_path)
    else:
        meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
        if os.path.exists(meta_path):
            return read_json(meta_path)

    
def read_root_meta():
    if os.path.exists(root_meta_path):
        return read_json(root_meta_path)
    
    
def read_metas():
    if os.path.exists(root_meta_path) and os.path.exists(pack_selected_meta_path):
        return read_json(root_meta_path), read_json(pack_selected_meta_path)
    
    
def refresh_root_meta_cache():
    global root_meta_cache
    root_meta_cache = read_root_meta()
    
    
def check_read_pack_meta(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    if not os.path.exists(pack_meta_path):
        return 'INEXISTENCE'
    metadata: dict = read_json(pack_meta_path)
    keys = list(metadata.keys())
    if keys != ["order", "tree_types", "version"]:
        return 'INVALID_META'
    return metadata


# Read Existing Files
def read_existing_files(dir_path, suffix=".zip", cull_suffix=True):
    existing_file_names = os.listdir(dir_path)
    filtered_file_names: list[str] = []
    if cull_suffix:
        suffix_length = len(suffix)
        for file_name in existing_file_names:
            if file_name.endswith(suffix):
                filtered_file_names.append(file_name[:-suffix_length])
    else:
        for file_name in existing_file_names:
            if file_name.endswith(suffix):
                filtered_file_names.append(file_name)
    return filtered_file_names


# History Record
def push_history(ori_paths, extra_identifier="d"):
    '''Copy the file to the history folder and return the copied file path.'''
    his_paths = []
    path_num = len(ori_paths)
    for i in range(path_num):
        ori_path = ori_paths[i]
        identifier = "_".join((str(time.time()), str(i), extra_identifier))
        dot_suffix = utils.get_dot_suffix(ori_path, ".zip", ".json")
        if dot_suffix is None:
            his_path = os.path.join(history_dir_path, identifier)
            shutil.copytree(ori_path, his_path)
        else:
            dst_name = "".join((identifier, dot_suffix))
            his_path = os.path.join(history_dir_path, dst_name)
            shutil.copyfile(ori_path, his_path)
        his_paths.append(his_path)
    return his_paths


def pull_history(ori_paths, his_paths):
    path_num = len(ori_paths)
    for i in range(path_num):
        ori_path = ori_paths[i]
        his_path = his_paths[i]
        dot_suffix = utils.get_dot_suffix(ori_path, ".zip", ".json")
        if dot_suffix is None:
            if os.path.exists(ori_path):
                shutil.rmtree(ori_path)
            shutil.copytree(his_path, ori_path)
            shutil.rmtree(his_path)
        else:
            if os.path.exists(ori_path):
                os.remove(ori_path)
            shutil.copyfile(his_path, ori_path)
            os.remove(his_path)
            
    
def del_paths(paths):
    for path in paths:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    

# CRUD of Pack and Preset
def create_pack(pack_name):
    global root_meta_cache
    global pack_meta_cache
    global pack_selected_dir_path
    global pack_selected_meta_path
    pack_selected_dir_path = os.path.join(pack_root_dir_path, pack_name)
    pack_selected_meta_path = os.path.join(pack_selected_dir_path, ".metadata.json")
    # create pack metadata
    root_meta_cache["pack_selected"] = pack_name
    pack_meta_cache = {}
    pack_meta_cache["order"] = []
    pack_meta_cache["tree_types"] = {}
    pack_meta_cache["version"] = version
    os.mkdir(pack_selected_dir_path)
    write_meta()
    # reload packs to get right order of packs
    load_packs_and_get_names()
    return pack_selected_dir_path


def delete_pack(pack_name):
    global pack_meta_cache
    pack_dir_path = os.path.join(pack_root_dir_path, pack_name)
    shutil.rmtree(pack_dir_path)
    return pack_dir_path


def clear_pack(pack_names):
    for pack_name in pack_names:
        delete_pack(pack_name)


def rename_pack(old_pack_name, new_pack_name):
    old_path = os.path.join(pack_root_dir_path, old_pack_name)
    new_path = os.path.join(pack_root_dir_path, new_pack_name)
    os.rename(old_path, new_path)
    # reload packs to get the right order of packs
    load_packs_and_get_names()
    update_root_meta_cache_mtime()
    select_pack(props_py.gl_packs[new_pack_name])


def load_packs_and_get_names():
    '''Load packs from folder into gl_packs and return pack names'''
    if not os.path.exists(pack_root_dir_path):
        ensure_pack_root()
    pack_names = os.listdir(pack_root_dir_path)
    if ".metadata.json" in pack_names:
        pack_names.remove(".metadata.json")
    props_py.gl_packs.clear()
    new_pack_num = len(pack_names)
    for i in range(new_pack_num):
        pack_name = pack_names[i]
        pack = props_py.Pack(pack_name)
        props_py.gl_packs[pack_name] = pack
    return pack_names


def select_pack(pack: props_py.Pack|None):
    global pack_meta_cache
    global root_meta_cache
    global pack_selected_meta_path
    global pack_selected_dir_path
    if pack is None:
        pack_meta_cache = {}
        pack_meta_cache["order"] = []
        pack_meta_cache["tree_types"] = {}
        pack_meta_cache["version"] = version
        pack_selected_meta_path = ""
        root_meta_cache["pack_selected"] = ""
    else:
        pack_selected_dir_path = os.path.join(pack_root_dir_path, pack.name)
        pack_selected_meta_path = os.path.join(pack_selected_dir_path, ".metadata.json")
        pack_meta_cache = read_pack_meta()
        root_meta_cache["pack_selected"] = pack.name
    props_py.gl_pack_selected = pack
    write_root_meta()
    
    
def import_pack(from_file_path: str, new_pack_name: str):
    global pack_selected_dir_path
    size = os.path.getsize(from_file_path)
    # if zip file is bigger than 150 Mib
    if size > 150 * 1048576:
        return 'OVER_SIZE'
    file = zipfile.ZipFile(from_file_path)
    new_pack_dir_path = os.path.join(pack_root_dir_path, new_pack_name)
    file.extractall(new_pack_dir_path)
    file.close()
    metadata = check_read_pack_meta(new_pack_name)
    if metadata == 'META_LACK':
        shutil.rmtree(new_pack_dir_path)
        return 'META_LACK'
    if metadata == 'INVALID_META':
        shutil.rmtree(new_pack_dir_path)
        return 'INVALID_META'
    return 'SUCCESS'
             

def export_selected_pack(dst_file_path):
    global pack_selected_dir_path
    zip = zipfile.ZipFile(dst_file_path, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(pack_selected_dir_path):
        relative_root = '' if root == pack_selected_dir_path else root.replace(pack_selected_dir_path, '') + os.sep
        for filename in files:
            zip.write(os.path.join(root, filename), relative_root + filename)
    zip.close()
    
    
def export_packs(pack_names, dst_dir_path):
    existing_zip_namebodys = read_existing_files(dst_dir_path, suffix=".zip")
            
    for pack in pack_names:
        pack_dir_path = os.path.join(pack_root_dir_path, pack)
        
        ensured_pack_name = utils.ensure_unique_name(pack, -1, existing_zip_namebodys)
            
        dst_file_name = ".".join((ensured_pack_name, "zip"))
        dst_file_path = os.path.join(dst_dir_path, dst_file_name)
        zip = zipfile.ZipFile(dst_file_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(pack_dir_path):
            relative_root = '' if root == pack_dir_path else root.replace(pack_dir_path, '') + os.sep
            for filename in files:
                zip.write(os.path.join(root, filename), relative_root + filename)
        zip.close()
        
        
def autosave_packs():
    ensure_dir_existing(autosave_dir_path)
    pack_names = load_packs_and_get_names()
    
    existing_zips = read_existing_files(autosave_dir_path, suffix=".zip", cull_suffix=False)
    existing_packs = []
    for i in range(len(existing_zips)):
        file_name = existing_zips[i]
        existing_packs.append(utils.get_string_between_words(file_name, None, ("_autosave_", "_deprecated_")))
            
    for pack_name in pack_names:
        pack_dir_path = os.path.join(pack_root_dir_path, pack_name)
        
        # remove the previous autosaved file with the same name
        if pack_name in existing_packs:
            zip_idx = existing_packs.index(pack_name)
            ealry_zip_path = os.path.join(autosave_dir_path, existing_zips[zip_idx])
            os.remove(ealry_zip_path)
            
        autosave_time_str = utils.get_autosave_time_str()
        ensured_pack_name = "".join((pack_name, "_autosave_", autosave_time_str))
            
        dst_file_name = ".".join((ensured_pack_name, "zip"))
        dst_file_path = os.path.join(autosave_dir_path, dst_file_name)
        file_name = zipfile.ZipFile(dst_file_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(pack_dir_path):
            relative_root = '' if root == pack_dir_path else root.replace(pack_dir_path, '') + os.sep
            for filename in files:
                file_name.write(os.path.join(root, filename), relative_root + filename)
        file_name.close()
    
    # if the autosaved pack no longer exists in the current packs, mark them as deprecated so that if user update the add-on these packs wont be auto recovered
    for i in range(len(existing_packs)):
        existing_pack = existing_packs[i]
        if existing_pack not in pack_names:
            new_zip_name = existing_zips[i].replace("_autosave_", "_deprecated_")
            old_zip_path = os.path.join(autosave_dir_path, existing_zips[i])
            new_zip_path = os.path.join(autosave_dir_path, new_zip_name)
            os.rename(old_zip_path, new_zip_path)
            
   
def auto_recover_packs():
    '''Recover all the packs which were marked as "autosave".'''
    if not os.path.exists(autosave_dir_path):
        os.mkdir(autosave_dir_path)
    existing_zips = read_existing_files(autosave_dir_path, suffix=".zip", cull_suffix=False)
    for file_name in existing_zips:
        pack_name = utils.get_string_between_words(file_name, None, ("_autosave_",))
        if pack_name is not False:
            file_path = os.path.join(autosave_dir_path, file_name)
            import_pack(file_path, pack_name)
    
    
def clear_outdated_autosave_packs():
    '''Clear packs which were autosaved 1 day before or autosaved in the last month.'''
    existing_zip_namebodys = read_existing_files(autosave_dir_path, suffix=".zip")
    current_time = utils.get_autosave_time()
    for namebody in existing_zip_namebodys:
        # DDHHMM
        autosave_time_str = utils.get_string_between_words(namebody, ("_deprecated_", ), None)
        if autosave_time_str is not False:
            autosave_time = utils.parse_autosave_time_str(autosave_time_str)
            day_delta = current_time[0] - autosave_time[0]
            # if the user opened blender after a month, the pack will be remained... but who cares?
            if day_delta > 1 or day_delta < 0:
                file_path = os.path.join(autosave_dir_path, "".join((namebody, ".zip")))
                os.remove(file_path)
    

def create_preset(preset_name: str, cpreset: dict):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["order"].append(preset_name)
    pack_meta_cache["tree_types"][preset_name] = cpreset["HN_preset_data"]["tree_type"]
    pack_meta_cache["version"] = version
    write_json(file_path, cpreset)
    write_meta()
    return file_path
    
    
def update_preset(preset_name: str, cpreset: dict):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["tree_types"][preset_name] = cpreset["HN_preset_data"]["tree_type"]
    pack_meta_cache["version"] = version
    write_json(file_path, cpreset)
    write_meta()
    return file_path


def delete_preset(preset_name):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["order"].remove(preset_name)
    del pack_meta_cache["tree_types"][preset_name]
    os.remove(file_path)
    write_meta()
    return file_path
    
    
def clear_preset(pack_name):
    delete_pack(pack_name)
    create_pack(pack_name)


def read_presets(pack_name=""):
    if pack_name == "":
        metadata_path = os.path.join(pack_selected_dir_path, ".metadata.json")
    else:
        metadata_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    metadata = read_json(metadata_path)
    # TODO merge them into a list, just like preset registered in hot_node_props
    preset_names = metadata["order"]
    tree_types = metadata["tree_types"]
    
    return preset_names, tree_types


def load_preset(preset_name, pack_name=""):
    file_name = '.'.join((preset_name, 'json'))
    if pack_name == "":
        file_path = os.path.join(pack_selected_dir_path, file_name)
    else:
        file_path = os.path.join(pack_root_dir_path, pack_name, file_name)
    return read_json(file_path)


def rename_preset(old_name, new_name):
    global pack_meta_cache
    old_file_name = '.'.join((old_name, 'json'))
    old_file_path = os.path.join(pack_selected_dir_path, old_file_name)
    new_file_name = '.'.join((new_name, 'json'))
    new_file_path = os.path.join(pack_selected_dir_path, new_file_name)
    os.rename(old_file_path, new_file_path)
    
    cpreset = load_preset(new_name)
    cpreset["HN_preset_data"]["preset_name"] = new_name
    write_json(new_file_path, cpreset)
    
    idx = pack_meta_cache["order"].index(old_name)
    pack_meta_cache["order"][idx] = new_name
    pack_meta_cache["tree_types"][new_name] = pack_meta_cache["tree_types"].pop(old_name)
    write_meta()
    
    
def reorder_preset_meta(preset_names):
    global pack_meta_cache
    pack_meta_cache["order"] = preset_names
    write_meta()
    
    
def exchange_order_preset_meta(idx1, idx2):
    global pack_meta_cache
    temp = pack_meta_cache["order"][idx2]
    pack_meta_cache["order"][idx2] = pack_meta_cache["order"][idx1]
    pack_meta_cache["order"][idx1] = temp
    write_meta()
    

# CRUD of images
def get_tex_names_in_dir(tex_dir_path):
    try:
        files = os.listdir(tex_dir_path)
    except FileNotFoundError:
        return 'DIR_NOT_FOUND'
    
    tex_names = [file for file in files if file.lower().endswith((".bmp", ".sgi", ".rgb", ".bw", 
                                                                  ".png", ".jpg", ".jpeg", ".jp2",
                                                                  ".j2c", ".tga", ".cin", ".dpx",
                                                                  ".exr", ".hdr", ".tif", ".tiff",
                                                                  ".webp"))]
    return tex_names