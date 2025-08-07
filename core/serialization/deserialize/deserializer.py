import bpy
import mathutils
# import time
from ....utils import utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .stg import Stg, LateStg
    from .adapter import Adapter
    from ..manager import SerializationManager
    from ...blender.user_pref import HotNodeUserPrefs
    
class DeserializationContext:
    """Context for deserialization, e.g. the node being set currently."""
    def __init__(self):
        self.bl_context: bpy.types.Context = None
        self.user_prefs: 'HotNodeUserPrefs' = None
        self.space_data: bpy.types.Space = None
        self.node_groups: bpy.types.bpy_prop_collection = None # bpy.data.node_groups, can't be set at init because it is not ready yet
        self.main_tree: bpy.types.NodeTree = None
        self.edit_tree: bpy.types.NodeTree = None
        self.node_tree: bpy.types.NodeTree = None
        self.interface: bpy.types.NodeTreeInterface = None
        self.nodes: bpy.types.Nodes = None
        self.node_links: bpy.types.NodeLinks = None
        self.node: bpy.types.Node = None
        
        self.jpreset: dict = None
        self.jdata: dict = None
        self.jnode_trees: dict = None
        self.jmain_tree: dict = None
        self.jnode_tree: dict = None
        self.jnodes: dict = None
        self.jnode_links: dict = None
        self.jnode: dict = None
        
        self.data_node_center: list[float] = [0.0, 0.0]
        self.data_compatible_mode: bool = True
        
        self.existing_node_group_names: list[str] = []
        self.newed_main_tree_nodes: list[bpy.types.Node] = []
        self.cursor_offset: 'mathutils.Vector' = mathutils.Vector((0, 0))
        self.node_frames_with_children: set[bpy.types.Node] = set()  # node with children, used to cancel selection when attaching

        self.is_create_tree = False
        self.is_apply_offset = True
        self.is_setting_main_tree = False
        self.is_add_nodes_to_new_tree = False  # whether the preset is being added to a new tree
        self.is_has_group_io_node = False  # whether the preset has group input/output nodes
        self.is_compatibility_checked = False
        
        # Image file names cache in the user prefs texture directory. 
        # Load every time before deserializing a preset if image obj exists.
        self.image_names_in_dir: list[str] = []
        self.obj_tree: list = []
        
    def init_on_deserializing_preset(self, bl_context: bpy.types.Context, jpreset: dict, main_tree: bpy.types.NodeTree|None = None, is_add_nodes_to_new_tree: bool = False):
        self.__init__()
        
        self.bl_context = bl_context
        self.user_prefs = utils.get_user_prefs(bl_context)
        self.space_data = bl_context.space_data
        self.node_groups = bpy.data.node_groups
        self.edit_tree = bl_context.space_data.edit_tree if hasattr(bl_context.space_data, "edit_tree") else None
        if main_tree is None:
            self.main_tree = self.edit_tree
        else:
            self.main_tree = main_tree

        jdata: dict = jpreset.get("HN@data", {})
        self.jpreset = jpreset
        self.jdata = jdata
        self.jnode_trees = jpreset.get("HN@node_trees", {})
        self.jmain_tree = self.jnode_trees.get("HN@main_tree", {})
        
        # use get to avoid KeyError if the key is not present when preset version is old
        self.data_node_center = jdata.get("node_center", [0.0, 0.0])
        self.data_compatible_mode = jdata.get("compatible_mode", True)
        
        self.existing_node_group_names = list(self.node_groups.keys())
        self.image_names_in_dir = []
        self.is_add_nodes_to_new_tree = is_add_nodes_to_new_tree
        
    def cal_cursor_offset(self):
        self.cursor_offset = self.bl_context.space_data.cursor_location - mathutils.Vector(self.data_node_center)

    def clear_cursor_offset(self):
        """Clear the cursor offset."""
        self.cursor_offset = mathutils.Vector((0, 0))

class Deserializer:
    """This class use stgs to do the serialization."""
    def __init__(self, manager: 'SerializationManager'):
        self.context = DeserializationContext()
        self.manager: 'SerializationManager' = manager
        self.stgs: 'Adapter.Stgs' = manager.deser_stgs
        # give the serializer and the stgs ref to each stg
        for stg in self.stgs.stg_list_all:
            stg.deserializer = self
            stg.stgs = self.stgs
            stg.context = self.context

    def get_vbya(self, obj, obj_stg: 'Stg'):
        attr_list = None
        for attr_list in obj_stg.attr_lists:
            # find the first valid attr_list if there are multiple attr_lists
            if attr_list.is_valid():
                break
            
        attrs = dir(obj)
        if attr_list is None:
            # dont have white or black attrs, serialize all attrs, except private & bl_ & callable & rna
            vbya = {attr: getattr(obj, attr) 
                    for attr in attrs if
                    not attr.startswith("__")
                    and not attr.startswith("bl_")
                    and not attr == "rna_type"
                    and not callable(getattr(obj, attr))}
        elif attr_list.is_white_only:
            # only serialize white attrs
            vbya = {attr: getattr(obj, attr) for attr in attr_list.w}
        else:
            # use white and black attrs
            vbya = {attr: getattr(obj, attr) 
                    for attr in attrs if
                    (attr in attr_list.w and hasattr(obj, attr))
                    or (not attr.startswith("__")
                    and not attr.startswith("bl_")
                    and not attr == "rna_type"
                    and not attr in attr_list.b
                    and not callable(getattr(obj, attr)))}
        return vbya, attr_list
    
    def get_stg(self, obj_or_type_str: object|str, stg_list: 'list[Stg]|Stg' = None) -> 'Stg':
        """Loop the stgs to find the stg of the given object/key(attr_name)."""
        if stg_list is None:
            stg_list = self.stgs.stg_list_core
        if not isinstance(stg_list, list):
            stg_list = [stg_list]
        if obj_or_type_str is None:
            return stg_list[-1]
        
        if isinstance(obj_or_type_str, str):
            obj_type = getattr(bpy.types, obj_or_type_str, None)
        else:
            obj_type = obj_or_type_str.__class__
        
        if obj_type is not None:
            for stg in stg_list:
                for stg_type in stg.types:
                    if obj_type is stg_type or issubclass(obj_type, stg_type):
                        return stg
        return stg_list[-1]
        
    def dispatch_deserialize(self, obj, jobj: dict, stg_list: 'list[Stg]|Stg|None' = None, b: set[str] = set()):
        self.context.obj_tree.append(obj)
        if jobj is None:
            return
        # start_time = time.time()
        if stg_list is None:
            stg_list = self.stgs.stg_list_core
            
        if not isinstance(stg_list, list):
            stg_list = [stg_list]
        
        for attr, jvalue in jobj.items():
            if b and attr in b or attr.startswith("HN@"):
                continue
            elif isinstance(jvalue, dict):
                value = getattr(obj, attr)
                if jvalue.get("HN@stg"):
                    self.stgs.hn.deserialize(value, jvalue)
                else:
                    self.get_stg(jvalue.get("HN@type", obj), stg_list).deserialize(value, jvalue)
            else:
                self.stgs.set.deserialize(obj, attr, jvalue)
                
        # end_time = time.time()
        self.context.obj_tree.pop()
        # if obj is not None:
        #     utils.print_time_cost("Dispatch Deser Cost", obj.rna_type.identifier, start_time, end_time, threshold=0.002)
        
    def search_deserialize(self, obj, jobj, stg_specifier: object|str|None = None, stg_list: 'list[Stg]' = None, is_dispatch_on_fallback: bool = False):
        self.context.obj_tree.append(obj)
        if jobj is None:
            return
        # start_time = time.time()
        if stg_specifier is None:
            stg_specifier = obj
        stg = self.get_stg(stg_specifier, stg_list)
        if stg is self.stgs.fallback and is_dispatch_on_fallback:
            # if the stg is fallback, use dispatch_deserialize to deserialize if needed
            self.dispatch_deserialize(obj, jobj, stg_list)
        else:
            stg.deserialize(obj, jobj)
        self.context.obj_tree.pop()
    
    def specify_deserialize(self, obj, jobj, stg: 'Stg'):
        self.context.obj_tree.append(obj)
        if jobj is None:
            return
        stg.deserialize(obj, jobj)
        self.context.obj_tree.pop()
        
    def specify_request(self, obj, stg: 'LateStg', *args):
        """Request the stg to do something before serializing."""
        self.context.obj_tree.append(obj)
        stg.request(*args)
        self.context.obj_tree.pop()