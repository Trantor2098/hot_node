# import time

import bpy

from .serialize.adapter import Adapter as SerAdapter
from .serialize.serializer import Serializer
from .deserialize.adapter import Adapter as DeserAdapter
from .deserialize.deserializer import Deserializer
from ...utils.constants import BLENDER_VERSION
# For API usage: BLENDER_VERSION = list(bpy.app.version)

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
            
    def reset(self):
        """Reset the serialization manager to its initial state."""
        self._initialized = False
        self.__class__._instance = None
    
    def serialize_preset(self, bl_context: bpy.types.Context, main_tree: bpy.types.NodeTree|None = None) -> dict:
        """main_tree: the dst node tree to get nodes from, if None, use the current edit tree."""
        self.ser_context.init_on_serializing_preset(bl_context, main_tree)
        return self.serializer.specify_serialize(self.ser_context.main_tree, None, self.ser_stgs.preset)

    def serialize_node_tree(self, bl_context: bpy.types.Context, node_tree: bpy.types.NodeTree) -> dict:
        """Serialize the entire node tree."""
        self.ser_context.init_on_serializing_preset(bl_context)
        self.ser_context.node_tree = node_tree
        return self.serializer.specify_serialize(node_tree, None, self.ser_stgs.node_tree)

    def serialize_interface(self, bl_context: bpy.types.Context, node_tree: bpy.types.NodeTree) -> dict:
        """Serialize the interface of the main tree."""
        self.ser_context.init_on_serializing_preset(bl_context)
        self.ser_context.node_tree = node_tree
        return self.serializer.specify_serialize(node_tree.interface, None, self.ser_stgs.interface)

    def deserialize_preset(self, bl_context: bpy.types.Context, jpreset: dict, main_tree: bpy.types.NodeTree|None = None, is_add_nodes_to_new_tree: bool = False):
        """main_tree: the dst node tree to deserialize into, if None, use the current edit tree."""
        if not jpreset:
            return
        # start_time = time.time()
        self.deser_context.init_on_deserializing_preset(bl_context, jpreset, main_tree, is_add_nodes_to_new_tree=is_add_nodes_to_new_tree)
        self.deserializer.specify_deserialize(self.deser_context.main_tree, jpreset, self.deser_stgs.preset)
        # end_time = time.time()
        # print(f"[HOT NODE DEV] Deserialize preset took {end_time - start_time:.4f} seconds")