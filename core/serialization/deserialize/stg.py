import bpy
import mathutils

from ....utils import constants
from ....utils.file_manager import FileManager
from ....utils import utils
from ....utils.reporter import Reporter

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .adapter import Adapter
    from .deserializer import Deserializer, DeserializationContext
    

# NOTE How to add stg and use it:
# 1. See the existing stgs to get familiar with the script.
# 2. Create a new class that inherits from its subclasses.
# 3. Set the types in __init__() by calling self.set_types() with the class or bl_idname, this tells the deserializer which type to use.
# 4. Implement the deserialize() method to handle the deserialization logic for the specific type.
# 5. Register the new stg to the adapter.


class Stg:
    def __init__(self):
        self.set_types()
        self.cull_default = False # Whether to cull default value of the obj of this stg.
        self.types: tuple[type] = () # bl_idname/__class__.__name__ to find
        self.b = () # attr in b wont be set
        
        self.deserializer: Deserializer = None # The serializer instance. Will be set by the serializer.
        self.stgs: Adapter.Stgs = None # The stgs instance. Will be set by the serializer.
        self.context: 'DeserializationContext' = None
        self.fm = FileManager()
        
    def deserialize(self, obj, jobj: dict):
        print(f"[Hot Node] Deserialization not implemented for {obj.__class__.__name__} (no action was done).")
    
    def set_types(self, *args: type|str):
        """For compatibility reasons, pass str instead of type."""
        types = []
        for arg in args:
            if isinstance(arg, str):
                arg_type = getattr(bpy.types, arg, None)
                if arg_type is not None:
                    types.append(arg_type)
            else:
                types.append(arg)
        self.types = tuple(types)


class LateStg(Stg):
    def __init__(self):
        super().__init__()
        self.request_list = [] # A list of requests to be processed later.
    
    def deserialize(self):
        self.request_list.clear()
        pass
    
    def request(self, *args):
        """Request to process the deserialization later."""
        self.request_list.append(args)


class FallbackStg(Stg):
    def __init__(self):
        super().__init__()
        
    def deserialize(self, obj, jobj: dict):
        if constants.IS_DEV:
            print("[Hot Node] Deser FallbackStg Accessed:")
            print(f" | node: {self.context.node}")
            print(f" | obj: {obj}")
            print(f" | jobj: {jobj}")
            print()
        self.deserializer.dispatch_deserialize(obj, jobj)


class PresetStg(Stg):
    def __init__(self):
        super().__init__()
    
    def deserialize(self, main_tree: bpy.types.Context, jpreset: dict):
        context = self.context
        
        node_tree_stg = self.stgs.node_tree
        node_links_stg = self.stgs.node_links
        
        # set node groups
        node_tree_stg.is_set_tree_io = True
        node_links_stg.is_link_group_io = True
        jnode_trees = jpreset.get("HN@node_trees")
        if jnode_trees is None:
            Reporter.report_warning("No node data found in the preset.")
            return
        for jname, jnode_tree in jnode_trees.items():
            if jname == "HN@main_tree":
                continue
            if context.node_groups.find(jname) != -1:
                existing_node_tree = context.node_groups[jname]
                if context.user_prefs.node_tree_reuse_mode == 'TRY_TO_REUSE':
                    if self.is_node_tree_same(existing_node_tree, jnode_tree):
                        jnode_tree["HN@ref"] = existing_node_tree
                        continue
            self.deserializer.specify_deserialize(None, jnode_tree, self.stgs.node_tree)

        # config edit tree deserialization settings
        # for creating geo tree directly
        if context.is_create_tree:
            if self.has_group_io_node(context.jnode_tree):
                node_tree_stg.is_set_tree_io = True
                node_links_stg.is_link_group_io = True
            else:
                node_tree_stg.is_set_tree_io = False
                node_links_stg.is_link_group_io = False
        # if is base node tree and not geo tree, no need to set tree io
        elif context.main_tree is context.space_data.node_tree and context.main_tree.bl_idname != constants.GEOMETRY_NODE_TREE_IDNAME:
            node_tree_stg.is_set_tree_io = False
            node_links_stg.is_link_group_io = False
        # if the edit tree has interface, may happen when it's geo tree or in a node group
        elif context.jmain_tree.get("interface"):
            # if the existing tree interface is capatibale with our preset, just use it
            if self.is_interface_same(context.main_tree, context.jmain_tree.get("interface")):
                node_tree_stg.is_set_tree_io = False
                node_links_stg.is_link_group_io = True
            # if tree io is not capatible and has group io node, let user to choose whether to reset tree io or not, or set when adding nodes to a new tree
            elif self.has_group_io_node(context.jmain_tree):
                node_tree_stg.is_set_tree_io = context.user_prefs.is_overwrite_tree_io or context.is_add_nodes_to_new_tree
                node_links_stg.is_link_group_io = node_tree_stg.is_set_tree_io
            # if dont have group io node, dont need to set tree io
            else:
                node_tree_stg.is_set_tree_io = False
                node_links_stg.is_link_group_io = True # whatever, wont be used
        # dont know how to go into this branch
        else:
            node_tree_stg.is_set_tree_io = False
            node_links_stg.is_link_group_io = True
        
        if context.is_apply_offset and not context.is_create_tree:
            context.cal_cursor_offset()
        else:
            context.clear_cursor_offset()

        # set main tree
        context.is_setting_main_tree = True
        self.deserializer.specify_deserialize(context.main_tree, jnode_tree, self.stgs.node_tree)
        
    def has_group_io_node(self, jnode_tree: dict) -> bool:
        """Check if the node tree has group io nodes."""
        for jnode in jnode_tree["nodes"].values():
            if jnode["bl_idname"] in (constants.NODE_GROUP_INPUT_IDNAME, constants.NODE_GROUP_OUTPUT_IDNAME):
                self.context.is_has_group_io_node = True
                return True
        self.context.is_has_group_io_node = False
        return False
    
    def is_interface_same(self, node_tree, jinterface) -> bool:
        existing_jinterface = self.deserializer.manager.serialize_interface(self.context.bl_context, node_tree)
        return existing_jinterface == jinterface
    
    def is_node_tree_same(self, node_tree, jnode_tree: dict) -> bool:
        """Check if the node tree is the same as the existing one."""
        # serialize node_tree does not guarantee same even they do same, so use interface + node num instead
        # existing_jnode_tree = self.deserializer.manager.serialize_node_tree(self.context.bl_context, node_tree)
        result = len(node_tree.nodes) == len(jnode_tree["nodes"])
        result &= self.is_interface_same(node_tree, jnode_tree.get("interface"))
        return result


class NodeTreeStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeTree)
        self.is_set_tree_io = False # Whether to set the tree interface, i.e. group io nodes.
    
    def deserialize(self, node_tree: bpy.types.NodeTree|None , jnode_tree: dict):
        if node_tree is None:
            node_tree = self.new(jnode_tree)
        self.set_context(node_tree, jnode_tree)
        nodes = node_tree.nodes
        links = node_tree.links
        interface = node_tree.interface
        
        jdescription = jnode_tree.get("description", None)
        jcolor_tag = jnode_tree.get("color_tag", None)
        jdefault_group_node_width = jnode_tree.get("default_group_node_width", None)
        
        if jdescription is not None:
            node_tree.description = jdescription
        if jcolor_tag is not None:
            node_tree.color_tag = jcolor_tag
        if jdefault_group_node_width is not None and hasattr(node_tree, "default_group_node_width"):
            node_tree.default_group_node_width = jdefault_group_node_width
        
        # Deselect Nodes
        for node in nodes:
            node.select = False
            
        # Setup Tree Interface if there are group io nodes in the preset or it's a ng
        if self.is_set_tree_io:
            jinterface = jnode_tree["interface"]
            node_tree
            self.stgs.interface.deserialize(interface, jinterface)
                
        # Generate Nodes & Set Node Attributes & Set IO Socket Value
        jnodes = jnode_tree["nodes"]
        self.stgs.nodes.deserialize(nodes, jnodes)
        
        # Generate Links
        jlinks = jnode_tree["links"]
        self.stgs.node_links.deserialize(links, jlinks)
        
        self.stgs.node_tree_interface_socket_menu_late.deserialize()
        jnode_tree["HN@ref"] = node_tree
        
    def new(self, jnode_tree: dict):
        jname = jnode_tree["name"]
        bl_idname = jnode_tree["bl_idname"]
        jname = utils.ensure_unique_name(jname, self.context.existing_node_group_names)
        node_tree = self.context.node_groups.new(jname, bl_idname)
        return node_tree
    
    def set_context(self, node_tree: bpy.types.NodeTree, jnode_tree: dict):
        self.context.node_tree = node_tree
        if self.context.main_tree is node_tree:
            self.context.is_setting_main_tree = True
        else:
            self.context.is_setting_main_tree = False


class InterfaceStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeTreeInterface)

    def deserialize(self, interface: bpy.types.NodeTreeInterface, jinterface: dict):
        self.context.interface = interface
        interface.clear()
        panels_citems = []
        child_parent_pairs = []
        # dont know why, after we newed all the items, their index will change. so we store references.
        for key, jitem in jinterface.items():
            if key.startswith("HN@"):
                continue
            name = jitem["name"]
            # set "" to the socket name will crash blender, so we set it to "UNNAMED"
            if name == "":
                jitem["name"] = "UNNAMED"
                name = "UNNAMED"
            item_type = jitem["item_type"]
            # invoke new() to create item
            if item_type == 'SOCKET':
                in_out = jitem["in_out"]
                socket_type = jitem["socket_type"]
                item = interface.new_socket(name, in_out=in_out, socket_type=socket_type)
            elif item_type == 'PANEL':
                item = interface.new_panel(name)
                panels_citems.append((item, jitem))
            # TODO There are more types...
            # get ref
            jitem["HN@ref"] = item
            # move position (order)
            interface.move(item, jitem["position"])
                
            # set item attributes
            self.deserializer.dispatch_deserialize(item, jitem, b=("in_out", "socket_type", "position", "index", "item_type"))
            
            # get parent relations
            if jitem["HN@parent_idx"] != -1:
                jparent_item = jinterface[str(jitem["HN@parent_idx"])]
                child_parent_pairs.append((item, jparent_item, jitem["position"]))
                
        jinterface["HN@ref"] = interface
        
        # set item parent
        for item, jparent_item, to_position in child_parent_pairs:
            interface.move_to_parent(item, jparent_item["HN@ref"], to_position)
            
        # putting items into the panel makes the panel go to the top of the interface, 
        # so we set the panel's position again after all items are created
        for panel, jitem in panels_citems:
            interface.move(panel, jitem["position"])

 
class NodeLinksStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeLinks)
        self.is_link_group_io = False
        
    def deserialize(self, node_links: bpy.types.NodeLinks, jnode_links: dict):
        if self.context.node_tree is not self.context.main_tree or self.is_link_group_io:
            for jlink in jnode_links:
                from_node, to_node = self.get_from_and_to_node(jlink)
                self.build_link(jlink, from_node, to_node, node_links)
        else:
            for jlink in jnode_links:
                from_node, to_node = self.get_from_and_to_node(jlink)
                if from_node.bl_idname != "NodeGroupInput" and to_node.bl_idname != "NodeGroupOutput":
                    self.build_link(jlink, from_node, to_node, node_links)
                    # TODO 5.0 GeoNode added a Mode menu, implement support for it

    def get_from_and_to_node(self, jlink: dict):
        jnodes = self.context.jnodes
        from_node_name = jlink['HN@fn_n']
        to_node_name = jlink['HN@tn_n']
        jfrom_node =  jnodes.get(from_node_name)
        jto_node = jnodes.get(to_node_name)
        from_node = jfrom_node["HN@ref"]
        to_node = jto_node["HN@ref"]
        return from_node, to_node
                        
    def build_link(self, jlink, from_node, to_node, node_links: bpy.types.NodeLinks):
        HN_from_socket_idx = jlink['HN@fs_i']
        HN_to_socket_idx = jlink['HN@ts_i']
        
        if not HN_from_socket_idx < len(from_node.outputs) and HN_to_socket_idx < len(to_node.inputs):
            return
        
        from_socket = from_node.outputs[HN_from_socket_idx]
        to_socket = to_node.inputs[HN_to_socket_idx]
        link = node_links.new(from_socket, to_socket)
        
        # if the link valid or is exactly invalid when saving (ser stg only record is_valid when it's False), return
        if link.is_valid or not jlink.get("HN@is_valid", True):
            return link
        
        # try to handle invalid link (usually caused by node socket map change of blender updation)
        HN_to_socket_identifier = jlink["HN@ts_id"]
        HN_to_socket_bl_idname = jlink["HN@ts_bid"]
        HN_from_socket_identifier = jlink["HN@fs_id"]
        HN_from_socket_bl_idname = jlink["HN@fs_bid"]
        
        new_to_socket = None
        if HN_to_socket_bl_idname != to_socket.bl_idname:
            for socket in to_node.inputs:
                if socket.bl_idname == HN_to_socket_bl_idname and socket.identifier == HN_to_socket_identifier:
                    new_to_socket = socket
                    break
                
        new_from_socket = None
        if HN_from_socket_bl_idname != from_socket.bl_idname:
            for socket in from_node.outputs:
                if socket.bl_idname == HN_from_socket_bl_idname and socket.identifier == HN_from_socket_identifier:
                    new_from_socket = socket
                    break
        
        if new_to_socket and new_from_socket:
            node_links.remove(link)
            link = node_links.new(new_from_socket, new_to_socket)
        elif new_to_socket:
            node_links.remove(link)
            link = node_links.new(from_socket, new_to_socket)
        elif new_from_socket:
            node_links.remove(link)
            link = node_links.new(new_from_socket, to_socket)
        else:
            link = None
        return link

    # not fully tested yet, do not use
    def build_link2(self, jlink, from_node, to_node, node_links: bpy.types.NodeLinks):
        HN_from_socket_idx = jlink['HN@fs_i']
        HN_to_socket_idx = jlink['HN@ts_i']
        
        if not HN_from_socket_idx < len(from_node.outputs) and HN_to_socket_idx < len(to_node.inputs):
            return
        
        HN_to_socket_identifier = jlink["HN@ts_id"]
        HN_from_socket_identifier = jlink["HN@fs_id"]
        HN_to_socket_bl_idname = jlink["HN@ts_bid"]
        HN_from_socket_bl_idname = jlink["HN@fs_bid"]
        
        from_socket = from_node.outputs[HN_from_socket_idx]
        to_socket = to_node.inputs[HN_to_socket_idx]

        # try to build link directly by idx
        if (
            # identifier check, to ensure the node socket of this idx is exactly the socket we recorded
            from_socket.identifier == HN_from_socket_identifier 
            and to_socket.identifier == HN_to_socket_identifier
        ):
            link = node_links.new(from_socket, to_socket)
            return link

        # try to build link by identifier
        new_to_socket = self.find_socket_by_identifier(to_node.inputs, HN_to_socket_identifier)
        new_from_socket = self.find_socket_by_identifier(from_node.outputs, HN_from_socket_identifier)

        if new_to_socket and new_from_socket:
            link = node_links.new(new_from_socket, new_to_socket)
        elif new_to_socket:
            link = node_links.new(from_socket, new_to_socket)
        elif new_from_socket:
            link = node_links.new(new_from_socket, to_socket)
        else:
            return None
        return link

    def find_socket_by_identifier(self, sockets, identifier):
        """Find a socket by its identifier."""
        for socket in sockets:
            if socket.identifier == identifier:
                return socket
        return None


class NodesStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.Nodes)
        self.special = True
        self.parse_all = False
        
    def deserialize(self, nodes: bpy.types.Nodes, jnodes: dict):
        self.set_context(nodes, jnodes)
        for key, jnode in jnodes.items():
            if key.startswith("HN@"):
                continue
            # may be handled by other stg
            if jnode.get("HN@ref"):
                continue 
            bl_idname = jnode["bl_idname"]
            
            # new and set node, no try-except for dev
            if constants.IS_DEV:
                node = nodes.new(type=bl_idname)
                self.deserializer.search_deserialize(node, jnode, bl_idname, self.stgs.stg_list_node)
            else:
                try:
                    node = nodes.new(type=bl_idname)
                    self.deserializer.search_deserialize(node, jnode, bl_idname, self.stgs.stg_list_node)
                except Exception as e:
                    # low Blender may dont have the node type
                    if not hasattr(bpy.types, bl_idname):
                        Reporter.report_warning("Current blender version does not support node: " + jnode["name"])
                    else:
                        Reporter.report_warning("Failed to set node: " + jnode["name"])

        # cursor offset will be handled in NodeStg

        jnodes["HN@ref"] = nodes # set late then wont be fond by our setter~

    def set_context(self, nodes, jnodes: dict):
        """Configure the context for the deserializer."""
        context = self.context
        context.nodes = nodes
        context.jnodes = jnodes


class NodeStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.Node)
        if constants.IS_NODE_HAS_LOCATION_ABSOLUTE:
            self.b = ("location",) # to not let 4.4- set location. set it manually.
        else:
            self.b = ("location", "location_absolute")

    def deserialize(self, node, jnode: dict):
        """Template methods to deserialize a node. Override these as you like!"""
        if node is None:
            node = self.new(jnode)
        self.try_set_node_ref(node, jnode)
        self.set_context(node, jnode)
        jnode["HN@ref"] = node
        self.set(node, jnode)
        if not constants.IS_NODE_HAS_LOCATION_ABSOLUTE:
            self.set_loc_4_3_L(node, jnode)
        if self.context.is_apply_offset and self.context.is_setting_main_tree and not self.context.is_create_tree:
            self.set_loc_offset(node, jnode)

    def new(self, jnode: dict):
        bl_idname = jnode["bl_idname"]
        return self.context.nodes.new(type=bl_idname)
    
    def set(self, node, jnode: dict = None):
        """Template method to set node attributes. Override this method to set specific attributes."""
        self.deserializer.dispatch_deserialize(node, jnode, b=self.b)
        
    def try_set_node_ref(self, node, jnode: dict):
        """recursively set parent node first to ensure parent assignment is done before node loc setting"""
        jnode_ref = jnode.get("parent")
        if jnode_ref:
            node.parent = self.set_node_ref(jnode_ref, self.context.node_frames_with_children)

    def set_node_ref(self, jnode_ref: dict, node_set_to_append = None):
        """node_set_to_append: a set to append the parent node to, usually is node_frames_with_children"""
        ref_jnode_name = jnode_ref["HN@ref2_node_name"]
        ref_jnode = self.context.jnodes.get(ref_jnode_name)
        if ref_jnode:
            ref_node = ref_jnode.get("HN@ref")
            # parent_node not created, create it first
            if not ref_node:
                self.deserializer.specify_deserialize(None, ref_jnode, self.stgs.node)
                ref_node = ref_jnode.get("HN@ref")
            if node_set_to_append is not None:
                node_set_to_append.add(ref_node)
            return ref_node
        return None
                
    def set_loc_4_3_L(self, node, jnode: dict = None):
        """for version 4.3 and lower, node dont have location_absolute, but 4.4+ set location by abs loc, so treat old node with abs loc."""
        node.location += mathutils.Vector(jnode["location_absolute"])
        
    def set_loc_offset(self, node, jnode: dict = None):
        node.location += self.context.cursor_offset
        
    def set_context(self, node, jnode):
        self.context.node = node
        self.context.jnode = jnode
        if self.context.is_setting_main_tree:
            self.context.newed_main_tree_nodes.append(node)
        
        
class NodeZoneOutputStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            "GeometryNodeSimulationOutput",
            "GeometryNodeRepeatOutput",
            "GeometryNodeForeachGeometryElementOutput",
        )
        self.items_attrs_map = {
            "GeometryNodeSimulationOutput": ("state_items", ),
            "GeometryNodeRepeatOutput": ("repeat_items", ),
            "GeometryNodeForeachGeometryElementOutput": ("generation_items", "main_items", "input_items"),
        }
    
    def set(self, node, jnode: dict = None):
        items_attrs = self.items_attrs_map.get(node.bl_idname, ())
        # set items first, so that NodeInputs and NodeOutputs can be created before setting them
        for items_attr in items_attrs:
            items = getattr(node, items_attr)
            jitems = jnode.get(items_attr)
            self.deserializer.specify_deserialize(items, jitems, self.stgs.bpy_prop_collection)
            # clear the jitems to avoid setting it again
            jitems = None
        self.deserializer.dispatch_deserialize(node, jnode, b=self.b)
        # jnode["HN@ref"] = node


class NodeZoneInputStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            "GeometryNodeSimulationInput",
            "GeometryNodeRepeatInput",
            "GeometryNodeForeachGeometryElementInput",
        )
        
    def try_set_node_ref(self, node, jnode):
        jpaired_output = jnode.get("paired_output")
        if jpaired_output:
            node.pair_with_output(self.set_node_ref(jpaired_output, None))
        jnode_ref = jnode.get("parent")
        if jnode_ref:
            node.parent = self.set_node_ref(jnode_ref, self.context.node_frames_with_children)

 
class NodeGroupStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.NodeGroup,
            bpy.types.ShaderNodeGroup, # NOTE ShaderNodeGroup and the types below is NOT a subclass of NodeGroup
            bpy.types.GeometryNodeGroup,
            bpy.types.TextureNodeGroup,
            bpy.types.CompositorNodeGroup,
        )
        self.b += ("node_tree",)  # add node_tree to b, so that it will be set by deserializer

    def set(self, node: bpy.types.NodeGroup, jnode: dict):
        jnode_tree_name = jnode.get("HN@nt_name")
        if jnode_tree_name is not None:
            # dst node tree has already been created, so we can set it directly
            dst_node_tree = self.context.jnode_trees[jnode_tree_name]["HN@ref"]
            if dst_node_tree is self.context.main_tree:
                # nesting the tree into itself, which is not allowed.
                # TODO report error
                return
            else:
                node.node_tree = dst_node_tree
        self.deserializer.dispatch_deserialize(node, jnode, b=self.b)
        

class CompositorNodeColorBalanceStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types("CompositorNodeColorBalance")

    def set(self, node: bpy.types.NodeGroup, jnode: dict):
        correction_method = jnode.get("correction_method", 'LIFT_GAMMA_GAIN')
        if correction_method == 'LIFT_GAMMA_GAIN':
            self.b = self.b + ("offset", "power", "slope")
        elif correction_method == 'OFFSET_POWER_SLOPE':
            self.b = self.b + ("lift", "gamma", "gain")
        self.deserializer.dispatch_deserialize(node, jnode, b=self.b)
        

class CompositorNodeOutputFileStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types("CompositorNodeOutputFile")
        self.b += ("file_slots", "format")

    def set(self, node: 'bpy.types.CompositorNodeOutputFile', jnode: dict):
        
        self.deserializer.specify_deserialize(node.format, jnode["format"], self.stgs.image_format_settings)
                
        # TODO
        # 5.0 alpha 2025-08-03 and below: file_slots, layer_slots
        # 5.0: file_output_items
        
        # TODO temp soluction for 0, edit the bpy_prop_collection stg to let items be set in item stgs
        self.deserializer.specify_deserialize(node.file_slots[0], jnode["file_slots"]["0"], self.stgs.compositor_node_output_file_file_slot)
        self.deserializer.specify_deserialize(node.file_slots, jnode["file_slots"], self.stgs.bpy_prop_collection)
        self.deserializer.dispatch_deserialize(node, jnode, b=self.b)


class NodeSocketStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeSocket)
        
    def deserialize(self, socket: bpy.types.NodeSocket, jsocket: dict):
        if socket.bl_idname == "NodeSocketVirtual":
            return
        elif socket.bl_idname == "NodeSocketColor":
            jdefault_value = jsocket.get("default_value", None)
            if jdefault_value == 0.0:
                jdefault_value = [0.0, 0.0, 0.0, 1.0]
                b = ("identifier", "type", "label", "default_value")
            else:
                b = ("identifier", "type", "label")
        else:
            b = ("identifier", "type", "label")
        self.deserializer.dispatch_deserialize(socket, jsocket, b=b)
        
    def new(self, socket_collection, jsocket: dict):
        socket = socket_collection.new(jsocket["type"], jsocket["name"])
        return socket


class ImageStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.Image)

    def deserialize(self, image: bpy.types.Image, jobj: dict):
        dir_to_match_image = self.context.user_prefs.dir_to_match_image
        image_name = jobj["name"]
        image_path = jobj["filepath"]
        images = bpy.data.images
        is_target_image_found = False
        
        # Try 1: search similar name from the directory in user prefs
        if dir_to_match_image and self.fm.is_path_exist(dir_to_match_image):
            # if image file names not cached in this preset applying process, load them
            if not self.context.image_names_in_dir:
                self.context.image_names_in_dir = self.fm.read_dir_file_names_with_suffixes(dir_to_match_image, constants.IMAGE_FILE_SUFFIXES)
                image_file_names = self.context.image_names_in_dir
                name_filter = self.context.user_prefs.image_name_filter
                if name_filter:
                    self.context.image_names_in_dir = [name for name in image_file_names if name_filter in name]
            image_file_names = self.context.image_names_in_dir
            
            target_image_name = utils.get_similar_str(jobj["name"], image_file_names, tolerance=0.5)
            if target_image_name:
                image_name = target_image_name
                image_path = self.fm.join_strs_to_str_path(dir_to_match_image, target_image_name)
                is_target_image_found = True

        # Try 2: load from original path
        if not is_target_image_found and image_path:
            if self.fm.is_path_exist(image_path):
                is_target_image_found = True
                
        # If image file cannot be found, keep image empty
        if not is_target_image_found:
            return
        
        # If have the image in data and the target image file is found, handle confliction and load image
        if images.find(image_name) != -1:
            existing_image: bpy.types.Image = bpy.data.images[image_name]
            # Load new image with uni name if size is different/ existing tex is lost
            if not self.fm.is_path_exist(existing_image.filepath) or not utils.compare_size_same(existing_image.filepath, image_path):
                # handle name conflict
                existing_image_name = image_name
                image_name = utils.ensure_unique_name(image_name, images.keys())
                existing_image.name = "HN@TEMP_IMAGE_NAME"
                image = bpy.data.images.load(image_path, check_existing=False)
                image.name = image_name
                existing_image.name = existing_image_name
            # same with the existing image, use the existing one
            elif is_target_image_found:
                image = bpy.data.images[image_name]
        # image not exists in current and found target image, load
        else:
            bpy.data.images.load(image_path, check_existing=False)
            image = bpy.data.images[image_name]
        
        self.context.obj_tree[-1].image = image # node.image is None so we need to give ref to it manually
        self.deserializer.dispatch_deserialize(image, jobj)
        # path and name may be different since we may load image with a different name
        image.filepath = image_path
        image.name = image_name


class BpyPropCollectionStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.bpy_prop_collection)
        self.new_item_func_map = {
            "NodeGeometryForeachGeometryElementGenerationItems": self.new_socket,
            "NodeGeometryForeachGeometryElementInputItems": self.new_socket,
            "NodeGeometryForeachGeometryElementMainItems": self.new_socket,
            "NodeGeometrySimulationOutputItems": self.new_socket,
            "NodeGeometryRepeatOutputItems": self.new_socket,
            "NodeGeometryBakeItems": self.new_socket,
            "NodeCompositorFileOutputItems": self.new_socket, # 5.0+
            "CompositorNodeOutputFileFileSlots": self.new_file_slot, # 4.5-
            "NodeGeometryCaptureAttributeItems": self.new_capture_item,
            "ColorRampElements": self.new_color_ramp_element,
            "CurveMapPoints": self.new_curve_map_point,
            "NodeMenuSwitchItems": self.new_node_enum_item,
        }

    def deserialize(self, obj, jobj):
        index_strs = list(key for key in jobj.keys() if key.isdigit())
        max_jobj_index = int(index_strs[-1]) if index_strs else -1
        jobj_length = len(index_strs)
        actual_length = len(obj)
        
        # if the length is the same, we can set all items.
        if actual_length == jobj_length:
            for i in range(actual_length):
                self.deserializer.search_deserialize(obj[i], jobj[str(i)], is_dispatch_on_fallback=True)
        elif actual_length < jobj_length:
            # wtf is this. solve in the future
            if max_jobj_index >= jobj_length:
                pass
            # actual_length < jobj_length < max_jobj_index
            else:
                new_item_func = self.new_item_func_map.get(obj.rna_type.identifier, None)
                if new_item_func is None:
                    print(f"[Hot Node] No new item function found for {obj.rna_type.identifier}. Trying fallback new_socket method...")
                    try:
                        for i in range(jobj_length):
                            if i >= actual_length:
                                self.new_socket(obj, jobj[str(i)])
                            self.deserializer.search_deserialize(obj[i], jobj[str(i)], is_dispatch_on_fallback=True)
                        print(f"[Hot Node] {obj.rna_type.identifier} has been set.")
                    except Exception as e:
                        print(f"[Hot Node] Failed to run fallback new_socket method for {obj.rna_type.identifier}: {e}")
                else:
                    for i in range(jobj_length):
                        if i >= actual_length:
                            new_item_func(obj, jobj[str(i)])
                        self.deserializer.search_deserialize(obj[i], jobj[str(i)], is_dispatch_on_fallback=True)
        # actual_length > jobj_length, means jobj is partially filled.
        else:
            # wtf is this. solve in the future
            if max_jobj_index >= actual_length:
                print(f"[Hot Node] jobj_length < actual_length < max_jobj_index: {obj.rna_type.identifier}.")
            else:
                for key in (key for key in jobj.keys() if key.isdigit()):
                    # if i < actual_length:
                    #     # we may recorded a virtual input whose idx is bigger than the length, but we dont need to set it.
                    self.deserializer.search_deserialize(obj[int(key)], jobj[key], is_dispatch_on_fallback=True)
                    # self.deserializer.dispatch_deserialize(obj[i], jitem)
                    
    def new_socket(self, collection_obj, jitem):
        collection_obj.new(jitem["socket_type"], jitem["name"])
        
    def new_file_slot(self, collection_obj, jitem):
        # TODO 0 already exists, cant be set here
        collection_obj.new(jitem["path"])
        file_slot = collection_obj[-1]
        self.deserializer.specify_deserialize(file_slot, jitem, self.stgs.compositor_node_output_file_file_slot)

    def new_capture_item(self, collection_obj, jitem):
        # capture items use data_type to determine the type of the item and have different type id like FLOAT_VECTOR
        data_type = jitem["data_type"]
        if "VECTOR" in data_type:
            data_type = 'VECTOR'
        collection_obj.new(data_type, jitem["name"])

    def new_color_ramp_element(self, collection_obj, jitem):
        collection_obj.new(jitem["position"])
        
    def new_curve_map_point(self, collection_obj, jitem):
        collection_obj.new(jitem["location"][0], jitem["location"][1])
        
    def new_node_enum_item(self, collection_obj, jitem):
        collection_obj.new(jitem["name"])
        
        
class CompositorNodeOutputFileFileSlotStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types("CompositorNodeOutputFileFileSlot")
        
    def deserialize(self, slot, jslot):
        juse_node_format = jslot.get("use_node_format", True)
        if not juse_node_format:
            # set use_node_format flag to let slot has format attr
            slot.use_node_format = False
            format = slot.format
            jformat = jslot["format"]
            self.deserializer.specify_deserialize(format, jformat, self.stgs.image_format_settings)
        
        
class ImageFormatSettingsStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types("ImageFormatSettings")
        
    def deserialize(self, format, jformat):
        jcolor_management = jformat.get("color_management", format.color_management)
        # if OVERRIDE, set this flag first to let node has view_settings
        if jcolor_management == 'OVERRIDE':
            format.color_management = 'OVERRIDE'
            view_settings = format.view_settings
            jview_settings = jformat["view_settings"]
            self.deserializer.specify_deserialize(view_settings, jview_settings, self.stgs.color_managed_view_settings)


class ColorManagedViewSettingsStg(Stg):
    def __init__(self):
        super().__init__()
        self.set_types("ColorManagedViewSettings")
        
    def deserialize(self, view_settings, jview_settings):
        # set these flags to let node has attrs to be set
        view_settings.use_curve_mapping = jview_settings.get("use_curve_mapping", view_settings.use_curve_mapping)
        view_settings.use_hdr_view = jview_settings.get("use_hdr_view", view_settings.use_hdr_view)
        # BUG Temperature and Tint cant be set correctly
        view_settings.use_white_balance = jview_settings.get("use_white_balance", view_settings.use_white_balance)
        self.deserializer.dispatch_deserialize(view_settings, jview_settings)


class NodeTreeInterfaceSocketMenuStg(LateStg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeTreeInterfaceSocketMenu)
        
    def deserialize(self, socket, jsocket: dict):
        # TODO Group the stgs to not let this stg to be visited when deserializing the nodes
        # because we only need to set this when we are setting the tree interface
        jdefault_value = jsocket.get("default_value")
        if jdefault_value is not None:
            self.stgs.node_tree_interface_socket_menu_late.request(socket, jdefault_value)


class NodeTreeInterfaceSocketMenuLateStg(LateStg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.NodeTreeInterfaceSocketMenu)
        
    def deserialize(self):
        for socket, jdefault_value in self.request_list:
            self.stgs.set.deserialize(socket, "default_value", jdefault_value)
        
    def request(self, socket, jdefault_value):
        # wait for socket order to be set before setting the default_value of the socket menu.
        self.request_list.append((socket, jdefault_value))
        
        
class HNStg(Stg):
    """Attr starts with HN@ or jobj that contains a HN@type: HN@... will be handled by this stg."""
    def __init__(self):
        super().__init__()
        
    def deserialize(self, value, jvalue):
        # not used, paired_output and parent are now solved in NodeStg.set_ref_node(), they look up the ref2node to set, so dont need late ref/set anymore.
        # TODO clean up
        pass


class SetStg(Stg):
    def __init__(self):
        super().__init__()
        
    def deserialize(self, obj, attr: str, jvalue):
        if jvalue is None:
            return
        try:
            # BUG sometimes (often after Ctrl + G and the node group interface is autoly created) tree interface socket's subtype is "", 
            # but it is supposed to be 'NONE'. maybe a blender bug? here we check this to avoid TypeError except.
            # SOLVE THIS BUG. it happens at gamma node.
            # if attr == "subtype" and jvalue == "":
            #     jvalue = 'NONE'
            if isinstance(jvalue, list):
                jvalue = mathutils.Vector(jvalue)
            setattr(obj, attr, jvalue)
        except Exception as e:
            if constants.IS_DEV:
                print("[Hot Node] SetStg try_setattr failed, see below:")
                print(" | obj:", obj)
                print(" | attr:", attr)
                print(" | jvalue:", jvalue)
                print(f" | exception: {e}")
                print()
                pass
            else:
                pass
                # print("[Hot Node] SetStg try_setattr failed silently.")