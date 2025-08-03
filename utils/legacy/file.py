import os, shutil, json, zipfile, tempfile, time

from .. import utils, constants


version = constants.HOT_NODE_VERSION
blender = constants.BLENDER_VERSION

# TODO Remove dependency on caches
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


def ensure_dir_existing(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)



def check_pack_existing():
    return os.path.exists(pack_selected_path)


def check_preset_existing(preset_name):
    file_name = '.'.join((preset_name, 'json'))
    file_path = os.path.join(pack_selected_path, file_name)
    return os.path.exists(file_path)


def exist_path(path):
    return os.path.exists(path)


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


def get_preset_file_path(pack_name, preset_name):
    file_name = "".join((preset_name, ".json"))
    return os.path.join(get_pack_path(pack_name), file_name)
    
    
def get_root_meta_path():
    os.path.join(pack_root_dir_path, ".metadata.json")
    
    
def get_pack_mtime(pack_name):
    pack_meta_path = os.path.join(pack_root_dir_path, pack_name, ".metadata.json")
    return os.path.getmtime(pack_meta_path)


# Get & Set Meta Data
def create_empty_pack_meta():
    pack_meta = {}
    pack_meta["order"] = []
    pack_meta["tree_types"] = {}
    pack_meta["pack_types"] = []
    pack_meta["icon"] = 'OUTLINER_COLLECTION'
    pack_meta["use_shortcut"] = False
    pack_meta["version"] = version
    return pack_meta

# Read Existing Files
def read_existing_file_names(dir_path, suffix=".zip", cull_suffix=True):
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
    return new_pack_dir_path

            
   
def auto_recover_packs():
    '''Recover all the packs which were marked as "autosave".'''
    ensure_dir_existing(autosave_dir_path)
    existing_zips = read_existing_file_names(autosave_dir_path, suffix=".zip", cull_suffix=False)
    for file_name in existing_zips:
        pack_name = utils.get_string_between_words(file_name, None, ("_autosave_",))
        if pack_name is not False:
            file_path = os.path.join(autosave_dir_path, file_name)
            import_pack(file_path, pack_name)
    
    
def clear_outdated_autosave_packs():
    '''Clear packs which were autosaved 1 day before or autosaved in the last month.'''
    ensure_dir_existing(autosave_dir_path)
    existing_zip_namebodys = read_existing_file_names(autosave_dir_path, suffix=".zip")
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


# CRUD of images
def get_tex_names_in_dir(tex_dir_path):
    if not os.path.exists(tex_dir_path):
        return 'DIR_NOT_FOUND'
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