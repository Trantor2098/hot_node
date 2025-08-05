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
    
    def set_types(self, *args: type):
        self.types = args


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
            # if tree io is not capatible and has group io node, let user to choose whether to reset tree io or not
            elif self.has_group_io_node(context.jmain_tree):
                node_tree_stg.is_set_tree_io = context.user_prefs.is_overwrite_tree_io
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
        self.deserializer.specify_deserialize(context.main_tree, jnode_tree, self.stgs.node_tree)
        
    def has_group_io_node(self, jnode_tree: dict) -> bool:
        """Check if the node tree has group io nodes."""
        for jnode in jnode_tree["nodes"].values():
            if jnode["bl_idname"] in ("NodeGroupInput", "NodeGroupOutput"):
                return True
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
        if jdefault_group_node_width is not None:
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
                        
    def get_from_and_to_node(self, jlink: dict):
        jnodes = self.context.jnodes
        from_node_name = jlink['HN@from_node_name']
        to_node_name = jlink['HN@to_node_name']
        jfrom_node =  jnodes.get(from_node_name)
        jto_node = jnodes.get(to_node_name)
        from_node = jfrom_node["HN@ref"]
        to_node = jto_node["HN@ref"]
        return from_node, to_node
                        
    def build_link(self, jlink, from_node, to_node, node_links):
        HN_from_socket_idx = jlink['HN@from_socket_idx']
        HN_to_socket_idx = jlink['HN@to_socket_idx']
        if (HN_from_socket_idx < len(from_node.outputs) and HN_to_socket_idx < len(to_node.inputs)):
            from_socket = from_node.outputs[HN_from_socket_idx]
            to_socket = to_node.inputs[HN_to_socket_idx]
            node_links.new(from_socket, to_socket)


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
            bl_idname = jnode["bl_idname"]
            node = nodes.new(type=bl_idname)
            self.deserializer.search_deserialize(node, jnode, bl_idname, self.stgs.stg_list_node)
            
        self.stgs.node_ref_late.deserialize()
        self.stgs.node_set_late.deserialize()
        self.stgs.node_location_set_late.deserialize()

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

    def deserialize(self, node, jnode: dict):
        self.set_context(node, jnode)
        self.set(node, jnode)
        
    def set(self, node, jnode: dict = None, b: tuple[str] = ()):
        self.deserializer.dispatch_deserialize(node, jnode, b=b if b else self.b)
        jnode["HN@ref"] = node
        
    def set_context(self, node, jnode):
        self.context.node = node
        self.context.jnode = jnode
        if self.context.is_setting_main_tree:
            self.context.newed_main_tree_nodes.append(node)
        
        
class NodeZoneOutputStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.GeometryNodeSimulationOutput,
            bpy.types.GeometryNodeRepeatOutput,
            bpy.types.GeometryNodeForeachGeometryElementOutput,
        )
        self.items_attrs_map = {
            bpy.types.GeometryNodeSimulationOutput: ("state_items", ),
            bpy.types.GeometryNodeRepeatOutput: ("repeat_items", ),
            bpy.types.GeometryNodeForeachGeometryElementOutput: ("generation_items", "main_items", "input_items"),
        }
    
    def set(self, node, jnode: dict = None, b: tuple[str] = ()):
        items_attrs = self.items_attrs_map.get(node.__class__, ())
        # set items first, so that NodeInputs and NodeOutputs can be created before setting them
        for items_attr in items_attrs:
            items = getattr(node, items_attr)
            jitems = jnode.get(items_attr)
            self.deserializer.specify_deserialize(items, jitems, self.stgs.bpy_prop_collection)
            # clear the jitems to avoid setting it again
            jitems = None
        self.deserializer.dispatch_deserialize(node, jnode)
        jnode["HN@ref"] = node


class NodeZoneInputStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.GeometryNodeSimulationInput,
            bpy.types.GeometryNodeRepeatInput,
            bpy.types.GeometryNodeForeachGeometryElementInput,
        )
    
    def deserialize(self, node, jnode: dict):
        self.set_context(node, jnode)
        jnode["HN@ref"] = node
        # pair_with_output will build the node's input and output sockets
        has_dst_node = self.stgs.node_ref_late.request(jnode, "paired_output")
        if has_dst_node:
            self.stgs.node_set_late.request(node, jnode, self)


class NodeFrameStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(
            bpy.types.NodeFrame,
        )
        
    def deserialize(self, node, jnode: dict):
        self.set_context(node, jnode)
        self.set(node, jnode)
        self.stgs.node_set_late.specify_request(node, jnode, "location")

 
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

    def deserialize(self, node: bpy.types.NodeGroup, jnode: dict):
        self.set_context(node, jnode)
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
        self.set(node, jnode)
        

class CompositorNodeColorBalanceStg(NodeStg):
    def __init__(self):
        super().__init__()
        self.set_types(bpy.types.CompositorNodeColorBalance)

    def deserialize(self, node: bpy.types.NodeGroup, jnode: dict):
        self.set_context(node, jnode)
        correction_method = jnode.get("correction_method", 'LIFT_GAMMA_GAIN')
        if correction_method == 'LIFT_GAMMA_GAIN':
            b = ("offset", "power", "slope")
        elif correction_method == 'OFFSET_POWER_SLOPE':
            b = ("lift", "gamma", "gain")
        self.set(node, jnode, b=b)


class NodeRefLateStg(LateStg):
    def __init__(self):
        super().__init__()

    def deserialize(self):
        # Set Referenced Nodes to The Nodes refering to them
        for src_jnode, src_ref_attr, dst_jnode in self.request_list:
            src_node = src_jnode["HN@ref"]
            dst_node = dst_jnode["HN@ref"]
            if src_ref_attr == "paired_output":
                src_node.pair_with_output(dst_node)
            elif src_ref_attr == "parent":
                dst_node.location = mathutils.Vector(src_jnode["location"]) + self.context.cursor_offset
                src_node.parent = dst_node
            else:
                self.stgs.set.deserialize(src_node, src_ref_attr, dst_node)
            src_jnode[src_ref_attr] = None
        self.request_list.clear()

    def request(self, src_jnode, attr_name: str):
        """Return True if dst node is found, otherwise return False."""
        dst_node_name = src_jnode[attr_name]["HN@ref2_node_name"]
        dst_jnode = self.context.jnodes.get(dst_node_name)
        if dst_jnode is not None:
            # if is None, it means we dont have dst node in json, maybe it's user didnt save the node's paired output node.
            # when a request is made, the dst node may not be created yet.
            self.request_list.append((src_jnode, attr_name, dst_jnode))
            return True
        else:
            return False


class NodeSetLateStg(LateStg):
    def __init__(self):
        super().__init__()
        self.specific_request_list = [] # for specific attr.
        
    def deserialize(self):
        for node, jnode, stg in self.request_list:
            stg: NodeStg
            stg.set(node, jnode)
        self.request_list.clear()
        for node, jnode, attr in self.specific_request_list:
            self.deserializer.dispatch_deserialize(node, jnode)
        self.specific_request_list.clear()
            
    def request(self, node, jnode, stg: Stg):
        self.request_list.append((node, jnode, stg))
        
    def specify_request(self, node, jnode, attr):
        self.specific_request_list.append((node, jnode, attr))

  
class NodeLocationSetLateStg(LateStg):
    def __init__(self):
        super().__init__()
        
    def deserialize(self):
        jnodes = self.context.jnodes
        apply_offset = False
        if self.context.node_tree is self.context.edit_tree and not self.context.is_create_tree:
            apply_offset = True
            
        cursor_offset = self.context.cursor_offset
        
        for key, jnode in jnodes.items():
            if not apply_offset or key.startswith("HN@"):
                continue
            
            node = jnode["HN@ref"]
            jparent = jnode.get("parent")
                
            if isinstance(node, bpy.types.NodeFrame):
                node.location = mathutils.Vector(jnode["location"])
            elif jparent:
                # real node loc = parent loc + jnode loc (relative to parent) + cursor offset
                parent_jnode = jnodes.get(jparent["HN@ref2_node_name"])
                parent_location = mathutils.Vector(parent_jnode["location"])
                node.location = mathutils.Vector(jnode["location"]) + parent_location + cursor_offset
            else:
                node.location = mathutils.Vector(jnode["location"]) + cursor_offset

      
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
                b = ("type", "label", "default_value")
            else:
                b = ("type", "label")
        else:
            b = ("type", "label")
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
            "NodeGeometryCaptureAttributeItems": self.new_capture_items,
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
                    print(f"[Hot Node] No new item function found for {obj.rna_type.identifier}.")
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
        
    def new_capture_items(self, collection_obj: bpy.types.NodeGeometryCaptureAttributeItems, jitem):
        # capture items use data_type to determine the type of the item and have different type id like FLOAT_VECTOR
        data_type = jitem["data_type"]
        if "VECTOR" in data_type:
            data_type = 'VECTOR'
        collection_obj.new(data_type, jitem["name"])

    def new_color_ramp_element(self, collection_obj: bpy.types.ColorRampElements, jitem):
        collection_obj.new(jitem["position"])
        
    def new_curve_map_point(self, collection_obj: bpy.types.CurveMapPoints, jitem):
        collection_obj.new(jitem["location"][0], jitem["location"][1])
        
    def new_node_enum_item(self, collection_obj: bpy.types.NodeMenuSwitchItems, jitem):
        collection_obj.new(jitem["name"])

   
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
        hn_stg = jvalue["HN@stg"]
        if hn_stg == "NodeRef":
            self.stgs.node_ref_late.request(self.context.jnode, jvalue["HN@ref2_node_attr"])


class SetStg(Stg):
    def __init__(self):
        super().__init__()
        
    def deserialize(self, obj, attr: str, jvalue):
        if jvalue is None:
            return
        try:
            # BUG sometimes (often after Ctrl + G and the node group interface is autoly created) tree interface socket's subtype is "", 
            # but it is supposed to be 'NONE'. maybe a blender bug? here we check this to avoid TypeError except.
            # SOLVE THIS FUCKIGN BUG. it happens at gamma node.
            if attr == "subtype" and jvalue == "":
                jvalue = 'NONE'
            elif isinstance(jvalue, list):
                jvalue = mathutils.Vector(jvalue)
            setattr(obj, attr, jvalue)
        except Exception as e:
            if constants.IS_DEV:
                print("[Hot Node] SetStg try_setattr failed, see below:")
                print(" | obj:", obj)
                print(" | attr:", attr)
                print(" | jvalue:", jvalue)
                print(f" | exception: {e}")
            else:
                print("[Hot Node] SetStg try_setattr failed silently.")