import copy
from pathlib import Path

from ...utils import constants
from ..serialization.manager import SerializationManager
from ...utils.file_manager import FileManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .pack import Pack


class PresetMeta():
    """Preset metadata class. Used to store metadata for a preset."""
    def __init__(self, name: str):
        self.name = name
        self.description = ""
        self.tree_type = constants.UNIVERSAL_NODE_TREE_IDNAME  # universal as a placeholder
        self.is_separator = False  # whether this preset performs as a separator in the UI
        
    def __deepcopy__(self, memo):
        new_meta = PresetMeta(self.name)
        new_meta.description = self.description
        new_meta.tree_type = self.tree_type
        new_meta.is_separator = self.is_separator
        new_meta.hot_node_version = constants.HOT_NODE_VERSION
        new_meta.blender_version = constants.BLENDER_VERSION
        return new_meta
    
    def deepcopy(self):
        """Create a deep copy of the PresetMeta instance."""
        return copy.deepcopy(self, memo={})
    
    def serialize(self):
        """Convert the metadata to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "tree_type": self.tree_type,
            "is_separator": self.is_separator,
            "hot_node_version": constants.HOT_NODE_VERSION,
            "blender_version": constants.BLENDER_VERSION,
        }
        
    def deserialize(self, data: dict):
        """Convert a dictionary to a PresetMeta instance."""
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.tree_type = data.get("tree_type", constants.UNIVERSAL_NODE_TREE_IDNAME)
        self.is_separator = data.get("is_separator", False)
        self.hot_node_version = data.get("hot_node_version", constants.HOT_NODE_VERSION)
        self.blender_version = data.get("blender_version", constants.BLENDER_VERSION)


class Preset():
    def __init__(self, name: str, pack: 'Pack'):
        self.sm = SerializationManager()
        self.fm = FileManager()
        
        self.name: str = name
        self.pack: 'Pack' = pack
        
        self.jpreset = {}
        
        self.meta = PresetMeta(name)
        
    def __deepcopy__(self, memo):
        new_preset = Preset(self.name, None)
        new_preset.jpreset = copy.deepcopy(self.jpreset, memo)
        new_preset.meta = copy.deepcopy(self.meta, memo)
        return new_preset
    
    def deepcopy(self):
        """Create a deep copy of the Preset instance."""
        return copy.deepcopy(self, memo={})
    
    @property
    def path(self) -> Path:
        """Get the file path for the preset."""
        return self.fm.packs_dir / self.pack.name / f"{self.name}.json"
        
    def is_env_safe(self):
        return self.path.exists()
        
    def save(self):
        self.jpreset["HN@meta"] = self.meta.serialize()
        self.fm.write_json(self.path, self.jpreset)
        
    def load(self):
        self.jpreset = self.fm.read_json(self.path)
        self.meta.deserialize(self.jpreset.get("HN@meta", {}))
        
    def serialize(self, bl_context, main_tree = None):
        self.jpreset = self.sm.serialize_preset(bl_context, main_tree)
        
    def deserialize(self, bl_context):
        self.load()
        self.sm.deserialize_preset(bl_context, self.jpreset)
        
    def get_ser_context(self):
        """Get the serialization context."""
        return self.sm.ser_context
    
    def get_deser_context(self):
        """Get the deserialization context."""
        return self.sm.deser_context
        
    def rename(self, new_name: str):
        """Rename the preset without checking."""
        self.fm.rename_path_tail(self.path, new_name, suffix=".json")
        self.name = new_name
        
    def overwrite(self, bl_context, main_tree = None):
        """Serialize current selected nodes and write the result."""
        self.serialize(bl_context, main_tree)
        if main_tree is None:
            self.meta.tree_type = bl_context.space_data.edit_tree.bl_idname
        else:
            self.meta.tree_type = main_tree.bl_idname

    def remove(self):
        """Delete the preset file."""
        self.path.unlink(missing_ok=True)
        
    def set_separator(self, is_separator: bool):
        """Set whether this preset is a separator in the UI."""
        self.meta.is_separator = is_separator