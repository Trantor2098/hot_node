import mathutils, os
import bpy
import json
from bpy.types import StringProperty, BoolProperty, EnumProperty
from ..utils import utils
from ..core.serialization.manager import SerializationManager
from collections.abc import Iterable
import pickle

stat_dir_path = os.path.join(os.path.dirname(__file__), "stat")

def is_read_only(obj, attr):
    try:
        original_value = getattr(obj, attr)
        setattr(obj, attr, original_value)  # 尝试重新设置相同的值
        return False  # 如果没有异常，则属性不是只读的
    except AttributeError:
        return "READONLY"  # 如果抛出 AttributeError，则属性是只读的
    
    
def is_readonly_dict(obj, key):
    try:
        original_value = obj[key].copy()  # 获取原始值
        obj[key] = original_value  # 尝试重新设置相同的值
        return False  # 如果没有异常，则属性不是只读的
    except AttributeError:
        return "READONLY"  # 如果抛出 AttributeError，则属性是只读的


def stat_file_path(file_name):
    """
    Get the path to the stat file.

    :param file_name: name of the stat file
    :return: path to the stat file
    """
    return os.path.join(stat_dir_path, file_name)

  
def extract_instance_hierarchy(instance):
    """
    Extract the hierarchy of a class instance and its attributes, till basic types.
    Can be used to analyze what attributes a instance (usually a node) exactly owns.

    :param instance: instance to analyze
    :return: Dict {attr: attr_type / subdict_by_attr}
    """
    def is_basic_type(value):
        return isinstance(value, 
                          (int, float, str, bool, type(None), 
                           list, dict, tuple, bpy.types.Struct, 
                           mathutils.Vector, mathutils.Matrix, mathutils.Color, mathutils.Euler, mathutils.Quaternion,
                           StringProperty, BoolProperty, EnumProperty))

    def get_type_by_attr_of_instance(obj, lvl=1):
        if lvl > 5:
            return str(type(obj)) + " (max level reached)"
        attributes = {}
        i = 0
        if isinstance(obj, bpy.types.bpy_prop_collection):
            for key, value in obj.items():
                if not isinstance(value, (bpy.types.bpy_prop_collection, bpy.types.bpy_prop_array)):
                    attributes[key] = get_type_by_attr_of_instance(value, lvl + 1)
                    if not isinstance(attributes[key], str):
                        attributes[key]["HN_TYPE"] = str(type(value))
                else:
                    attributes[key] = str(type(value))
        elif isinstance(obj, bpy.types.bpy_prop_array):
            length = len(obj)
            for i in range(length):
                item = obj[i]
                attributes[str(i)] = get_type_by_attr_of_instance(item, lvl + 1)
                attributes[str(i)]["HN_TYPE"] = str(type(item))
        else:
            for attr in dir(obj):
                if (not attr.startswith("__")) and (not callable(getattr(obj, attr)) and (not attr in ("bl_rna", "rna_type"))):
                    value = getattr(obj, attr)
                    if is_basic_type(value):
                        attributes[attr] = str(type(value))
                    else:
                        attributes[attr] = get_type_by_attr_of_instance(value, lvl + 1)
                        attributes[attr]["HN_TYPE"] = str(type(value))
        return attributes

    hierarchy = get_type_by_attr_of_instance(instance)
    file_path = stat_file_path("unique_types.json")
    
    
def extract_instances_unique_attr_type(instances):
    """
    Extract the type of the special attributes that cannot be treated as basic types.
    Often these are types that make infinite recursion possible, like collections or arrays.

    :param instances: instances to analyze
    :return: Dict {attr: attr_type / subdict_by_attr}
    """
    unique_types = {}
    max_level_reached_types = {}
    unique_types_details = {}
    max_level_reached_types_details = {}
    def is_basic_type(value):
        return isinstance(value, 
                          (int, float, str, bool, type(None), 
                           list, dict, tuple, bpy.types.Struct, 
                           mathutils.Vector, mathutils.Matrix, mathutils.Color, mathutils.Euler, mathutils.Quaternion,
                           StringProperty, BoolProperty, EnumProperty))

    def get_unique_types_of_instance(attr, obj, lvl=1, node_name=""):
        if lvl > 7:
            # if the max level is reached, return the type of the object
            result = str(type(obj))
            max_level_reached_types[result] = result
            max_level_reached_types_details[result] = max_level_reached_types_details.get(result, {})
            max_level_reached_types_details[result][node_name + ": "  + str(attr)] = True
            return result + " (max level reached)"
        attributes = {}
        i = 0
        if isinstance(obj, bpy.types.bpy_prop_collection):
            for key, value in obj.items():
                if not isinstance(value, (bpy.types.bpy_prop_collection, bpy.types.bpy_prop_array)):
                    attributes[key] = get_unique_types_of_instance(key, value, lvl + 1, node_name=node_name)
                else:
                    result = str(type(value))
                    attributes[key] = result
                    unique_types[result] = True
                    unique_types_details[result] = unique_types_details.get(result, {})
                    unique_types_details[result][node_name + ": " + key] = True
        elif isinstance(obj, bpy.types.bpy_prop_array):
            length = len(obj)
            for i in range(length):
                item = obj[i]
                idx_str = str(i)
                attr_idx = str(attr) + "[" + idx_str + "]"
                if is_basic_type(item):
                    attributes[attr_idx] = attr_idx
                    unique_types[attr_idx] = "array"
                    unique_types_details[attr_idx] = unique_types_details.get(result, {})
                    unique_types_details[attr_idx][node_name + ": "  + attr_idx] = "array"
                else:
                    attributes[attr_idx] = get_unique_types_of_instance(attr_idx, item, lvl + 1, node_name=node_name)
        else:
            for attr in dir(obj):
                if (not attr.startswith("__")) and (not callable(getattr(obj, attr)) and (not attr in ("bl_rna", "rna_type"))):
                    value = getattr(obj, attr)
                    if is_basic_type(value):
                        result = str(type(value))
                        attributes[attr] = result
                        unique_types[attr] = True
                        unique_types_details[result] = unique_types_details.get(result, {})
                        unique_types_details[result][node_name + ": "  + attr] = True
                    else:
                        attributes[attr] = get_unique_types_of_instance(attr, value, lvl + 1, node_name=node_name)
        return attributes

    for instance in instances:
        node_name = utils.cull_bpy_type_like_str(str(type(instance)))
        get_unique_types_of_instance(instance.name, instance, node_name=node_name)
        
    result = [unique_types, max_level_reached_types, unique_types_details, max_level_reached_types_details]
    file_path = stat_file_path("unique_types.json")
    
    
def find_nodes_having_dynamic_inputs(nodes):
    """
    Find all nodes that have dynamic inputs.

    :param node: node to analyze
    :return: type_str list of nodes that have dynamic inputs
    """
    node_type_strs = []
    for node in nodes:
        for attr in dir(node):
            value = getattr(node, attr)
            if (not attr.startswith("__")) and (not callable(value) and (not attr in ("bl_rna", "rna_type")) and isinstance(value, bpy.types.bpy_prop_collection)):
                # if "items" in attr:
                    for sub_attr in dir(value):
                        if (not attr.startswith("__")) and callable(getattr(node, attr)):
                            if "new" in attr:
                                print("Dynamic input found: ", node, attr)
                                node_type_strs.append(utils.cull_bpy_type_like_str(str(type(node))))
                                break
    if not node_type_strs:
        print("No dynamic inputs found.")

    file_path = stat_file_path("dynamic_nodes.json")
    return node_type_strs


def extract_instance_hierarchy_catch_readonly(instances):
    """
    Extract the hierarchy of a class instance and its attributes, till basic types.
    Can be used to analyze what attributes a instance (usually a node) exactly owns.

    :param instance: instance to analyze
    :return: Dict {attr: attr_type / subdict_by_attr}
    """
    def is_basic_type(value):
        return isinstance(value, 
                          (int, float, str, bool, type(None), 
                           list, dict, tuple, bpy.types.Struct, 
                           mathutils.Vector, mathutils.Matrix, mathutils.Color, mathutils.Euler, mathutils.Quaternion,
                           StringProperty, BoolProperty, EnumProperty))

    def get_type_by_attr_of_instance(obj, lvl=1):
        if lvl > 5:
            return str(type(obj)) + " (max level reached)"
        attributes = {}
        i = 0
        if isinstance(obj, bpy.types.bpy_prop_collection):
            for key, value in obj.items():
                if not isinstance(value, (bpy.types.bpy_prop_collection, bpy.types.bpy_prop_array)):
                    attributes[key] = get_type_by_attr_of_instance(value, lvl + 1)
                else:
                    attributes[key] = is_readonly_dict(obj, key)
        elif isinstance(obj, bpy.types.bpy_prop_array):
            length = len(obj)
            for i in range(length):
                item = obj[i]
                attributes[str(i)] = get_type_by_attr_of_instance(item, lvl + 1)
        else:
            for attr in dir(obj):
                if (not attr.startswith("__")) and (not callable(getattr(obj, attr)) and (not attr in ("bl_rna", "rna_type"))):
                    value = getattr(obj, attr)
                    if is_basic_type(value):
                        attributes[attr] = is_read_only(obj, attr)
                    else:
                        # class
                        attributes[attr] = get_type_by_attr_of_instance(value, lvl + 1)
        return attributes
    
    hierarchy = {}
    for instance in instances:
        node_name = utils.cull_bpy_type_like_str(str(type(instance)))
        hierarchy[node_name] = get_type_by_attr_of_instance(instance)
            
    file_path = stat_file_path("unique_types_readonly.json")
    
def save_preset(context):
    manager = SerializationManager()
    preset = manager.serialize_preset(context)
    file_path = stat_file_path("preset.json")
    with open(file_path, "w") as f:
        json.dump(preset, f, indent=1)
        

def load_preset(context):
    manager = SerializationManager()
    file_path = stat_file_path("preset.json")
    with open(file_path, "r") as f:
        jpreset = json.load(f)
    manager.deserialize_preset(context, jpreset)
    return manager