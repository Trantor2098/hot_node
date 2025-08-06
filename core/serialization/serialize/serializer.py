import bpy

from ....utils import utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .stg import Stg
    from .adapter import Adapter
    from ..manager import SerializationManager
    from ...blender.user_pref import HotNodeUserPrefs
    
class Context:
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
        self.prev_obj: object = None # the object calling the dispatch/search/specify serialize

        self.fsockets = None # items_tree of finterface for comparing default value
        self.fnode_by_bl_idname: dict[str, bpy.types.Node] = {} # for comparing
        self.fnode: bpy.types.Node = None

        self.preset_name_when_only_one_node = None
        self.obj_tree: list = []
        
    def init_on_serializing_preset(self, bl_context: bpy.types.Context, main_tree: bpy.types.NodeTree|None = None):
        self.bl_context = bl_context
        self.user_prefs = utils.get_user_prefs(bl_context)
        self.space_data = bpy.context.space_data
        self.node_groups = bpy.data.node_groups
        self.edit_tree = bl_context.space_data.edit_tree if hasattr(bl_context.space_data, "edit_tree") else None
        if main_tree is None:
            self.main_tree = self.edit_tree
        else:
            self.main_tree = main_tree
        self.preset_name_when_only_one_node = None
        self.prev_obj = None

class Serializer:
    """This class use stgs to do the serialization."""
    def __init__(self, manager: 'SerializationManager'):
        self.context = Context()
        self.manager: 'SerializationManager' = manager
        self.stgs: 'Adapter.Stgs' = manager.ser_stgs
        # give the serializer and the stgs ref to each stg
        for stg in self.stgs.stg_list_all:
            stg.serializer = self
            stg.stgs = self.stgs
            stg.context = self.context

    def get_vbya(self, obj, stg: 'Stg'):
        # TODO use map to speed up
        attr_list = None
        for attr_list in stg.attr_lists:
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
            vbya = {attr: getattr(obj, attr) for attr in attr_list.w if hasattr(obj, attr)}
        else:
            # use white and black attrs
            vbya = {
                attr: getattr(obj, attr) 
                for attr in attrs if
                    attr in attr_list.w 
                    or not attr.startswith("__")
                    and not attr.startswith("bl_")
                    and not attr == "rna_type"
                    and not attr in attr_list.b
                    and not callable(getattr(obj, attr))}
        return vbya, attr_list

    def get_stg(self, obj, stg_list: 'list[Stg]|None' = None) -> 'Stg':
        """Loop the stgs to find the stg of the given object."""
        # TODO Type Mapping
        if stg_list is None:
            stg_list = self.stgs.stg_list_core

        for stg in stg_list:
            if isinstance(obj, stg.types):
                return stg

        return self.stgs.stg_list_core[-1]

    def dispatch_serialize(self, obj, fobj: object|None, stg: 'Stg|None' = None):
        """
        Read attributes of the given object, find the stg of each attr and use the stg's serialize method, 
        get the serialization result and return them as a dictionary.
        
        :param obj: The object to serialize.
        :param fobj: The object to compare default value, None to skip comparation.
        :param obj_stg: Will be used to specify the stg of obj, the stg will provide w/b to find vbya. If None, loop to find the stg of obj.
        """
        self.context.obj_tree.append(obj)
        if obj is None:
            return None
        jobj = {}
        
        if stg is None:
            stg = self.get_stg(obj, stg)
        
        vbya, attr_list = self.get_vbya(obj, stg)
        for attr, value in vbya.items():
            if value is None:
                continue
            value_stg = self.get_stg(value)
            cull_default = not self.context.user_prefs.is_maximize_compatibility and stg.cull_default and value_stg.cull_default
            # only serialize when the value has stg
            if value_stg is not None:
                # if attr is in white attrs, serialize it
                if attr_list is not None and attr in attr_list.w:
                    jobj[attr], need = value_stg.serialize(attr, value, None)
                    if value_stg.is_record_type:
                        jvalue["HN@type"] = value.__class__.__name__
                # cull default value if condition met
                elif cull_default and fobj is not None and hasattr(fobj, attr):
                    fvalue = getattr(fobj, attr)
                    jvalue, need = value_stg.serialize(attr, value, fvalue)
                    # serialize when default value changed (determined by stg, known from param "need")
                    if need:
                        jobj[attr] = jvalue
                        if value_stg.is_record_type:
                            jvalue["HN@type"] = value.__class__.__name__
                # serialize directly if not cull default value
                else:
                    jvalue, need = value_stg.serialize(attr, value, None)
                    if need:
                        jobj[attr] = jvalue
                        if value_stg.is_record_type:
                            jvalue["HN@type"] = value.__class__.__name__
        if jobj and stg.is_record_type:
            jobj["HN@type"] = obj.__class__.__name__
        self.context.obj_tree.pop()
        return jobj
    
    def search_serialize(self, obj, fobj: object|None, stg_list: 'list[Stg]|None' = None, is_dispatch_on_fallback=False):
        """
        Serialize the object with specified stg.
        
        :param obj: The object to serialize.
        :param fobj: The object to compare default value, None to skip comparation.
        :param obj_stg: The stg of the object. If None, loop to find the stg of obj.
        """
        self.context.obj_tree.append(obj)
        stg = self.get_stg(obj, stg_list)
        if stg is self.stgs.fallback and is_dispatch_on_fallback:
            # if the stg is fallback, use dispatch_serialize to serialize if needed
            jobj = self.dispatch_serialize(obj, fobj, stg)
        else:
            jobj, need = stg.serialize(None, obj, fobj)
        self.context.obj_tree.pop()
        if jobj and stg.is_record_type:
            jobj["HN@type"] = obj.__class__.__name__
        return jobj
    
    def specify_serialize(self, obj, fobj: object|None, stg: 'Stg'=None):
        """Serialize the object with specified stg."""
        self.context.obj_tree.append(obj)
        jobj, need = stg.serialize(None, obj, fobj)
        self.context.obj_tree.pop()
        if jobj and stg.is_record_type:
            jobj["HN@type"] = obj.__class__.__name__
        return jobj