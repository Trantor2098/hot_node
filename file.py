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

import os, shutil, json, zipfile, tempfile

from . version_control import version
from . import utils

addon_dir_path = os.path.dirname(__file__)
temp_dir_path = os.path.join(tempfile.gettempdir(), "hot_node_autosave")
pack_root_dir_path = os.path.join(addon_dir_path, "preset_packs")
pack_selected_dir_path = os.path.join(pack_root_dir_path, "")
pack_meta_path = ""
root_meta_path = os.path.join(pack_root_dir_path, ".metadata.json")

pack_meta_cache = {}
root_meta_cache = {}

pack_meta_size_cache = 0
root_meta_size_cache = 0

pack_meta_mtime_cache = 0
root_meta_mtime_cache = 0


# Initialize & finalize files when opening & closing blender
def init():
    refresh_pack_root()
    autosave_packs()
    
    
def finalize():
    autosave_packs()
    clear_outdated_autosave_packs()

# Sync Check
def refresh_pack_root():
    '''Read root meta to global root_meta_cache, recover autosaved files when there is no pack root dir (mostly happen when updating add-on)'''
    global root_meta_cache
    if not os.path.exists(pack_root_dir_path):
        os.mkdir(pack_root_dir_path)
        auto_recover_packs()
        packs = read_packs()
        if len(packs) == 0:
            select_pack("")
        else:
            select_pack(packs[0])
    elif not os.path.exists(root_meta_path):
        packs = read_packs()
        if len(packs) == 0:
            select_pack("")
        else:
            select_pack(packs[0])
    else:
        root_meta_cache = read_root_meta()
        
        
def check_sync():
    # if there is no pack, pass the check and wait for creating operation
    if pack_meta_path == "":
        packs = read_packs()
        if len(packs) == 0:
            return True
        else:
            return False
    if not os.path.exists(pack_meta_path):
        return False
    if pack_meta_cache != read_pack_meta():
        return False
    return True


def check_sync_by_mtime():
    # if no pack, pass the check and dont sync
    if pack_meta_path == "":
        packs = read_packs()
        if len(packs) == 0:
            return True
        else:
            return False
    
    global pack_meta_mtime_cache
    global root_meta_mtime_cache
    current_root_meta_mtime = os.path.getmtime(root_meta_path)
    if root_meta_mtime_cache != current_root_meta_mtime:
        root_meta_mtime_cache = current_root_meta_mtime
        return False
    if not os.path.exists(pack_meta_path):
        return False
    current_pack_meta_mtime = os.path.getmtime(pack_meta_path)
    if pack_meta_mtime_cache != current_pack_meta_mtime:
        pack_meta_mtime_cache = current_pack_meta_mtime
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


# Get Path
def get_pack_meta_path():
    os.path.join(pack_selected_dir_path, ".metadata.json")
    
    
def get_root_meta_path():
    os.path.join(pack_root_dir_path, ".metadata.json")
        

# CRUD of Json
def write_json(file_path: str, data: dict):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=1)


def read_json(file_path) -> dict:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
    
def write_pack_meta():
    write_json(pack_meta_path, pack_meta_cache)
    global pack_meta_mtime_cache
    pack_meta_mtime_cache = os.path.getmtime(pack_meta_path)
    
    
def write_root_meta():
    write_json(root_meta_path, root_meta_cache)
    global root_meta_mtime_cache
    root_meta_mtime_cache = os.path.getmtime(root_meta_path)
    
    
def write_meta():
    write_json(root_meta_path, root_meta_cache)
    write_json(pack_meta_path, pack_meta_cache)
    global root_meta_mtime_cache
    root_meta_mtime_cache = os.path.getmtime(root_meta_path)
    global pack_meta_mtime_cache
    pack_meta_mtime_cache = os.path.getmtime(pack_meta_path)
    
    
def read_pack_meta():
    if os.path.exists(pack_meta_path):
        return read_json(pack_meta_path)

    
def read_root_meta():
    if os.path.exists(root_meta_path):
        return read_json(root_meta_path)
    
    
def read_meta():
    if os.path.exists(root_meta_path) and os.path.exists(pack_meta_path):
        return read_json(root_meta_path), read_json(pack_meta_path)
    
    
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


# CRUD of Pack and Preset
def create_pack(pack_name):
    global root_meta_cache
    global pack_meta_cache
    global pack_selected_dir_path
    global pack_meta_path
    pack_selected_dir_path = os.path.join(pack_root_dir_path, pack_name)
    pack_meta_path = os.path.join(pack_selected_dir_path, ".metadata.json")
    # create pack metadata
    root_meta_cache["pack_selected"] = pack_name
    pack_meta_cache = {}
    pack_meta_cache["order"] = []
    pack_meta_cache["tree_types"] = {}
    pack_meta_cache["version"] = version
    os.mkdir(pack_selected_dir_path)
    write_meta()


def delete_pack(pack_name):
    global pack_meta_cache
    pack_dir_path = os.path.join(pack_root_dir_path, pack_name)
    shutil.rmtree(pack_dir_path)


def clear_pack(pack_names):
    for pack_name in pack_names:
        delete_pack(pack_name)


def rename_pack(old_pack_name, new_pack_name):
    old_path = os.path.join(pack_root_dir_path, old_pack_name)
    new_path = os.path.join(pack_root_dir_path, new_pack_name)
    os.rename(old_path, new_path)
    select_pack(new_pack_name)


def read_packs():
    if not os.path.exists(pack_root_dir_path):
        refresh_pack_root()
    pack_names = os.listdir(pack_root_dir_path)
    if ".metadata.json" in pack_names:
        pack_names.remove(".metadata.json")
    return pack_names


def select_pack(pack_name):
    global pack_meta_cache
    global root_meta_cache
    global pack_meta_path
    global pack_selected_dir_path
    if pack_name != "":
        pack_selected_dir_path = os.path.join(pack_root_dir_path, pack_name)
        pack_meta_path = os.path.join(pack_selected_dir_path, ".metadata.json")
        pack_meta_cache = read_pack_meta()
    else:
        pack_meta_cache = {}
        pack_meta_path = ""
    root_meta_cache["pack_selected"] = pack_name
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
    
    
def export_packs(packs, dst_dir_path):
    existing_zip_namebodys = read_existing_files(dst_dir_path, suffix=".zip")
            
    for pack in packs:
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
    if not os.path.exists(temp_dir_path):
        os.mkdir(temp_dir_path)
    packs = read_packs()
    
    existing_zips = read_existing_files(temp_dir_path, suffix=".zip", cull_suffix=False)
    existing_packs = []
    for i in range(len(existing_zips)):
        file_name = existing_zips[i]
        existing_packs.append(utils.get_string_between_words(file_name, None, ("_autosave_", "_deprecated_")))
            
    for pack in packs:
        pack_dir_path = os.path.join(pack_root_dir_path, pack)
        
        # remove the previous autosaved file with the same name
        if pack in existing_packs:
            zip_idx = existing_packs.index(pack)
            ealry_zip_path = os.path.join(temp_dir_path, existing_zips[zip_idx])
            os.remove(ealry_zip_path)
            
        autosave_time_str = utils.get_autosave_time_str()
        ensured_pack_name = "".join((pack, "_autosave_", autosave_time_str))
            
        dst_file_name = ".".join((ensured_pack_name, "zip"))
        dst_file_path = os.path.join(temp_dir_path, dst_file_name)
        file_name = zipfile.ZipFile(dst_file_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(pack_dir_path):
            relative_root = '' if root == pack_dir_path else root.replace(pack_dir_path, '') + os.sep
            for filename in files:
                file_name.write(os.path.join(root, filename), relative_root + filename)
        file_name.close()
    
    # if the autosaved pack no longer exists in the current packs, mark them as deprecated so that if user update the add-on these packs wont be auto recovered
    for i in range(len(existing_packs)):
        existing_pack = existing_packs[i]
        if existing_pack not in packs:
            new_zip_name = existing_zips[i].replace("_autosave_", "_deprecated_")
            old_zip_path = os.path.join(temp_dir_path, existing_zips[i])
            new_zip_path = os.path.join(temp_dir_path, new_zip_name)
            os.rename(old_zip_path, new_zip_path)
            
   
def auto_recover_packs():
    '''Recover all the packs which were marked as "autosave".'''
    if not os.path.exists(temp_dir_path):
        os.mkdir(temp_dir_path)
    existing_zips = read_existing_files(temp_dir_path, suffix=".zip", cull_suffix=False)
    for file_name in existing_zips:
        pack_name = utils.get_string_between_words(file_name, None, ("_autosave_",))
        if pack_name is not False:
            file_path = os.path.join(temp_dir_path, file_name)
            import_pack(file_path, pack_name)
    
    
def clear_outdated_autosave_packs():
    '''Clear packs which were autosaved 1 day before or autosaved in the last month.'''
    existing_zip_namebodys = read_existing_files(temp_dir_path, suffix=".zip")
    current_time = utils.get_autosave_time()
    for namebody in existing_zip_namebodys:
        # DDHHMM
        autosave_time_str = utils.get_string_between_words(namebody, ("_deprecated_", ), None)
        if autosave_time_str is not False:
            autosave_time = utils.parse_autosave_time_str(autosave_time_str)
            day_delta = current_time[0] - autosave_time[0]
            # if the user opened blender after a month, the pack will be remained... but who cares?
            if day_delta > 1 or day_delta < 0:
                file_path = os.path.join(temp_dir_path, "".join((namebody, ".zip")))
                os.remove(file_path)
    

def create_preset(preset_name: str, cpreset: dict):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["order"].append(preset_name)
    pack_meta_cache["tree_types"][preset_name] = cpreset["HN_preset_data"]["tree_type"]
    pack_meta_cache["version"] = version
    write_json(file_path, cpreset)
    write_pack_meta()
    
    
def update_preset(preset_name: str, cpreset: dict):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["tree_types"][preset_name] = cpreset["HN_preset_data"]["tree_type"]
    pack_meta_cache["version"] = version
    write_json(file_path, cpreset)
    write_pack_meta()


def delete_preset(preset_name):
    global pack_meta_cache
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
    pack_meta_cache["order"].remove(preset_name)
    del pack_meta_cache["tree_types"][preset_name]
    os.remove(file_path)
    write_pack_meta()
    
    
def clear_preset(pack_name):
    delete_pack(pack_name)
    create_pack(pack_name)


def read_preset_infos():
    metadata_path = os.path.join(pack_selected_dir_path, ".metadata.json")
    metadata = read_json(metadata_path)
    preset_names = metadata["order"]
    tree_types = metadata["tree_types"]
    
    return preset_names, tree_types


def load_preset(preset_name):
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_dir_path, file_name)
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
    write_pack_meta()
    
    
def reorder_preset_meta(preset_names):
    global pack_meta_cache
    pack_meta_cache["order"] = preset_names
    write_pack_meta()
    
    
def exchange_order_preset_meta(idx1, idx2):
    global pack_meta_cache
    temp = pack_meta_cache["order"][idx2]
    pack_meta_cache["order"][idx2] = pack_meta_cache["order"][idx1]
    pack_meta_cache["order"][idx1] = temp
    write_pack_meta()
    

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