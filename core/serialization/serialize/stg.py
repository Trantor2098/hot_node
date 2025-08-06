import bpy
import mathutils
from ....utils import constants
from ....utils import utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .adapter import Adapter
    from .serializer import Serializer, Context


class Attrlist:
    """
    A class to hold the attribute name list.
    This is used to store the white and black attrs of the stg.
    """
    def __init__(self, w: set[str] = set(), b: set[str] = set(), is_white_only: bool = False, is_valid_func: callable = lambda: True):
        self.w = w
        self.b = b
        self.is_white_only = is_white_only
        self.is_valid_func = is_valid_func
        
    def is_valid(self) -> bool:
        """
        Check if the given attribute is valid.
        
        :param attr: The attribute name to check.
        :return: True if the attribute is valid, False otherwise.
        """
        return self.is_valid_func()


class Stg:
    def __init__(self):
        self.set_types()
        self.cull_default = False # Whether to cull default value of the obj of this stg.
        self.is_record_type = True
        self.types: tuple[type] = () # bl_idname/__class__.__name__ to find
        self.attr_lists: list[Attrlist] = [] # The white or black attrs of the obj of this stg.
        
        self.serializer: Serializer = None # The serializer instance. Will be set by the serializer.
        self.stgs: Adapter.Stgs = None # The stgs instance. Will be set by the serializer.
        self.context: Context = None # The context instance. Will be set by the serializer.
        
        self.hn_stg_id = 0
        self.hn_bl_id = 0

    def serialize(self, attr: str|None, obj, fobj) -> tuple[dict, bool]:
        """
        Serialize the given object.
        
        :param serializer: The serializer instance. For recursive serialization.
        :param attr: The attribute name of the obj to serialize.
        :param obj: The object to serialize.
        :param fobj: The object to compare default value, None to skip comparation.
        :param obj_tree: The previous stg, i.e. stg of the obj that owns the attr.
        :return: (jobj, need), param "need" tells the serializer if the result jobj should be record.
        """
        return self.serializer.dispatch_serialize(obj, fobj), True
    
    def append_attr_list(self, w: tuple[str] = (), b: tuple[str] = (), is_white_only: bool = False, is_valid_func: callable = lambda: True):
        """
        Add an attribute list to the stg.
        
        :param w_attrs: The white attrs of the stg.
        :param b_attrs: The black attrs of the stg.
        :param is_white_only: Whether the stg only has white attrs.
        :param is_valid_func: A function to check if the attr list is valid.
        """
        self.attr_lists.append(Attrlist(set(w), set(b), is_white_only, is_valid_func))
        
    def clear_attr_lists(self):
        """
        Clear the attribute lists of the stg.
        This is used to clear the attribute lists of the parent class.
        """
        self.attr_lists = []
        
    def set_types(self, *args: type):
        self.types = args


class FallbackStg(Stg):
    def __init__(self):
        super().__init__()
    def serialize(self, attr, obj, fobj):
        if constants.IS_DEV:
            print(f"[HOT NODE] Ser FallbackStg Accessed:")
            print(f" |-node: {self.context.node}")
            print(f" |-value's attr: {attr}")
            print(f" |-value's type: {type(obj)}")
            print()
        return None, False


# TODO generate a default value map of old blender versions for higher blender version which changed the default value of some properties to help the backward compatibility.
class PresetStg(Stg):
    def __init__(self):
        super().__init__()
        self.is_record_type = False
        
    def serialize(self, attr, main_tree: bpy.types.NodeTree, fobj):
        jpreset = {}
        jnode_trees = {}
        jpreset["HN@node_trees"] = jnode_trees
        sorted_ngs = self.record_node_group_names(main_tree)
        
        # Parse NodeGroups
        self.stgs.node_tree.parse_all = True
        self.stgs.node_tree.is_main_tree = False
        # sort ng name by level, ensure the lower ones are ranked first
        for node_tree_name, level in sorted_ngs:
            ng_tree = bpy.data.node_groups[node_tree_name]
            jnode_tree = self.serializer.specify_serialize(ng_tree, None, self.stgs.node_tree)
            # jnode_tree, _ = self.stgs.node_tree.serialize(None, ng_tree, None)
            jnode_trees[node_tree_name] = jnode_tree
        
        # Parse main tree
        if main_tree is self.context.edit_tree:
            self.stgs.node_tree.parse_all = False
        else:
            self.stgs.node_tree.parse_all = True
            
        self.stgs.node_tree.is_main_tree = True
        jmain_tree = self.serializer.specify_serialize(main_tree, None, self.stgs.node_tree)
        jnode_trees["HN@main_tree"] = jmain_tree
        if len(jmain_tree["nodes"]) == 1:
            jnode = list(jmain_tree["nodes"].values())[0]
            
            # this also help to filter empty str
            if jnode.get("label"):
                preset_name = jnode["label"]
            elif jnode.get("HN@nt_name"):
                preset_name = jnode["HN@nt_name"]
            else:
                preset_name = jnode["name"]
                
            self.context.preset_name_when_only_one_node = preset_name
        
        self.set_data(jpreset)
        
        return jpreset, True
    
    def set_data(self, jpreset: dict):
        jdata = {}
        jpreset["HN@data"] = jdata
        jnodes = jpreset["HN@node_trees"]["HN@main_tree"]["nodes"]
        location_node_num = 0
        node_center = [0.0, 0.0]
        for jnode in jnodes.values():
            if jnode["bl_idname"] != "NodeFrame":
                jlocation_abs = jnode["location_absolute"]
                node_center[0] += jlocation_abs[0]
                node_center[1] += jlocation_abs[1]
                location_node_num += 1
        if location_node_num > 0:
            node_center[0] /= location_node_num
            node_center[1] /= location_node_num
            
        jdata["node_center"] = node_center
        
    def record_node_group_names(self, node_tree: bpy.types.NodeTree, required_ng_lvls=None, level=1) -> list:
        '''Record all node group the node tree need, and sort their name into a list by level descending order.
        
        - node_tree: The node_tree that need to record it's sub node trees.
        - required_ngs: The dict reference for recursive call, keep None if is first called and it will be automatically created.
        - lever: The number of layers of recursive calls, also means the ng level. Only for recursively call, for ranking ngs by their hierarchy.'''
        if required_ng_lvls is None:
            required_ng_lvls = {}
        nodes = node_tree.nodes
        for node in nodes:
            # level > 1 means the node is in a node group so record them all
            if level > 1 or node.select:
                if node.bl_idname in constants.NODE_GROUP_IDNAMES and node.node_tree is not None:
                    # record the deeper level
                    if required_ng_lvls.get(node.node_tree.name, 0) < level:
                        required_ng_lvls[node.node_tree.name] = level
                    self.record_node_group_names(node.node_tree, required_ng_lvls=required_ng_lvls, level=level + 1)
        if level == 1:
            sorted_ngs = sorted(required_ng_lvls.items(), key = lambda x: x[1], reverse=True)
            return sorted_ngs
        else:
            return required_ng_lvls


class NodeTreeStg(Stg):
    def __init__(self):
        super().__init__()
        self.parse_all = False
        self.is_main_tree = False
        self.is_record_type = False
        
    def serialize(self, attr, node_tree: bpy.types.NodeTree, fobj):
        self.context.node_tree = node_tree
        jnode_tree = {}
        jnode_tree["name"] = node_tree.name
        jnode_tree["bl_idname"] = node_tree.bl_idname
        jnode_tree["color_tag"] = node_tree.color_tag if hasattr(node_tree, "color_tag") else None
        jnode_tree["description"] = node_tree.description if hasattr(node_tree, "description") else None
        jnode_tree["default_group_node_width"] = node_tree.default_group_node_width if hasattr(node_tree, "default_group_node_width") else None
        nodes = node_tree.nodes
        links = node_tree.links

        self.stgs.nodes.parse_all = self.parse_all
        self.stgs.links.parse_all = self.parse_all
        jnodes = self.serializer.specify_serialize(nodes, None, self.stgs.nodes)
        # Node Group or Main Tree with IO Nodes, serialize the interface.
        if not self.is_main_tree or self.has_group_io_node(jnodes):
            # make sure the interface is in front of the nodes to let setter set the interface first.
            jnode_tree["interface"] = self.serializer.specify_serialize(node_tree.interface, None, self.stgs.interface)
        jnode_tree['nodes'] = jnodes
        jnode_tree["links"] = self.serializer.specify_serialize(links, None, self.stgs.links )
        # jnode_tree["links"], _ = self.stgs.links.serialize(None, links, None)

        return jnode_tree, True
    
    def has_group_io_node(self, jnodes) -> bool:
        """Check if the node tree has group input or output node."""
        for jnode in jnodes.values():
            if jnode["bl_idname"] in ("NodeGroupInput", "NodeGroupOutput"):
                return True
        return False


class InterfaceStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeTreeInterface)
        self.is_record_type = False

    def serialize(self, attr, interface: bpy.types.NodeTreeInterface, fobj):
        self.context.interface = interface
        # node group input & output should declear their sockets first. here we do this.
        jitems_tree = {}
        items_tree = interface.items_tree
        fnode_tree: bpy.types.NodeTree = bpy.data.node_groups.new("HN@TEMP_NODE_TREE_FOR_COMPARE", self.context.node_tree.bl_idname)
        finterface = fnode_tree.interface
        
        for i, item in enumerate(items_tree):
            if item.item_type == 'SOCKET':
                fitem = finterface.new_socket("HN@SOCKET_FOR_COMPARE", in_out=item.in_out, socket_type=item.socket_type)
            elif item.item_type == 'PANEL':
                fitem = finterface.new_panel("HN@SOCKET_FOR_COMPARE")
            jitem = self.serializer.specify_serialize(item, fitem, self.stgs.interface_item)
            jitems_tree[str(i)] = jitem
            
        bpy.data.node_groups.remove(fnode_tree)
        return jitems_tree, True


class NodeTreeInterfaceItemStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.NodeTreeInterfaceItem, 
            # bpy.types.NodeTreeInterfacePanel # Panel is a subclass of Item
        )
        self.append_attr_list(
            w=("item_type", "index", "socket_type", "in_out", "position"),
            b=("interface_items", "identifier", "parent")
        )
        self.cull_default = True
        
    def serialize(self, attr, item: bpy.types.NodeTreeInterfaceItem, fitem):
        jitem = self.serializer.dispatch_serialize(item, fitem, self)
        # we take care of "parnet" attr here, so add parent into the black list
        jitem["HN@parent_idx"] = item.parent.index
        return jitem, True


class NodeLinksStg(Stg):
    def __init__(self):
        super().__init__()
        self.parse_all = False
        self.is_record_type = False
        
    def serialize(self, attr, links: bpy.types.NodeLinks, fobj):
        self.context.node_links = links
        jlinks = []
        for link in links:
            from_node = link.from_node
            to_node = link.to_node
            from_socket = link.from_socket
            to_socket = link.to_socket
            # create links for ng (because all nodes in ng are needed), and for selected
            if self.parse_all or from_node.select and to_node.select:
                jlink = {}
                jlink["HN@fn_n"] = from_node.name
                jlink["HN@tn_n"] = to_node.name
                outputs = from_node.outputs
                length = len(outputs)
                for i in range(length):
                    # fortunatelly it seems like socket type have __eq__() function that allows we to use ==, and it works...
                    if from_socket == outputs[i]:
                        jlink["HN@fs_i"] = i
                        jlink["HN@fs_bid"] = from_socket.bl_idname
                        jlink["HN@fs_n"] = from_socket.name
                        jlink["HN@fs_id"] = from_socket.identifier
                        break
                inputs = to_node.inputs
                length = len(inputs)
                for i in range(length):
                    if to_socket == inputs[i]:
                        jlink["HN@ts_i"] = i
                        jlink["HN@ts_bid"] = to_socket.bl_idname
                        jlink["HN@ts_n"] = to_socket.name
                        jlink["HN@ts_id"] = to_socket.identifier
                        break
                jlinks.append(jlink)
        return jlinks, True


class NodesStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.Nodes,)
        self.special = True
        self.parse_all = False
        self.is_record_type = False
        
    def serialize(self, attr, nodes: bpy.types.Nodes, fobj):
        jnodes = {}
        self.context.nodes = nodes
        for node in nodes:
            if self.parse_all or node.select:
                bl_idname = node.bl_idname
                name = node.name
                fnode = nodes.new(bl_idname)
                jnode = self.serializer.search_serialize(node, fnode, self.stgs.stg_list_node)
                jnodes[name] = jnode
                nodes.remove(fnode)
        return jnodes, True


class NodeStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.Node,)
        self.append_attr_list(
            w=("name", "bl_idname", "location", "location_absolute"), 
            b=("node_tree", "internal_links", "rna_type", "select", "dimensions", "is_active_output", "type") # "type" is read-only but it will be culled by default
        )
        self.cull_default = True

    def serialize(self, attr, node: bpy.types.Node, fobj):
        jnode, is_ref = self.pre_serialize(attr, node, fobj)
        if not is_ref:
            jnode = self.serializer.dispatch_serialize(node, fobj, self)
        return jnode, True
    
    def pre_serialize(self, attr, node: bpy.types.Node, fobj):
        """Universal serialization steps before the actual serialization."""
        jnode = {}
        is_ref = False
        if attr is not None:
            # serialize() called by search_serialize() will get attr as None, it means the upper stg is NodesStg
            # if the node is a referenced attribute, we just need to record the node name and the attr
            jnode["HN@ref2_node_attr"] = attr
            jnode["HN@ref2_node_name"] = node.name
            jnode["HN@stg"] = "NodeRef"
            if attr == "parent":
                jnode["HN@ref2_node_loc"] = list(node.location)
            is_ref = True
            self.is_record_type = False
        else:
            self.is_record_type = True
        self.context.node = node
        self.context.fnode = self.context.fnode_by_bl_idname.get(node.bl_idname)
        return jnode, is_ref

 
class LinkStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.bpy_prop_collection,)
        self.is_record_type = False
    
    def serialize(self, attr, obj, fobj):
        # not used
        return None, True


class NodeGroupStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.ShaderNodeGroup,
            bpy.types.GeometryNodeGroup,
            bpy.types.CompositorNodeGroup,
            bpy.types.TextureNodeGroup,
        )
        self.clear_attr_lists()
        self.append_attr_list(
            w=("name", "bl_idname", "location", "location_absolute"), 
            b=("node_tree", "internal_links", "rna_type", "select", "dimensions", "is_active_output")
        )
        self.cull_default = True

    def serialize(self, attr, node, fnode):
        jnode, is_ref= self.pre_serialize(attr, node, fnode)
        if not is_ref:
            # not ref, record as normal, not skip
            # assign node tree for a blank ng fnode, then the node knows what sockets' default_value it have
            fnode.node_tree = node.node_tree
            jnode = self.serializer.dispatch_serialize(node, fnode, self)
            jnode["HN@nt_name"] = node.node_tree.name if node.node_tree is not None else None
        return jnode, True


class NodeSocketStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeSocket,)
        self.append_attr_list(
            b=("node", "select", "dimensions", "is_active_output", "internal_links", "rna_type", "is_linked", "is_unavailable", "is_multi_input", "is_output", "link_limit", "is_icon_visible", "is_inactive", "inferred_structure_type")
        )
        self.cull_default = True

    def serialize(self, attr, obj: bpy.types.NodeSocket, fobj):
        jobj = self.serializer.dispatch_serialize(obj, fobj, self)
        need = jobj != {}
        if need:
            jobj["identifier"] = obj.identifier # for future use.
        return jobj, need


class NodeItemStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.ForeachGeometryElementGenerationItem,
            bpy.types.ForeachGeometryElementInputItem,
            bpy.types.ForeachGeometryElementMainItem,
            bpy.types.RepeatItem,
            bpy.types.SimulationStateItem,
            bpy.types.NodeGeometryBakeItem,
            bpy.types.NodeGeometryCaptureAttributeItem,
        )
        self.append_attr_list(
            w=("name", "socket_type", ), 
            b=("rna_type", "color", "active_item")
        )
        self.cull_default = True
        
    def serialize(self, attr, obj, fobj):
        jobj = self.serializer.dispatch_serialize(obj, fobj, self)
        need = jobj != {}
        return jobj, need


class ImageStg(Stg):
    def __init__(self):
        super().__init__()
        self.cull_default = True
        self.set_types(bpy.types.Image,)
        self.append_attr_list(
            w=("name", "alpha_mode", "filepath", "source", "use_fake_user"),
            # b=("colorspace_settings", "packed_file", "file_format", "file_format_settings", "is_dirty", "render_slots", "type", "stereo_3d_format", "users"),
            is_white_only=True,
        )
        
    def serialize(self, attr, image: bpy.types.Image, fobj):
        if isinstance(self.context.obj_tree[-1], bpy.types.Image):
            return None, False
        jimage = {}
        fimage = bpy.data.images.new("HN@IMAGE_FOR_COMPARE", width=1, height=1)
        image_path = image.filepath
        if image_path is not None and image_path.startswith("//"):
            image_path = bpy.path.abspath(image_path)
            image.filepath = utils.normpath(image_path)
        jimage = self.serializer.dispatch_serialize(image, fimage, self)
        
        if image is not None:
            jimage["colorspace_settings"] = self.serializer.dispatch_serialize(image.colorspace_settings, fimage.colorspace_settings, self)
        
        fimage = bpy.data.images.remove(fimage)
        return jimage, True


class BpyPropCollectionStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.bpy_prop_collection,)
        self.cull_default = True

    def serialize(self, attr, obj, fobj):
        jobj = {}
        is_length_same = False
        # maybe fobj is None, so we need to check if fobj is a collection
        if isinstance(fobj, bpy.types.bpy_prop_collection):
            if len(fobj) == len(obj):
                # only cull default if the items if the length is the same
                is_length_same = True
        for i, item in enumerate(obj):
            fitem = None
            if is_length_same:
                fitem = fobj[i]
            jitem = self.serializer.search_serialize(item, fitem, None, is_dispatch_on_fallback=True)
            if jitem != {}:
                # use the index as key, because we may skip some items
                jobj[str(i)] = jitem
        need = (jobj != {})
        return jobj, need


class BpyPropArrayStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.bpy_prop_array)
        self.cull_default = True
        self.is_record_type = False

    def serialize(self, attr, obj, fobj):
        list_obj = list(obj)
        need = (fobj == None or list_obj != list(fobj))
        return list_obj, need


class FlatVectorStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.bpy_prop_array, 
            mathutils.Vector, 
            mathutils.Color, 
            mathutils.Euler, 
            mathutils.Quaternion,
        )
        self.cull_default = True
        self.is_record_type = False

    def serialize(self, attr, obj, fobj):
        list_obj = list(obj)
        list_fobj = list(fobj) if isinstance(fobj, self.types) else None
        need = (list_obj != list_fobj)
        return list_obj, need


class MatrixStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(mathutils.Matrix,)
        
    def serialize(self, attr, obj, fobj):
        return [list(row) for row in obj], True


class CommonTypeStg(Stg):
    """
    For types that can simply going into the recursive serialization. Useful for escaping infinite recuring.
    """
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.ColorRamp,
            bpy.types.ColorMapping,
            bpy.types.CurveMapping,
            bpy.types.ColorManagedViewSettings,
            bpy.types.ColorManagedDisplaySettings,
            bpy.types.TexMapping,
            bpy.types.ImageFormatSettings,
            bpy.types.ImageUser,
        )
        self.cull_default = True

    def serialize(self, attr, obj, fobj):
        jobj = self.serializer.dispatch_serialize(obj, fobj)
        return jobj, True


class BasicStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bool, int, str, float, bpy.types.EnumProperty)
        self.cull_default = True
        self.is_record_type = False

    def serialize(self, attr, obj, fobj):
        need = fobj == None or obj != fobj
        return obj, need