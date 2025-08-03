# import time

import bpy

from .serialize.adapter import Adapter as SerAdapter
from .serialize.serializer import Serializer
from .deserialize.adapter import Adapter as DeserAdapter
from .deserialize.deserializer import Deserializer
from ...utils.constants import BLENDER_VERSION, HOT_NODE_PKG
from ...utils import utils

class SerializationManager:
    """Singleton class to manage serialization and deserialization of presets."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            
            self.ser_adapter = SerAdapter(BLENDER_VERSION)
            self.deser_adapter = DeserAdapter(BLENDER_VERSION)
            self.ser_stgs = self.ser_adapter.get_stgs()
            self.deser_stgs = self.deser_adapter.get_stgs()
            self.serializer = Serializer(self)
            self.deserializer = Deserializer(self)

            self.ser_context = self.serializer.context
            self.deser_context = self.deserializer.context
    
    def init_ser_context(self, bl_context: bpy.types.Context, main_tree: bpy.types.NodeTree|None = None):
        context = self.ser_context
        context.bl_context = bl_context
        context.user_prefs = utils.get_user_prefs(bl_context)
        context.space_data = bpy.context.space_data
        context.node_groups = bpy.data.node_groups
        context.edit_tree = bl_context.space_data.edit_tree if hasattr(bl_context.space_data, "edit_tree") else None
        if main_tree is None:
            context.main_tree = context.edit_tree
        else:
            context.main_tree = main_tree
        context.preset_name_when_only_one_node = None
        context.prev_obj = None
        
    def init_deser_context(self, bl_context: bpy.types.Context, jpreset: dict, main_tree: bpy.types.NodeTree|None = None):
        jdata: dict = jpreset.get("HN@data", {})
        
        context = self.deser_context
        context.init_on_deserializing_preset()
        context.bl_context = bl_context
        context.user_prefs = utils.get_user_prefs(bl_context)
        context.space_data = bl_context.space_data
        context.node_groups = bpy.data.node_groups
        context.edit_tree = bl_context.space_data.edit_tree if hasattr(bl_context.space_data, "edit_tree") else None
        if main_tree is None:
            context.main_tree = context.edit_tree
        else:
            context.main_tree = main_tree

        context.jpreset = jpreset
        context.jdata = jdata
        context.jnode_trees = jpreset.get("HN@node_trees", {})
        context.jmain_tree = context.jnode_trees.get("HN@main_tree", {})
        
        # use get to avoid KeyError if the key is not present when preset version is old
        context.data_node_center = jdata.get("node_center", [0.0, 0.0])
        context.data_compatible_mode = jdata.get("compatible_mode", True)
        
        context.existing_node_group_names = list(context.node_groups.keys())
        context.image_names_in_dir = []
    
    def serialize_preset(self, bl_context: bpy.types.Context, main_tree: bpy.types.NodeTree|None = None) -> dict:
        """main_tree: the dst node tree to get nodes from, if None, use the current edit tree."""
        self.init_ser_context(bl_context, main_tree)
        return self.serializer.specify_serialize(self.ser_context.main_tree, None, self.ser_stgs.preset)

    def serialize_node_tree(self, bl_context: bpy.types.Context, node_tree: bpy.types.NodeTree) -> dict:
        """Serialize the entire node tree."""
        self.init_ser_context(bl_context)
        self.ser_context.node_tree = node_tree
        return self.serializer.specify_serialize(node_tree, None, self.ser_stgs.node_tree)

    def serialize_interface(self, bl_context: bpy.types.Context, node_tree: bpy.types.NodeTree) -> dict:
        """Serialize the interface of the main tree."""
        self.init_ser_context(bl_context)
        self.ser_context.node_tree = node_tree
        return self.serializer.specify_serialize(node_tree.interface, None, self.ser_stgs.interface)

    def deserialize_preset(self, bl_context: bpy.types.Context, jpreset: dict, main_tree: bpy.types.NodeTree|None = None):
        """main_tree: the dst node tree to deserialize into, if None, use the current edit tree."""
        if not jpreset:
            return
        # start_time = time.time()
        self.init_deser_context(bl_context, jpreset, main_tree)
        self.deserializer.specify_deserialize(self.deser_context.main_tree, jpreset, self.deser_stgs.preset)
        # end_time = time.time()
        # print(f"[HOT NODE DEV] Deserialize preset took {end_time - start_time:.4f} seconds")