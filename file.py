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

from . import utils, props_py, constants
from . __init__ import bl_info


version = bl_info["version"]
blender = bl_info["blender"]

# Paths
addon_dir_path = os.path.dirname(__file__)
temp_dir_path = tempfile.gettempdir()
autosave_dir_path = os.path.join(temp_dir_path, "hot_node_autosave")
history_dir_path = os.path.join(addon_dir_path, "hot_node_history")
pack_root_dir_path = os.path.join(addon_dir_path, "preset_packs")
pack_selected_path = os.path.join(pack_root_dir_path, "")
pack_selected_meta_path = ""
root_meta_path = os.path.join(pack_root_dir_path, ".metadata.json")

# Metas
last_mtime = 0.0
pack_selected_meta = {}
root_meta_cache = {"pack_selected": "", 
                   "last_mtime": 0.0}


# Sync & Check
def ensure_pack_root():
    '''Read root meta to global root_meta_cache, recover autosaved files when there is no pack root dir (mostly happen when updating add-on)'''
    global root_meta_cache
    if not os.path.exists(pack_root_dir_path):
        os.mkdir(pack_root_dir_path)
        auto_recover_packs()
        pack_names = load_packs()
        if len(pack_names) == 0:
            select_pack(None)
        else:
            select_pack(props_py.gl_packs[pack_names[0]])
    elif not os.path.exists(root_meta_path):
        pack_names = load_packs()
        if len(pack_names) == 0:
            select_pack(None)
        else:
            select_pack(props_py.gl_packs[pack_names[0]])
            
            
def ensure_dir_existing(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        
        
def check_sync():
    global last_mtime
    mtime_data = get_mtime_data_and_refresh_root_meta_cache()
    if mtime_data != last_mtime:
        last_mtime = mtime_data
        return False
    return True


def check_pack_existing():
    return os.path.exists(pack_selected_path)


def check_preset_existing(preset_name):
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_path, file_name)
    return os.path.exists(file_path)


# Get File Info & Path
def get_pack_selected_meta_path():
    return os.path.join(pack_selected_path, ".metadata.json")
    
    
def get_pack_meta_path(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    return pack_meta_path


def get_pack_path(pack_name):
    return os.path.join(pack_root_dir_path, pack_name)


def get_preset_path(preset_name):
    file_name = "".join((preset_name, ".json"))
    return os.path.join(pack_selected_path, file_name)
    
    
def get_root_meta_path():
    os.path.join(pack_root_dir_path, ".metadata.json")
    
    
def get_pack_mtime(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    return os.path.getmtime(pack_meta_path)


# Get & Set Meta Data
def get_mtime_data_and_refresh_root_meta_cache():
    global root_meta_cache
    root_meta_cache = read_root_meta()
    mtime_data = root_meta_cache.get("last_mtime", 0.0)
    return mtime_data


def update_root_meta_cache_mtime():
    global root_meta_cache, last_mtime
    last_mtime = time.time()
    root_meta_cache["last_mtime"] = last_mtime
    
    
def update_mtime_data():
    global root_meta_cache, last_mtime
    root_meta_cache = read_root_meta()
    last_mtime = time.time()
    root_meta_cache["last_mtime"] = last_mtime
    write_root_meta()
    
    
def update_pack_types(pack_name: str, write_meta=True):
    pack_meta: dict = read_pack_meta(pack_name)
    pack_types = []
    tree_types = list(pack_meta["tree_types"].values())
    for tree_type in constants.tree_type_id_names:
        if tree_type in tree_types and tree_type not in pack_types:
            pack_types.append(tree_type)
    pack_meta["pack_types"] = pack_types
    if write_meta:
        pack_path = get_pack_path(pack_name)
        write_pack_meta(pack_path, pack_meta)
    return pack_meta


def update_pack_types_of_meta(pack_meta: dict):
    pack_types = []
    tree_types = list(pack_meta["tree_types"].values())
    for tree_type in constants.tree_type_id_names:
        if tree_type in tree_types and tree_type not in pack_types:
            pack_types.append(tree_type)
    pack_meta["pack_types"] = pack_types
    return pack_meta


def get_pack_types(pack_name):
    pack_meta: dict = read_pack_meta(pack_name)
    pack_types = pack_meta.get("pack_types", None)
    if pack_types is None:
        pack_meta = update_pack_types(pack_name)
        pack_types = pack_meta["pack_types"]
    return pack_types
    
    
# CRUD of Json
def write_json(file_path: str, data: dict, indent: int|str|None=1):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=indent)


def read_json(file_path) -> dict:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
    
def write_metas(pack_selected_meta):
    update_root_meta_cache_mtime()
    write_json(pack_selected_meta_path, pack_selected_meta, 1)
    write_json(root_meta_path, root_meta_cache, 1)
    
    
def write_pack_meta(pack_path: str, meta_data: dict):
    meta_path = os.path.join(pack_path, ".metadata.json")
    write_json(meta_path, meta_data, 1)
    
    
def write_root_meta(update_mtime=False):
    if update_mtime:
        update_root_meta_cache_mtime()
    write_json(root_meta_path, root_meta_cache, 1)
    
    
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
    if "tree_types" not in keys:
        return 'INVALID_META'
    return metadata


def read_translation_dict():
    return read_json(os.path.join(addon_dir_path, "translation.json"))


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
    ensure_dir_existing(history_dir_path)
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
            
            
def try_del_paths(*pathss):
    for paths in pathss:
        for path in paths:
            if os.path.exists(path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
    

# CRUD of Pack and Preset
def create_pack(pack_name):
    global root_meta_cache
    global pack_selected_path
    global pack_selected_meta_path
    pack_selected_path = os.path.join(pack_root_dir_path, pack_name)
    pack_selected_meta_path = os.path.join(pack_selected_path, ".metadata.json")
    # create pack metadata
    root_meta_cache["pack_selected"] = pack_name
    pack_selected_meta = {}
    pack_selected_meta["order"] = []
    pack_selected_meta["tree_types"] = {}
    pack_selected_meta["version"] = version
    pack_selected_meta["pack_types"] = []
    os.mkdir(pack_selected_path)
    write_metas(pack_selected_meta)
    # reload packs to get right order of packs
    load_packs()
    return pack_selected_path


def delete_pack(pack_name):
    pack_dir_path = os.path.join(pack_root_dir_path, pack_name)
    shutil.rmtree(pack_dir_path)
    update_mtime_data()
    return pack_dir_path


# not used
def clear_pack(pack_names):
    for pack_name in pack_names:
        delete_pack(pack_name)


def rename_pack(old_pack_name, new_pack_name):
    old_path = os.path.join(pack_root_dir_path, old_pack_name)
    new_path = os.path.join(pack_root_dir_path, new_pack_name)
    os.rename(old_path, new_path)
    # reload packs to get the right order of packs
    load_packs()
    update_mtime_data()
    select_pack(props_py.gl_packs[new_pack_name])


def load_packs():
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
    global root_meta_cache
    global pack_selected_meta_path
    global pack_selected_path
    if pack is None:
        # pack_selected_meta = {}
        # pack_selected_meta["order"] = []
        # pack_selected_meta["tree_types"] = {}
        # pack_selected_meta["version"] = version
        # pack_selected_meta_path = ""
        root_meta_cache["pack_selected"] = ""
    else:
        pack_selected_path = os.path.join(pack_root_dir_path, pack.name)
        pack_selected_meta_path = os.path.join(pack_selected_path, ".metadata.json")
        root_meta_cache["pack_selected"] = pack.name
    props_py.gl_pack_selected = pack
    write_root_meta()
    
    
def import_pack(from_file_path: str, new_pack_name: str):
    '''Import pack.zip into add-on, return the imported pack path.'''
    global pack_selected_path
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
    return new_pack_dir_path
             

def export_selected_pack(dst_file_path, unique_name=True):
    global pack_selected_path
    if unique_name:
        dst_dir_path = os.path.dirname(dst_file_path)
        existing_zip_namebodys = read_existing_files(dst_dir_path, suffix=".zip")
        pack_name = props_py.gl_pack_selected.name
        ensured_pack_name = utils.ensure_unique_name(pack_name, -1, existing_zip_namebodys)
        dst_file_path = os.path.join(dst_dir_path, ".".join((ensured_pack_name, "zip")))
    zip = zipfile.ZipFile(dst_file_path, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(pack_selected_path):
        relative_root = '' if root == pack_selected_path else root.replace(pack_selected_path, '') + os.sep
        for filename in files:
            zip.write(os.path.join(root, filename), relative_root + filename)
    zip.close()
    return dst_file_path
    
    
def export_packs(pack_names, dst_dir_path):
    # ensure we are getting a dir path, not a file path. if it's a file path, get the dir path of it using dirname()
    dst_dir_path = os.path.dirname(dst_dir_path)
    existing_zip_namebodys = read_existing_files(dst_dir_path, suffix=".zip")
            
    for pack_name in pack_names:
        pack_dir_path = os.path.join(pack_root_dir_path, pack_name)
        
        ensured_pack_name = utils.ensure_unique_name(pack_name, -1, existing_zip_namebodys)
            
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
    pack_names = load_packs()
    
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
    pack_selected_meta = read_pack_meta()
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_path, file_name)
    tree_type = cpreset["HN_preset_data"]["tree_type"]
    pack_selected_meta["order"].append(preset_name)
    pack_selected_meta["tree_types"][preset_name] = tree_type
    pack_selected_meta["version"] = version
    pack_selected_meta = update_pack_types_of_meta(pack_selected_meta)
    write_json(file_path, cpreset)
    write_metas(pack_selected_meta)
    return file_path
    
    
def update_preset(preset_name: str, cpreset: dict):
    pack_selected_meta = read_pack_meta()
    read_pack_meta()
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_path, file_name)
    pack_selected_meta["tree_types"][preset_name] = cpreset["HN_preset_data"]["tree_type"]
    pack_selected_meta["version"] = version
    pack_selected_meta = update_pack_types_of_meta(pack_selected_meta)
    write_json(file_path, cpreset)
    write_metas(pack_selected_meta)
    return file_path


def delete_preset(preset_name):
    pack_selected_meta = read_pack_meta()
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_path, file_name)
    pack_selected_meta["order"].remove(preset_name)
    del pack_selected_meta["tree_types"][preset_name]
    pack_selected_meta = update_pack_types_of_meta(pack_selected_meta)
    os.remove(file_path)
    write_metas(pack_selected_meta)
    return file_path
    
    
def clear_preset(pack_name):
    delete_pack(pack_name)
    create_pack(pack_name)


def read_presets(pack_name=""):
    '''Read presets via pack meta'''
    if pack_name == "":
        metadata_path = os.path.join(pack_selected_path, ".metadata.json")
    else:
        metadata_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    metadata = read_json(metadata_path)
    # TODO merge them into a list, just like preset registered in hot_node_props
    preset_names = metadata["order"]
    tree_types = metadata["tree_types"]
    
    return preset_names, tree_types


def refresh_pack_meta(pack_name):
    '''Read presets by listing directory and update the pack meta'''
    old_pack_meta = read_pack_meta()
    old_order = old_pack_meta["order"]
    pack_path = get_pack_path(pack_name)
    preset_names = read_existing_files(pack_path, suffix=".json", cull_suffix=True)
    filtered_preset_names = []
    if ".metadata" in preset_names:
        preset_names.remove(".metadata")
    # order the new preset names by the order before
    for i in range(len(old_order)):
        pack_name = old_order[i]
        if pack_name in preset_names:
            preset_names.remove(pack_name)
            filtered_preset_names.append(pack_name)
    filtered_preset_names.extend(preset_names)
    
    tree_types = {}
    for preset_name in filtered_preset_names:
        preset = load_preset(preset_name)
        tree_types[preset_name] = preset["HN_preset_data"]["tree_type"]
        
    pack_meta = {}
    pack_meta["order"] = filtered_preset_names
    pack_meta["tree_types"] = tree_types
    pack_meta["version"] = version
    for preset_name in filtered_preset_names:
        preset = load_preset(preset_name)
        pack_meta["tree_types"][preset_name] = preset["HN_preset_data"]["tree_type"]
        
    write_pack_meta(pack_path, pack_meta)
    return filtered_preset_names, pack_meta


def load_preset(preset_name, pack_name=""):
    file_name = '.'.join((preset_name, 'json'))
    if pack_name == "":
        file_path = os.path.join(pack_selected_path, file_name)
    else:
        file_path = os.path.join(pack_root_dir_path, pack_name, file_name)
    return read_json(file_path)


def rename_preset(old_name, new_name):
    pack_selected_meta = read_pack_meta()
    old_file_name = '.'.join((old_name, 'json'))
    old_file_path = os.path.join(pack_selected_path, old_file_name)
    new_file_name = '.'.join((new_name, 'json'))
    new_file_path = os.path.join(pack_selected_path, new_file_name)
    os.rename(old_file_path, new_file_path)
    
    cpreset = load_preset(new_name)
    cpreset["HN_preset_data"]["preset_name"] = new_name
    write_json(new_file_path, cpreset)
    
    idx = pack_selected_meta["order"].index(old_name)
    pack_selected_meta["order"][idx] = new_name
    pack_selected_meta["tree_types"][new_name] = pack_selected_meta["tree_types"].pop(old_name)
    write_metas(pack_selected_meta)
    
    
def reorder_preset_meta(preset_names):
    pack_selected_meta = read_pack_meta()
    pack_selected_meta["order"] = preset_names
    write_metas(pack_selected_meta)
    
    
def exchange_order_preset_meta(idx1, idx2):
    pack_selected_meta = read_pack_meta()
    temp = pack_selected_meta["order"][idx2]
    pack_selected_meta["order"][idx2] = pack_selected_meta["order"][idx1]
    pack_selected_meta["order"][idx1] = temp
    write_metas(pack_selected_meta)
    

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


# Initialize & finalize files when opening & closing blender
def init():
    global last_mtime
    load_packs()
    ensure_pack_root()
    ensure_dir_existing(history_dir_path)
    autosave_packs()
    last_mtime = get_mtime_data_and_refresh_root_meta_cache()
    pack_selected_name = root_meta_cache["pack_selected"]
    props_py.gl_pack_selected = props_py.gl_packs.get(pack_selected_name, None)
    
    
def finalize(remove_his_dir=True):
    autosave_packs()
    clear_outdated_autosave_packs()