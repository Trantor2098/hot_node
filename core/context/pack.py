from .preset import Preset
from ...services.sync import SyncService
from ...utils.file_manager import FileManager
from ...utils import utils
from ...utils.reporter import Reporter
    
class PackMeta:
    """Pack metadata class. Used to store metadata for a pack."""
    def __init__(self):
        self.icon = 'OUTLINER_COLLECTION'
        self.description = ""
        self.ordered_preset_names: list[str] = []
        self.tree_types: list[str] = []
        
    def serialize(self):
        """Convert the metadata to a dictionary."""
        return {
            "icon": self.icon,
            "description": self.description,
            "ordered_preset_names": self.ordered_preset_names,
            "tree_types": self.tree_types,
        }
        
    def deserialize(self, data: dict):
        """Convert a dictionary to a PackMeta instance."""
        self.icon = data.get("icon", 'OUTLINER_COLLECTION')
        self.description = data.get("description", "")
        self.ordered_preset_names = data.get("ordered_preset_names", [])
        self.tree_types = data.get("tree_types", [])

class Pack:
    """Pack class. Includes methods for managing pack / pack_meta / presets in the disk."""
    def __init__(self, name):
        self.fm = FileManager()
        
        self.name = name
        self.presets: dict[str, Preset] = {}
        self.ordered_presets: list[Preset] = []
        
        self.meta = PackMeta()
        
        self.fm.ensure_dir(self.pack_dir)
        if not self.meta_path.exists():
            self.save_pack_meta()
        
    @property
    def pack_dir(self):
        """Get the pack directory."""
        return self.fm.packs_dir / self.name
    
    @property
    def meta_path(self):
        """Get the metadata file path."""
        return self.fm.packs_dir / self.name / ".meta"
        
    def is_env_safe(self):
        if not self.pack_dir.exists() or not self.meta_path.exists():
            return False
        
    def is_preset_file_exist(self, preset: Preset):
        return preset.path.exists()
    
    def is_meta_match_disk(self):
        """Check if the disk presets have changed compared to the metadata."""
        disk_names = set(self.fm.read_dir_file_names(self.pack_dir, ".json", cull_suffix=True))
        meta_names = set(self.meta.ordered_preset_names)
        return disk_names == meta_names
        
    def save_pack_meta(self):
        self.fm.write_json(self.meta_path, self.meta.serialize())
        
    def load_pack_meta(self):
        meta_dict = self.fm.read_json(self.meta_path)
        self.meta.deserialize(meta_dict)
        
    def save_sync_meta(self):
        SyncService.save_sync_meta(self)
        
    def save_metas(self):
        """Save the pack meta and sync meta to disk."""
        self.save_pack_meta()
        SyncService.save_sync_meta(self)
        
    def load(self):
        """Load pack meta and content safely. Will try best to use the meta, and load from disk if meta is not match and fix meta. (Will save meta)"""
        self.load_pack_meta()
        self.load_from_disk_and_try_use_meta()
        # self.save_pack_meta()
            
    def load_from_disk_and_try_use_meta(self):
        """Load pack content from the disk and try to use the meta if it's partly correct. (Wont save meta)"""
        self.presets.clear()
        self.ordered_presets.clear()
        disk_preset_names = self.fm.read_dir_file_names(self.pack_dir, ".json", cull_suffix=True)
        disk_preset_by_name = {}
        # create preset dict with the names from disk
        for preset_name in disk_preset_names:
            preset = Preset(preset_name, self)
            self.presets[preset_name] = preset
            disk_preset_by_name[preset_name] = preset
        # find disk presets in the meta and order them
        for i, preset_name in enumerate(self.meta.ordered_preset_names):
            if disk_preset_by_name.get(preset_name):
                self.ordered_presets.append(disk_preset_by_name.pop(preset_name))
        # add the rest of the disk presets to the ordered presets
        for preset_name, preset in disk_preset_by_name.items():
            self.ordered_presets.append(preset)
        # save the meta with the ordered preset names
        self.meta.ordered_preset_names = [preset.name for preset in self.ordered_presets]
        self.load_presets()
    
    def load_from_meta(self, is_load_presets = False):
        """Load pack from meta (ref, not from disk)."""
        self.presets.clear()
        self.ordered_presets.clear()
        for preset_name in self.meta.ordered_preset_names:
            preset = self.create_preset(preset_name)
            self.add_preset(preset)
        if is_load_presets:
            self.load_presets()
    
    def load_preset(self, preset: Preset):
        if not self.presets.get(preset.name):
            return
        try:
            preset.load()
        except:
            Reporter.report_warning(f"Failed to load preset {preset.name} in pack {self.name}. The preset file may be corrupted.")
            print(f"[Hot Node] Failed to load preset: {preset.name} in pack: {self.name}")
            self.remove_preset(preset)
            self.save_metas()
            
    def load_presets(self):
        for preset in self.ordered_presets:
            self.load_preset(preset)
        
    def get_preset(self, preset_name: str) -> Preset|None:
        """Get a preset by name from the pack."""
        return self.presets.get(preset_name)
    
    def get_preset_by_idx(self, idx: int):
        """Get a preset by index from the ordered presets."""
        return self.ordered_presets[idx]
    
    def get_preset_idx(self, preset: Preset|str):
        """Get the index of a preset in the ordered presets."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        return self.ordered_presets.index(preset)
    
    def has_preset(self, preset: Preset|str):
        """Check if a preset with the given name exists in the pack."""
        if isinstance(preset, str):
            result = self.presets.get(preset)
        else:
            result = preset in self.ordered_presets
        return result
        
    def remove(self):
        """Remove the pack from disk."""
        self.fm.remove_tree(self.pack_dir)
        
    def rename(self, new_name: str):
        """Rename the pack instance and write to the disk."""
        self.fm.rename_path_tail(self.pack_dir, new_name)
        self.name = new_name
        
    def set_meta_icon(self, icon: str = 'COLLECTION'):
        """Set the icon for the pack and write to the disk."""
        self.meta.icon = icon
        
    def set_meta_description(self, description: str):
        """Set the description for the pack meta and write to the disk."""
        self.meta.description = description
        
    def update_meta_tree_types(self):
        """Loop to collect what kinds of tree types are present in the pack."""
        self.meta.tree_types.clear()
        for preset in self.ordered_presets:
            if preset.meta.tree_type not in self.meta.tree_types:
                self.meta.tree_types.append(preset.meta.tree_type)
                
    def add_meta_tree_types(self, tree_type: str):
        """Add a tree type to the pack meta."""
        if tree_type not in self.meta.tree_types:
            self.meta.tree_types.append(tree_type)
        
    def create_preset(self, preset_name: str):
        preset = Preset(preset_name, self)
        return preset
    
    def create_presets(self, preset_names: list[str]):
        presets = []
        for preset_name in preset_names:
            preset = Preset(preset_name, self)
            presets.append(preset)
        return presets
    
    def add_preset(self, preset: Preset, dst_idx: int|None = None):
        """Add a preset instance to the pack, just ref."""
        preset.pack = self
        self.presets[preset.name] = preset
        if dst_idx is None:
            self.ordered_presets.append(preset)
            self.meta.ordered_preset_names.append(preset.name)
        else:
            self.ordered_presets.insert(dst_idx, preset)
            self.meta.ordered_preset_names.insert(dst_idx, preset.name)
        self.add_meta_tree_types(preset.meta.tree_type)
            
    def add_presets(self, presets: list[Preset]):
        for preset in presets:
            preset.pack = self
            self.presets[preset.name] = preset
            self.ordered_presets.append(preset)
            self.meta.ordered_preset_names.append(preset.name)
        self.update_meta_tree_types()
        
    def save_preset(self, preset: Preset|str):
        """Save the preset to disk."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        preset.save()
        
    def save_presets(self, presets: list[Preset]|list[str]):
        """Save a list of presets to disk."""
        if not presets:
            return
        if isinstance(presets[0], str):
            for preset_name in presets:
                preset = self.presets[preset_name]
                preset.save()
        else:
            for preset in presets:
                preset.save()
                
    def duplicate_preset(self, preset: Preset|str):
        """Duplicate a preset in the pack."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        new_name = utils.ensure_unique_name_for_item(preset.name, self.ordered_presets)
        new_preset = preset.deepcopy()
        new_preset.name = new_name
        self.add_preset(new_preset)
        self.save_preset(new_preset)
        return new_preset
            
    def add_preset_nodes_to_tree(self, bl_context, preset: Preset):
        preset.deserialize(bl_context)
            
    def overwrite_preset(self, preset: Preset|str, bl_context, main_tree = None):
        """Serialize current selected nodes and write the result to disk."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        preset.overwrite(bl_context, main_tree)
        preset.save()
        self.update_meta_tree_types()
    
    def rename_preset(self, preset: Preset|str, new_name: str):
        """Rename the preset in the pack and the disk."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        self.presets.pop(preset.name)
        self.presets[new_name] = preset
        preset.rename(new_name)
        idx = self.ordered_presets.index(preset)
        self.ordered_presets[idx] = preset
        self.meta.ordered_preset_names[idx] = new_name
            
    def remove_preset(self, preset: Preset|str|int):
        """Remove a preset from the pack and the disk."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        elif isinstance(preset, int):
            preset = self.ordered_presets[preset]
        self.remove_preset_from_pack(preset)
        preset.remove()
        self.update_meta_tree_types()
        
    def remove_preset_from_pack(self, preset: Preset|str|int):
        """Remove a preset from the pack, keep it on disk."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        elif isinstance(preset, int):
            preset = self.ordered_presets[preset]
        self.presets.pop(preset.name)
        idx = self.ordered_presets.index(preset)
        self.ordered_presets.pop(idx)
        self.meta.ordered_preset_names.pop(idx)
        self.update_meta_tree_types()
        
    def clear_presets(self):
        """Remove all presets from the pack and the disk."""
        for preset in self.ordered_presets:
            preset.remove()
        self.presets.clear()
        self.ordered_presets.clear()
        self.meta.ordered_preset_names = []
        self.update_meta_tree_types()
        
    def order_preset(self, src_idx: int, dst_idx: int):
        if src_idx == dst_idx:
            return
        preset = self.ordered_presets.pop(src_idx)
        self.ordered_presets.insert(dst_idx, preset)
        self.meta.ordered_preset_names = [preset.name for preset in self.ordered_presets]
        
    def try_match_order(self, preset_names: list[str]):
        """Try to match the order of presets with the given names."""
        if not preset_names:
            return
        new_ordered_presets = []
        used_names = set()
        for preset_name in preset_names:
            preset = self.presets.get(preset_name)
            if preset:
                new_ordered_presets.append(preset)
                used_names.add(preset_name)
        for preset in self.ordered_presets:
            if preset.name not in used_names:
                new_ordered_presets.append(preset)
        self.ordered_presets = new_ordered_presets
        self.meta.ordered_preset_names = [preset.name for preset in self.ordered_presets]
        
    def set_preset_separator(self, preset: Preset|str, is_separator: bool|None = None):
        """Set whether the preset is a separator in the UI. if is_separator is None, it will check if the preset name is only dash and set automatically."""
        if isinstance(preset, str):
            preset = self.presets[preset]
        if is_separator is None:
            is_separator = utils.is_str_only_dash(preset.name)
        preset.set_separator(is_separator)