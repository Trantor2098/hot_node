# BEGIN GPL LICENSE BLOCK #####
#
# This file is part of Hot Node.
#
# Hot Node is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# Hot Node is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hot Node. If not, see <https://www.gnu.org/licenses/>.
#
# END GPL LICENSE BLOCK #####


import bpy
import mathutils

from . import utils, properties


# NOTE 
# Attributes starts with "HN" means it's not correspond to blender's data structures, 
# so cant be put in the has/get/setattr(). They are just for convenience.

# last saved preset
cpreset_cache = {}
cpreset_name_cache = ''

# Only class attributes whose type is in this tuple will be parsed in the progress of parsing another type.
required_attr_types = (
    bpy.types.ColorRamp,
    bpy.types.CurveMapping,
    bpy.types.Image,
)

node_group_id_names = ("ShaderNodeGroup", "GeometryNodeGroup", "CompositorNodeGroup", "TextureNodeGroup")

# <type>, <white attrs>, <black attrs> | white & black list for parsing attributes.
# the lowest type should be in the front, if there are parent relation between two types.
type_wb_attrs = (
    (bpy.types.NodeTreeInterfaceItem, 
    ("item_type", "socket_type", "in_out", "index", "position", "identifier"), 
    ()),
    (bpy.types.NodeSocket,
    (),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "type", "identifier", "is_linked", "is_unavailable")),
    ((bpy.types.ShaderNodeGroup, bpy.types.GeometryNodeGroup, bpy.types.CompositorNodeGroup),
     ("bl_idname",),
     ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "interface")),
    (bpy.types.Node,
    ("bl_idname",),
    ('select', 'dimensions', 'is_active_output', "internal_links", "rna_type", "outputs")),
    ((bpy.types.ColorRampElement, bpy.types.CurveMapPoint),
    ("position", "location"),
    ()),
    ((bpy.types.Image),
    ("name", "alpha_mode", "colorspace_settings", "filepath", "source"),
    ()),
)
    
def get_white_black_attrs(obj):
    for item in type_wb_attrs:
        if isinstance(obj, item[0]):
            return item[1], item[2]
    # fallback black list
    return (), ("rna_type", )


def get_attrs_values(obj, white_attrs: list|tuple=(), black_attrs: list|tuple=(), white_only=False):
    '''Get object's attributes, ignoring attrs that match name in ignore_attrs.'''
    attrs = dir(obj)
    if white_only:
        attrs_values = {attr: getattr(obj, attr) for attr in white_attrs}
    else:
        attrs_values = {attr: getattr(obj, attr) 
                        for attr in attrs if
                        attr in white_attrs
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
        if ivalue != None and list(ivalue) == vector and vector != None:
            is_default = True
        result = vector
    elif isinstance(value, (bool, int, str, float, bpy.types.EnumProperty)):
        if ivalue != None and value == ivalue:
            is_default = True
        result = value
        
    return result, is_default


def parse_attrs(obj, iobj=None, white_only=False):
    '''Parse and record node's attrs to cnode, it's a universal, helpful and powerful function.

    - obj: Father of the attrs waiting to be parsed. Can be a node or an attr that contains other sub attrs.
    - iobj: Newly created obj to get default_value, keep None if dont need to cull values that same as the default.
    - white_only: If True, only attributes on white list will be parsed.
    '''
    # cobj is a dict that mirrors the obj to record attr values
    cobj = {}
    white_attrs, black_attrs = get_white_black_attrs(obj)
    attrs_values = get_attrs_values(obj, white_attrs=white_attrs, black_attrs=black_attrs, white_only=white_only)
    for attr, value in attrs_values.items():
        ivalue = getattr(iobj, attr) if iobj is not None else None
        result, is_default = decode_compare_value(value, ivalue)
        
        # Parse common attrs that dont contains another class, dict... 
        # note that 0, 0.0, False will not go into the branch so, use != None.
        if result != None:
            # Dont parse if value == default, but help white attr pass the default check
            if not is_default or attr in white_attrs:
                cobj[attr] = result
        # parse bpy_prop_collection attr, it's a list of props
        elif isinstance(value, bpy.types.bpy_prop_collection):
            length = len(value)
            ilength = len(ivalue)
            cattr = []
            for i in range(length):
                element = value[i]
                celement = None
                # In some prop collection like color ramp's elements, the number of the element may be dynamic, 
                # here we escape index out of range error.
                if ilength == 0:
                    ielement = None
                elif i > ilength - 1:
                    ielement = ivalue[0]
                else:
                    ielement = ivalue[i]
                result, is_default = decode_compare_value(element, ielement)
                
                if result:
                    # some common value
                    if not is_default or attr in white_attrs:
                        celement = result
                else:
                    # some class...
                    celement = parse_attrs(element, ielement)
                    
                # NOTE HN_idx is our custom attribute to help record the element index in the original list, 
                # because we only have part of the list been recorded. 
                # this can help reducing the json space, escaping repeat {} merely for occupying a right index.
                if celement:
                    cattr.append(celement)
                    celement["HN_idx"] = i
            if cattr:
                    cobj[attr] = cattr
                
        # parse the specfic class attr
        elif isinstance(value, bpy.types.Image):
            cobj[attr] = parse_image(value, bpy.context.scene.hot_node_tex_default_mode)
        elif isinstance(value, required_attr_types):
            cobj[attr] = parse_attrs(value, ivalue)
            
    return cobj


def parse_image(image: bpy.types.Image, open_mode: str, tex_key: str=""):
    cimage = {}
    iimage = bpy.data.images.new("HOTNODE_IMAGE_FOR_COMPARE", width=1, height=1)
    cimage = parse_attrs(image, iimage, white_only=True)
    iimage = bpy.data.images.remove(iimage)
    
    if image is not None:
        cimage["HN_color_space"] = image.colorspace_settings.name
    elif open_mode == 'FIXED_PATH':
        # dont worry, image may be None and this may be reached.
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
        # "HN_parent_HN_idx" is not a blender attr, it's a sugar to get parent in hot node logic.
        # XXX dont know why, if no parent, we can still get item.parent.index as -1. our generate logic is based on this.
        citem["HN_parent_idx"] = item.parent.index
        citems_tree.append(citem)
        
    bpy.data.node_groups.remove(inode_tree)
    return citems_tree


def parse_nodes(nodes: bpy.types.Nodes, parse_all=False):
    cnodes = {}
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
            if bl_idname in node_group_id_names:
                # assign node tree for a blank ng inode, then the node knows what sockets it have
                inode.node_tree = node.node_tree
                cnode = parse_attrs(node, inode)
                # this is a custom attribute
                cnode["HN_nt_name"] = node.node_tree.name
            # elif bl_idname in ("GeometryNodeSimulationInput", "GeometryNodeSimulationOutput"):
            #     node.select = False
            #     continue
            else:
                cnode = parse_attrs(node, inode)
                
            if node.parent and node.parent.select:
                # this is a custom attribute
                cnode["HN_parent_name"] = node.parent.name
            else:
                cnode["HN_parent_name"] = None
            nodes.remove(inode)
            cnodes[name] = cnode
    return cnodes


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

    cnode_tree["interface"] = parse_interface(node_tree)
    cnode_tree['nodes'] = parse_nodes(nodes, parse_all=parse_all)
    cnode_tree["links"] = parse_links(links, parse_all=parse_all)

    return cnode_tree


def parse_node_preset(edit_tree: bpy.types.NodeTree):
    '''Top level parser, parse edit_tree and it's sons into hot node json data. Will update the preset cache.
    
    - edit_tree: Node tree on current user node editor interface.
    - ops: The operator who called this function. Will be used to report error infos.'''
    global cpreset_cache
    cpreset_cache = {}
    sorted_ngs = record_node_group_names(edit_tree)
    # sort ng name by level, ensure the higher level ones are ranked first
    for nt_name, level in sorted_ngs:
        ng_tree = bpy.data.node_groups[nt_name]
        cnode_tree = parse_node_tree(ng_tree, parse_all=True)
        cpreset_cache[nt_name] = cnode_tree
        
    cedit_tree = parse_node_tree(edit_tree)
    cpreset_cache["HN_edit_tree"] = cedit_tree
    
    return cpreset_cache


def record_node_group_names(edit_tree: bpy.types.NodeTree, required_ngs=None, level=1) -> list:
    '''Record all node group the node tree need, and sort their name into a list by level descending order.
    
    - node_tree: The node_tree that need to record it's sub node trees.
    - required_ngs: The dict reference for recursive call, keep None if is first called and it will be automatically created.'''
    if not required_ngs:
        required_ngs = {}
    nodes = edit_tree.nodes
    for node in nodes:
        if level > 1 or node.select:
            bl_idname = node.bl_idname
            if bl_idname in node_group_id_names:
                required_ngs[node.node_tree.name] = level
                record_node_group_names(node.node_tree, required_ngs=required_ngs, level=level + 1)
    sorted_ngs = sorted(required_ngs.items(), key = lambda x: x[1], reverse=True)
    return sorted_ngs


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
    if not properties.allow_tex_save:
        return 'NOT_PRESET_SELECTED'
    
    # find which tree the user is setting...
    if edit_tree.name in ("Shader Nodetree", ):
        cnode_tree = cpreset_cache["HN_edit_tree"]
    else:
        cnode_tree = cpreset_cache[edit_tree.name]
    cnodes: dict = cnode_tree["nodes"]
    
    cnode = cnodes.get(node.name, 'NOTFOUND')
    if cnode == 'NOTFOUND':
        return 'NOT_SAVED_NODE'
    
    image = node.image
    cnode["image"] = parse_image(image, open_mode, tex_key=tex_key)
    return cpreset_cache


def set_preset_data(preset_name, pack_name):
    from . version_control import version
    global cpreset_cache
    cdata = cpreset_cache["HN_preset_data"] = {}
    cdata["preset_name"] = preset_name
    cdata["pack_name"] = pack_name
    cdata["tree_type"] = cpreset_cache["HN_edit_tree"]["bl_idname"]
    cdata["version"] = version
    return cpreset_cache