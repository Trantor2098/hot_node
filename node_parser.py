import bpy
import mathutils

from . import utils, constants

# Properties for Parsing Nodes

# NOTE 
# Attributes starts with "HN" means it's not correspond to blender's data structures, 
# so cant be put in the has/get/setattr(). They are just for convenience.

# Only class attributes whose type is in this tuple will be parsed in the progress of parsing another type.
_required_attr_types = (
    bpy.types.ColorRamp,
    bpy.types.CurveMapping,
    bpy.types.Image,
)


# <type>, <white attrs>, <black attrs>, <special parser func> | white & black list for parsing attributes, and special later parser func for special attrs.
# NOTE the smallest type should be in the front, if there are parent relation between two types.
# NOTE attrs in the white list will be parsed first, and will appear earlier in the json order. It's a feature can be used somehow...
# TODO specify the node tree type (or the super type) then specify the node to improve the parsing speed.
# NOTE This helps escaping some errors, and the other errors were solved by setter's try-except.
_type_wb_attrs_parser = (
    # (bpy.types.NodeTreeInterfaceSocketMenu,
    # ("item_type", "socket_type", "in_out", "index", "position", "identifier"),
    # ("default_value", ),
    # None),
    ((bpy.types.NodeTreeInterfaceItem, bpy.types.NodeTreeInterfacePanel),
    ("item_type", "socket_type", "in_out", "index", "position"), 
    # ("interface_items", ),
    ("interface_items", "identifier"),
    None),
    (bpy.types.NodeSocket,
    (),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "type", "identifier", "is_linked", "is_unavailable", "is_multi_input", "is_output"),
    None),
    ((bpy.types.ShaderNodeGroup, bpy.types.GeometryNodeGroup, bpy.types.CompositorNodeGroup),
     ("bl_idname", "location"),
     ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "interface"),
    None),
    (bpy.types.GeometryNodeCaptureAttribute,
    ("bl_idname", "capture_items", "location"),
    ("rna_type", "dimensions", 'select', "enum_definition", 'is_active_output', "internal_links", "rna_type"),
    "parse_capture_items"),
    (bpy.types.NodeFrame,
    ("bl_idname", "location"),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "width", "height"),
    None),
    (bpy.types.NodeReroute,
    ("bl_idname", "location"),
    ("inputs", "outputs", 'select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "width", "height"),
    None),
    # this can be moved, leave it to the setter to handle the error, but just keep it is fine.
    (bpy.types.GeometryNodeMenuSwitch,
    ("bl_idname", "location"),
    ("rna_type", "dimensions", 'select', "enum_definition", 'is_active_output', "internal_links", "rna_type"),
    None),
    (bpy.types.CompositorNodeColorBalance,
    ("bl_idname", "location", "correction_method", "lift", "gamma", "gain", "offset", "power", "slope"),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type"),
    "parse_compositor_node_color_balance"),
    (bpy.types.Node,
    ("bl_idname", "location"),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type"),
    None),
    ((bpy.types.ColorRampElement, bpy.types.CurveMapPoint),
    ("position", "location"),
    (),
    None),
    ((bpy.types.Image),
    ("name", "alpha_mode", "colorspace_settings", "filepath", "source"),
    (),
    None),
    ((bpy.types.SimulationStateItem, bpy.types.NodeGeometryCaptureAttributeItem, bpy.types.RepeatItem),
    ("socket_type", "name"),
    ("color", "rna_type"),
    None),
)

# TODO replace inner special logic by this class.
# TODO reduce special logics
# For special attributes that need unique logic to parse, containing delegates for parser to invoke. The delegate will be used as Unity's late_update().
class SpecialParser():
    
    @staticmethod
    def parse_capture_items(obj: bpy.types.GeometryNodeCaptureAttribute, cobj: dict):
        # Here we already parsed the ccapture_items, but we should add some own params into the cobj.
        # XXX data_type is the only way to know socket_type but it is not fully capatibale with socket type enum... 
        # why blender dont have a socket_type attribute in CaptureAttributeItem??
        # NOTE Not only GeometryNodeCaptureAttribute have the CaptureAttributeItem, so does ShaderNodeAttribute...
        capture_items = obj.capture_items
        ccapture_items = cobj.get("capture_items", None)
        if ccapture_items is None:
            return
        length = len(capture_items)
        for i in range(length):
            data_type = capture_items[i].data_type
            if data_type.find('VECTOR') != -1:
                ccapture_items[i]["HN_socket_type"] = 'VECTOR'
            else:
                ccapture_items[i]["HN_socket_type"] = data_type
                
    # @staticmethod
    # def parse_bake_items(obj: bpy.types.NodeGeometryBakeItem, cobj: dict):
    #     # Here we already parsed the cbake_items, but we should add some own params into the cobj.
    #     # XXX socket_type is the only way to know socket_type but it is not fully capatibale with socket type enum... 
    #     # why blender dont have a socket_type attribute in CaptureAttributeItem??
    #     # NOTE Not only GeometryNodeCaptureAttribute have the CaptureAttributeItem, so does ShaderNodeAttribute...
    #     bake_items = obj.bake_items
    #     cbake_items = cobj.get("bake_items", None)
    #     if cbake_items is None:
    #         return
    #     length = len(bake_items)
    #     for i in range(length):
    #         socket_type = bake_items[i].socket_type
    #         if socket_type.find('VECTOR') != -1:
    #             cbake_items[i]["HN_socket_type"] = 'VECTOR'
    #         else:
    #             cbake_items[i]["HN_socket_type"] = socket_type
                
    @staticmethod
    def parse_compositor_node_color_balance(obj: bpy.types.CompositorNodeColorBalance, cobj: dict):
        # Here we already parsed the color_balance, but different correction_method need to set different rbg values.
        # e.g. mode OFFSET_POWER_SLOPE need to set offset, power, slope, but escaping setting lift, gamma, gain.
        # if dont do so, setting a wrong value will make the node rgb values incorrect.
        # NOTE Additionally, if both values like lift and offset are set (no matter by user or by our script),
        # the node will be "crashed" and the rgb values will always be incorrect. It's a blender bug i think.
        # For now we only ensure the user set mode's values are correct.
        if obj.correction_method == 'LIFT_GAMMA_GAIN':
            del cobj["offset"]
            del cobj["power"]
            del cobj["slope"]
        elif obj.correction_method == 'OFFSET_POWER_SLOPE':
            del cobj["lift"]
            del cobj["gamma"]
            del cobj["gain"]
                

# ★★★ Functions for Parsing Nodes ★★★
def get_whites_blacks_delegate(obj):
    delegate = None
    for item in _type_wb_attrs_parser:
        if isinstance(obj, item[0]):
            if item[3] is not None:
                delegate = getattr(SpecialParser, item[3])
            return item[1], item[2], delegate
    # fallback black list
    return (), ("rna_type", ), delegate


def get_attrs_values(obj, white_attrs: list|tuple=(), black_attrs: list|tuple=(), white_only=False):
    '''Get object's attributes, the result will depend on the parameters white_attrs, black_attrs, white_only.'''
    attrs = dir(obj)
    if white_only:
        attrs_values = {attr: getattr(obj, attr) for attr in white_attrs}
    else:
        attrs_values = {attr: getattr(obj, attr) 
                        for attr in attrs if
                        (attr in white_attrs and hasattr(obj, attr))
                        or (not attr.startswith("__")
                        and not attr.startswith("bl_")
                        and not attr in black_attrs
                        and not callable(getattr(obj, attr)))}
    return attrs_values


def decode_compare_value(value, ivalue=None):
    '''Decode the common value to json supported format.

    - value: Value of the attribute
    - ivalue: Default value of the attribute, come from a newly generated node. 
      Keep None if dont want to compare, then is_default will always be False.
    - Return: 
        result: The attr's value that can be stored in json, None if uncommon type (usually a list, dict, class).
        is_default: Is the value same with default value (from ivalue)'''
    result = None
    is_default = False
    if isinstance(value, (mathutils.Vector, 
                          mathutils.Euler, 
                          mathutils.Color, 
                          bpy.types.bpy_prop_array)):
        vector = list(value)
        if ivalue is not None and type(value) == type(ivalue) and list(ivalue) == vector and vector != None:
            is_default = True
        result = vector
    elif isinstance(value, (bool, int, str, float, bpy.types.EnumProperty)):
        if ivalue is not None and value == ivalue:
            is_default = True
        result = value
        
    return result, is_default


def parse_attrs_simply(obj, attrs: tuple):
    cobj = {}
    for attr in attrs:
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            if isinstance(value, (mathutils.Vector, 
                                  mathutils.Euler, 
                                  mathutils.Color, 
                                  bpy.types.bpy_prop_array)):
                value = list(value)
            cobj[attr] = value
    return cobj


# XXX have a better structure
def parse_attrs(obj, iobj=None, white_only=False):
    '''Parse and record node's attrs to cnode, it's a universal, helpful and powerful function.

    - obj: Father of the attrs waiting to be parsed. Can be a node or an attr that contains other sub attrs.
    - iobj: Newly created obj to get default_value, keep None if dont need to cull values that same as the default.
    - white_only: If True, only attributes on white list will be parsed.
    '''
    # cobj is a dict that mirrors the obj to record attr values
    cobj = {}
    white_attrs, black_attrs, parse_special = get_whites_blacks_delegate(obj)
    attrs_values = get_attrs_values(obj, white_attrs=white_attrs, black_attrs=black_attrs, white_only=white_only)
    for attr, value in attrs_values.items():
        ivalue = getattr(iobj, attr) if iobj is not None and hasattr(iobj, attr) else None
        result, is_default = decode_compare_value(value, ivalue)
        
        # Parse common attrs that dont contains another class, dict... 
        # Dont parse if value == default, but help white attr pass the default check
        if result is not None and (not is_default or attr in white_attrs):
            cobj[attr] = result
        # parse bpy_prop_collection attr, it's a list of props
        elif isinstance(value, bpy.types.bpy_prop_collection):
            length = len(value)
            ilength = len(ivalue)
            celements = []
            for i in range(length):
                element = value[i]
                celement = None
                
                if ilength == 0:
                    ielement = None
                # In some prop collection like color ramp's elements, the number of the element may be dynamic, 
                # here we escape index out of range error.
                elif i > ilength - 1:
                    # XXX It's safer to set it None, but it will waste some space...
                    # ielement = ivalue[0]
                    ielement = None
                else:
                    ielement = ivalue[i]
                result, is_default = decode_compare_value(element, ielement)
                
                # some common value
                if result is not None:
                    if not is_default or attr in white_attrs:
                        celement = result
                # some class...
                else:
                    celement = parse_attrs(element, ielement)
                    
                # NOTE HN_idx is our custom attribute to help record the element index in the original list, 
                # because we only have part of the list been recorded. 
                # this can help reducing the json space, escaping repeat {} merely for occupying a right index.
                if celement:
                    celements.append(celement)
                    celement["HN_idx"] = i
            # XXX should I add this "if"?
            if celements != []:
                cobj[attr] = celements
                
        # parse special classes
        elif isinstance(value, bpy.types.Image):
            cobj[attr] = parse_image(value, bpy.context.preferences.addons[__package__].preferences.tex_default_mode)
        # if a node refers to a related node attributes, we just get refered node's name for our setter to get a ref
        elif isinstance(value, bpy.types.Node) and attr != "node":
            cobj["HN_ref2_node_attr"] = attr
            cobj["HN_ref2_node_name"] = value.name
        elif isinstance(value, _required_attr_types):
            cobj[attr] = parse_attrs(value, ivalue)
    
    # Late Parse. at the end we merge some extra things with special logic to cobj
    if parse_special is not None:
        parse_special(obj, cobj)
        
    return cobj


def parse_image(image: bpy.types.Image | None, open_mode: str, tex_key: str=""):
    cimage = {}
    iimage = bpy.data.images.new("HOTNODE_IMAGE_FOR_COMPARE", width=1, height=1)
    cimage = parse_attrs(image, iimage, white_only=True)
    iimage = bpy.data.images.remove(iimage)
    
    if image is not None:
        cimage["HN_color_space"] = image.colorspace_settings.name
    elif open_mode == 'FIXED_PATH':
        open_mode = 'STAY_EMPTY'
    cimage["HN_open_mode"] = open_mode
    cimage["HN_tex_keys"] = utils.split_by_slash(tex_key)
    
    return cimage


def parse_interface(node_tree: bpy.types.NodeTree):
    # node group input & output should declear their sockets first. here we do this.
    citems_tree = []
    interface = node_tree.interface
    items_tree = interface.items_tree
    # new items will break the index order. so we add a new tree... is that making a fuss?
    inode_tree: bpy.types.NodeTree = bpy.data.node_groups.new("HOTNODE_NODE_TREE_FOR_COMPARE", node_tree.bl_idname)
    iinterface = inode_tree.interface
    for item in items_tree:
        if item.item_type == 'SOCKET':
            iitem = iinterface.new_socket("HOTNODE_SOCKET_FOR_COMPARE", socket_type=item.socket_type)
        elif item.item_type == 'PANEL':
            iitem = iinterface.new_panel("HOTNODE_SOCKET_FOR_COMPARE")
        citem = parse_attrs(item, iitem)
        # "HN_parent_idx" is not a blender attr, it's a sugar to get parent in hot node logic.
        # XXX dont know why, if no parent, we can still get item.parent.index as -1. our generate logic is based on this.
        # TODO this special logic can be merged into universal logic
        citem["HN_parent_idx"] = item.parent.index
        citems_tree.append(citem)
        
    bpy.data.node_groups.remove(inode_tree)
    
    return citems_tree


def parse_nodes(nodes: bpy.types.Nodes, parse_all=False):
    cnodes = {}
    states = None
    for node in nodes:
        # note that in a node group every nodes are un-selected, we should consider it.
        if parse_all or node.select:
            # node.bl_idname: like ShaderNodeColor, will be used in nodes.new()
            # node.name: the identifier of the node, maybe like Node.001
            bl_idname = node.bl_idname
            # name may be changed when create
            name = node.name
            # inode is used to compare default value. will be destroyed after this loop ends.
            inode = nodes.new(type=bl_idname)
            # setup the node group's node tree to fill this node tree's need
            if bl_idname in constants.node_group_id_names:
                # assign node tree for a blank ng inode, then the node knows what sockets it have
                inode.node_tree = node.node_tree
                cnode = parse_attrs(node, inode)
                # this is a custom attribute
                cnode["HN_nt_name"] = node.node_tree.name if node.node_tree is not None else None
            else:
                cnode = parse_attrs(node, inode)
                
            nodes.remove(inode)
            cnodes[name] = cnode
    if len(cnodes) == 1:
        # Can i dont use for to get the only value?
        for cnode in cnodes.values():
            if cnode["bl_idname"] in constants.node_group_id_names:
                states = cnode.get("label", cnode.get("HN_nt_name", cnode["name"]))
            else:
                name = cnode["name"]
                name, _ = utils.split_name_suffix(name)
                states = cnode.get("label", name)
        
    return cnodes, states


def parse_links(links, parse_all=False):
    clinks = []
    for link in links:
        from_node = link.from_node
        to_node = link.to_node
        from_socket = link.from_socket
        to_socket = link.to_socket
        # create links for ng (because all nodes in ng are needed), and for selected
        if parse_all or from_node.select and to_node.select:
            clink = {}
            clink["HN_from_node_name"] = from_node.name
            clink["HN_to_node_name"] = to_node.name
            outputs = from_node.outputs
            length = len(outputs)
            for i in range(length):
                # fortunatelly it seems like socket type have __eq__() function that allows we to use ==, and it works...
                if from_socket == outputs[i]:
                    clink["HN_from_socket_idx"] = i
                    break
            inputs = to_node.inputs
            length = len(inputs)
            for i in range(length):
                if to_socket == inputs[i]:
                    clink["HN_to_socket_idx"] = i
                    break
            clinks.append(clink)
    return clinks


def parse_node_tree(node_tree: bpy.types.NodeTree, parse_all=False):
    '''Parse the node_tree into our hot node json data.
    
    - node_tree: node_tree to parse
    - parse_all: if False, will only parse the user selectd nodes.'''
    cnode_tree = {}
    cnode_tree["name"] = node_tree.name
    cnode_tree["bl_idname"] = node_tree.bl_idname
    nodes = node_tree.nodes
    links = node_tree.links
    states = None

    cnodes, states = parse_nodes(nodes, parse_all=parse_all)
    
    # make sure the interface is in front of the nodes to let setter set the interface first.
    if check_group_io_node(cnodes):
        cnode_tree["interface"] = parse_interface(node_tree)
    cnode_tree['nodes'] = cnodes
    cnode_tree["links"] = parse_links(links, parse_all=parse_all)

    return cnode_tree, states


def parse_node_preset(edit_tree: bpy.types.NodeTree):
    '''Top level parser, parse edit_tree and it's sons into hot node json data. Will update the preset cache.
    
    - edit_tree: Node tree on current user node editor interface.
    - Return: cpreset_cache'''
    global cpreset_cache
    cpreset_cache = {}
    sorted_ngs = record_node_group_names(edit_tree)
    # sort ng name by level, ensure the lower ones are ranked first
    for nt_name, level in sorted_ngs:
        ng_tree = bpy.data.node_groups[nt_name]
        cnode_tree, _ = parse_node_tree(ng_tree, parse_all=True)
        cpreset_cache[nt_name] = cnode_tree
        
    cedit_tree, states = parse_node_tree(edit_tree)
    cpreset_cache["HN_edit_tree"] = cedit_tree
    
    return cpreset_cache, states


def record_node_group_names(node_tree: bpy.types.NodeTree, required_ng_lvls=None, level=1) -> list:
    '''Record all node group the node tree need, and sort their name into a list by level descending order.
    
    - node_tree: The node_tree that need to record it's sub node trees.
    - required_ngs: The dict reference for recursive call, keep None if is first called and it will be automatically created.
    - lever: The number of layers of recursive calls, also means the ng level. Only for recursively call, for ranking ngs by their hierarchy.'''
    if required_ng_lvls is None:
        required_ng_lvls = {}
    nodes = node_tree.nodes
    for node in nodes:
        # level > 1 means the node is in a node group so record them all, node.select means the node is selected by user
        if level > 1 or node.select:
            if node.bl_idname in constants.node_group_id_names and node.node_tree is not None:
                # record the deeper level
                if required_ng_lvls.get(node.node_tree.name, 0) < level:
                    required_ng_lvls[node.node_tree.name] = level
                record_node_group_names(node.node_tree, required_ng_lvls=required_ng_lvls, level=level + 1)
    if level == 1:
        sorted_ngs = sorted(required_ng_lvls.items(), key = lambda x: x[1], reverse=True)
        return sorted_ngs
    else:
        return required_ng_lvls
    
    
def check_group_io_node(cnodes):
    for cnode in cnodes.values():
        if cnode["bl_idname"] in ("NodeGroupInput", "NodeGroupOutput"):
            return True
    return False


def set_texture_rule(edit_tree: bpy.types.NodeTree, selected_preset, selected_pack, open_mode: str, tex_key: str=""):
    global cpreset_cache
    selected_one = False
    for n in edit_tree.nodes:
        if n.select:
            if selected_one:
                return 'EXCEED'
            selected_one = True
            node = n
    if selected_one == False:
        return 'NO_NODE_SELECTED'
    if not hasattr(node, "image"):
        return 'NOT_TEX_NODE'
    from .props_bl import allow_tex_save
    if not allow_tex_save:
        return 'NOT_PRESET_SELECTED'
    
    # find which tree the user is setting...
    if edit_tree.name in ("Shader Nodetree", ):
        cnode_tree = cpreset_cache["HN_edit_tree"]
    else:
        cnode_tree = cpreset_cache[edit_tree.name]
    cnodes: dict = cnode_tree["nodes"]
    
    cnode = cnodes.get(node.name, None)
    if cnode is None:
        return 'NOT_SAVED_NODE'
    
    image = node.image
    cnode["image"] = parse_image(image, open_mode, tex_key=tex_key)
    
    return cpreset_cache


def set_preset_data(preset_name, pack_name, cpreset: dict|None=None):
    from . versioning import version, blender
    # when in parsing node process, cpreset is stored in global cpreset_cache
    if cpreset is None:
        global cpreset_cache
        cedit_tree = cpreset_cache["HN_edit_tree"]
        cdata = cpreset_cache["HN_preset_data"] = {}
    # we may need to modify a cpreset data, e.g. in version_control.py, in this case the cache is local
    else:
        cedit_tree = cpreset["HN_edit_tree"]
        cdata = cpreset["HN_preset_data"] = {}
    
    cnodes = cedit_tree["nodes"]
    
    location_node_num = 0
    node_center = [0.0, 0.0]
    for cnode in cnodes.values():
        if cnode["bl_idname"] != "NodeFrame":
            clocation = cnode["location"]
            node_center[0] += clocation[0]
            node_center[1] += clocation[1]
            location_node_num += 1
    if location_node_num > 0:
        node_center[0] /= location_node_num
        node_center[1] /= location_node_num
    
    cdata["preset_name"] = preset_name
    cdata["pack_name"] = pack_name
    cdata["tree_type"] = cedit_tree["bl_idname"]
    cdata["node_center"] = node_center
    # NOTE version can be set only when: save preset / set by version_control.py
    cdata["version"] = version
    cdata["blender"] = blender
    
    if cpreset is None:
        return cpreset_cache
    else:
        return cpreset