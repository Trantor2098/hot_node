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

import os
from mathutils import Vector

from . import file, utils, node_parser, versioning, constants

# NOTE 
# In our code, you can see many "HN_ref" key, they are used to escaping get wrong ref because of blender's rename logic.
# NOTE 
# Attributes starts with "HN" means it's not correspond to blender's data structures, 
# so cant be put in the has/get/setattr(). They are just for convenience.
# NOTE 
# Assign the "socket_type" will change default_value, min_value, max_value back to default!

# <type>, <black attrs> | Black list for parsing attributes, escaping assigning some attrs that is read-only, 
# or have side effect, or customized like HN prefixed attrs, etc.
# The lowest type should be in the front, if there are parent relation between two types.
type_b_attrs_setter = (
    ((bpy.types.NodeTreeInterfaceItem, ),
    ("location", "item_type", "socket_type", "in_out", "identifier", "index", "position"),
    None),
    (bpy.types.NodeSocket,
    ("location", "label", ),
    None),
    (bpy.types.Image,
    ("location", "filepath", "name"),
    None),
)

failed_tex_num = 0

class SpecialSetter():
    
    @staticmethod
    def parse_capture_items(obj: bpy.types.GeometryNodeCaptureAttribute, cobj):
        # XXX data_type is the only way to know socket_type but it is not fully capatibale with socket type enum... 
        # why blender dont have a socket_type attribute in CaptureAttributeItem??
        # NOTE Not only GeometryNodeCaptureAttribute have the CaptureAttributeItem, so does ShaderNodeAttribute...
        capture_items = obj.capture_items
        ccapture_items = cobj["capture_items"]
        length = len(capture_items)
        for i in range(length):
            data_type = capture_items[i].data_type
            if data_type.find('VECTOR') != -1:
                ccapture_items[i]["HN_socket_type"] = 'VECTOR'
            else:
                ccapture_items[i]["HN_socket_type"] = data_type
                
    
def get_blacks_delegate(obj):
    delegate = None
    for item in type_b_attrs_setter:
        if isinstance(obj, item[0]):
            if item[2] is not None:
                delegate = getattr(SpecialSetter, item[2])
            return item[1], delegate
    # fallback black list
    return (), delegate


# Tool Method
def check_common(cattrs):
    '''Check if the cattrs is a dict or list containing common attributes like int, float, str, vector'''
    if isinstance(cattrs, dict):
        for cattr in cattrs.values():
            if not isinstance(cattr, (int, float, str)):
                return False
    elif isinstance(cattrs, list):
        for cattr in cattrs:
            if isinstance(cattr, (dict, list)) or not isinstance(cattr, (int, float, str)):
                return False
    else:
        # a dict or list containing complex values...
        return False
    return True


def is_ignore_attr(ignore_attr_owners: tuple[str, str, str], attr: str, owner: str, grand_owner: str):
    if ignore_attr_owners != ():
        for iattr, iowner, igrand_owner in ignore_attr_owners:
            if attr == iattr:
                if owner == iowner or iowner == "":
                    if grand_owner == igrand_owner or igrand_owner == "":
                        return True
    return False


def compare_same(obj1, obj2, ignore_attr_owners=(), owner="", grand_owner="", great_owner=""):
    '''Compare whether a complex dict or list is totally same, but attributes with the owner in ignore_attrs_owner swill pass the compare.
    
    - ignore_attr_owners: ((attr1, owner1, grand_owner1), (attr2, owner2, grand_owner2), ...), "" means any owner is ok. For list elements the owner will be the attr who own the list.
    - owner: Only for recursively call.
    - grand_owner: Only for recursively call.
    - great_owner: Only for recursively call, for list to get their grand owner.'''
    if isinstance(obj1, (bool, int, float, str)) and isinstance(obj2, (bool, int, float, str)):
        if not obj1 == obj2:
            # print(obj1, obj2)
            return False
    elif isinstance(obj1, list) and isinstance(obj2, list):
        length1 = len(obj1)
        length2 = len(obj2)
        if not length1 == length2:
            return False
        for i in range(length1):
            if is_ignore_attr(ignore_attr_owners, owner, grand_owner, great_owner):
                continue
            if not compare_same(obj1[i], obj2[i], ignore_attr_owners=ignore_attr_owners, owner=owner, grand_owner=owner, great_owner=great_owner):
                # print(obj1[i], obj2[i])
                return False
    elif isinstance(obj1, dict) and isinstance(obj2, dict):
        keys1 = list(obj1.keys())
        keys2 = list(obj2.keys())
        # if not compare_same(keys1, keys2):
        if keys1 != keys2:
            return False
        for key in keys1:
            if is_ignore_attr(ignore_attr_owners, key, owner, grand_owner):
                continue
            if not compare_same(obj1[key], obj2[key], ignore_attr_owners=ignore_attr_owners, owner=key, grand_owner=owner, great_owner=great_owner):
                # print(obj1[key], obj2[key])
                return False
    elif not obj1 == obj2:
        # print(obj1, obj2)
        return False
    return True


def check_group_io_node(cnodes):
    for cnode in cnodes.values():
        if cnode["bl_idname"] in ("NodeGroupInput", "NodeGroupOutput"):
            return True
    return False


def open_tex(cobj):
    tex_dir_path = bpy.context.scene.hot_node_props.tex_dir_path
    tolerance=bpy.context.scene.hot_node_props.compare_tolerance
    open_mode = cobj["HN_open_mode"]
    tex_keys = cobj["HN_tex_keys"]
    open_mode = cobj["HN_open_mode"]
    open_mode = cobj["HN_open_mode"]
    open_mode = cobj["HN_open_mode"]
    
    # Keyword Mode
    if open_mode == 'KEYWORD':
        tex_names = file.get_tex_names_in_dir(tex_dir_path)
        if tex_names == 'DIR_NOT_FOUND':
            return 'DIR_NOT_FOUND'
        max_match_num = 0
        tex_name: str = None
        for name in tex_names:
            match_num = 0
            lower_name = name.lower()
            for tex_key in tex_keys:
                if lower_name.find(tex_key.lower()) != -1:
                    match_num += 1
            if match_num > max_match_num:
                tex_name = name
                max_match_num = match_num
        tex_path = "\\".join((tex_dir_path, tex_name))
        if tex_name is None:
            return 'NO_MATCHED_TEX'
    # Stay Empty Mode
    elif open_mode == 'STAY_EMPTY':
        return 'STAY_EMPTY'
    # Fixed Path Mode
    elif open_mode == 'FIXED_PATH':
        tex_path = cobj["filepath"]
        tex_name = cobj["name"]
        if not os.path.exists(tex_path):
            return 'FILE_INEXIST'
    # Similar Mode
    elif open_mode == 'SIMILAR':
        tex_names = file.get_tex_names_in_dir(tex_dir_path)
        if tex_names == 'DIR_NOT_FOUND':
            return 'DIR_NOT_FOUND'
        tex_name = utils.get_similar_str(cobj["name"], tex_names, tolerance=tolerance)
        if not tex_name:
            return 'NO_MATCHED_TEX'
        tex_path = "\\".join((tex_dir_path, tex_name))
    # Auto Mode
    elif open_mode == 'AUTO':
        tex_names = file.get_tex_names_in_dir(tex_dir_path)
        if tex_names == 'DIR_NOT_FOUND':
            tex_path = cobj["filepath"]
            tex_name = cobj["name"]
            if not os.path.exists(tex_path):
                return 'STAY_EMPTY'
        else:
            tex_name = utils.get_similar_str(cobj["name"], tex_names, tolerance=tolerance)
            if not tex_name:
                tex_path = cobj["filepath"]
                tex_name = cobj["name"]
                if not os.path.exists(tex_path):
                    return 'STAY_EMPTY'
            else:
                tex_path = "\\".join((tex_dir_path, tex_name))
        
    images = bpy.data.images
    # have the tex in data
    if images.find(tex_name) != -1:
        old_tex_path = bpy.data.images[tex_name].filepath
        old_tex = bpy.data.images[tex_name]
        # different with the existing tex, load a the new tex and ensure using an unique name
        if not utils.compare_size_same(old_tex_path, tex_path):
            old_name = tex_name
            tex_name = utils.ensure_unique_name(tex_name, -1, images.keys())
            # make a room for new tex
            old_tex.name = "HOTNODE_TEMP_IMAGE"
            # the new image occupied the old name, get the new iamge by old name then change it
            bpy.data.images.load(tex_path, check_existing=False)
            tex = bpy.data.images[old_name]
            tex.name = tex_name
            # reset the old tex
            old_tex.name = old_name
        # same with the existing tex, use the existing one
        else:
            tex = bpy.data.images[tex_name]
    # tex not exists, load new tex
    else:
        bpy.data.images.load(tex_path, check_existing=False)
        tex = bpy.data.images[tex_name]
        
    tex.colorspace_settings.name = cobj["HN_color_space"]
    return tex


def new_element(obj, cobj, attr_name):
    '''New an element of bpy_prop_collection by new() function in blender
    
    - obj: bpy prop collection
    - cattr: An element of the collection, will be used as new()'s input parameter
    - attr_name: Attributs' name, will be used to find what new() to use'''
    def new(*parameter):
        getattr(obj, "new")(*parameter)
    # XXX it's weak. we should use some other way to specify it. maybe need to add an attr_owner...
    if attr_name == "elements":
        new(cobj["position"])
    elif attr_name == "points":
        new(cobj["location"][0], cobj["location"][1])


def set_attrs(obj, cobj, attr_name: str=None, attr_owner=None):
    '''Set obj's attributes.
    
    - obj: The object to set it's attributes.
    - cattrs: The object's mirror in hot node data json format.
    - attr_name: The waitting-for-set attribute name, useful for getting the name of an underlying attr, or an attr conataining a list. 
      Only for recursive call, keep None if you are calling this function menually.
    - black_attrs: Attributes in this will never be setted, for some read-only attrs that could only be setted in new().'''
    # get black attributes that needent be assigned
    if obj is None:
        return
    black_attrs, set_special = get_blacks_delegate(obj)
    if isinstance(cobj, list):
        length = len(obj)
        clength = len(cobj)
        if length == clength:
            for i in range(clength):
                set_attrs(obj[i], cobj[i], attr_name=attr_name)
        elif length < clength:
            # may be the new node should append list manually, like curve[i].points, simulationInputs, etc. here we do this.
            for i in range(clength):
                if i > length - 1:
                    new_element(obj, cobj[i], attr_name)
                set_attrs(obj[i], cobj[i], attr_name=attr_name)
        else:
            # length > clength, for when we only recorded part of the list
            for i in range(clength):
                set_attrs(obj[cobj[i]["HN_idx"]], cobj[i], attr_name=attr_name)
    elif isinstance(cobj, dict):
        for attr, cvalue in cobj.items():
            if attr in black_attrs or attr.startswith("HN_"):
                continue
            elif isinstance(cvalue, list) and not check_common(cvalue):
                sub_obj = getattr(obj, attr)
                set_attrs(sub_obj, cobj[attr], attr_name=attr, attr_owner=obj)
            elif isinstance(cvalue, dict) and not check_common(cvalue.values()):
                sub_obj = getattr(obj, attr)
                set_attrs(sub_obj, cobj[attr], attr_name=attr, attr_owner=obj)
            else:
                # BUG sometimes (often after Ctrl + G and the node group interface is autoly created) tree interface socket's subtype is "", 
                # but it is supposed to be 'NONE'. maybe a blender bug? here we check this to avoid TypeError except.
                if attr == "subtype" and cvalue == "":
                    cvalue = 'NONE'
                setattr(obj, attr, cvalue)
        cobj["HN_ref"] = obj
    elif attr_name not in black_attrs:
        obj = cobj

        
def set_interface(interface, cinterface):
    interface.clear()
    clength = len(cinterface)
    child_parent_pairs = []
    # dont know why, after we newed all the items, their index will change. so we store references.
    for i in range(clength):
        citem = cinterface[i]
        name = citem["name"]
        item_type = citem["item_type"]
        # invoke new() to create item
        if item_type == 'SOCKET':
            in_out = citem["in_out"]
            socket_type = citem["socket_type"]
            item = interface.new_socket(name, in_out=in_out, socket_type=socket_type)
        elif item_type == 'PANEL':
            item = interface.new_panel(name)
            
        # set item attributes
        interface.move(item, citem["position"])
        set_attrs(item, citem)
        citem["HN_ref"] = item
        
        # get parent relations
        if citem["HN_parent_idx"] != -1:
            child_parent_pairs.append((item, citem["HN_parent_idx"], citem["position"]))
    
    # set item parent
    for item, HN_parent_idx, to_position in child_parent_pairs:
        interface.move_to_parent(item, cinterface[HN_parent_idx]["HN_ref"], to_position)
        
        
def set_nodes(nodes, cnodes, cnode_trees, node_offset=Vector((0.0, 0.0)), set_tree_io=False):
    node_cnode_attr_ref2nodenames = []
    later_setup_cnodes = {}
    for cnode in cnodes.values():
        bl_idname = cnode["bl_idname"]
        # new node and get ref
        node = nodes.new(type=bl_idname)
        cnode["HN_ref"] = node
        # set name
        node.name = cnode['name']
        
        # record sub node this node refers to, set it and set node refs after all nodes were created
        ref_to_attr_name = cnode.get("HN_ref2_node_attr", None)
        if ref_to_attr_name is not None:
            node_cnode_attr_ref2nodenames.append((node, cnode, ref_to_attr_name, cnode["HN_ref2_node_name"]))
            
        # Set Special Nodes. TODO Change to delegates
        # set node's sub node tree if node is ng
        if bl_idname in constants.node_group_id_names:
            node.node_tree = cnode_trees[cnode["HN_nt_name"]]["HN_ref"]
        # set node's image
        elif bl_idname in ("NodeGroupInput", "NodeGroupOutput"):
            if not set_tree_io:
                # node.location = cnode["location"]
                continue
        elif cnode.get("image", None):
            tex = open_tex(cnode["image"])
            if tex == 'DIR_NOT_FOUND' or tex == 'FILE_INEXIST' or tex =='NO_MATCHED_TEX':
                failed_tex_num += 1
            elif tex == 'STAY_EMPTY':
                pass
            else:
                node.image = tex
        elif bl_idname == "GeometryNodeSimulationOutput":
            cstate_items = cnode.get("state_items", [])
            length = len(cstate_items)
            # idx 0 is a build-in geometry socket, skip it
            for i in range(1, length):
                citem = cstate_items[i]
                node.state_items.new(citem["socket_type"], citem["name"])
        elif bl_idname == "GeometryNodeCaptureAttribute":
            capture_items = cnode.get("capture_items", [])
            for citem in capture_items:
                node.capture_items.new(citem["HN_socket_type"], citem["name"])
        elif bl_idname == "GeometryNodeSimulationInput":
            later_setup_cnodes[cnode['name']] = (node, cnode)
            continue
        
        # set attributes, io sockets
        set_attrs(node, cnode)
            
    # Set Referenced Nodes to The Nodes refering to them
    for node, cnode, attr, ref2_node_name in node_cnode_attr_ref2nodenames:
        # BUG if have nested frame, when first created and with auto create select, dragging will make 
        # them dance crazily. for now the solution is click some where then select them again...
        # I guess it's because the location and size we set for the frame complict with auto frame adjust...
        cref2_node = cnodes.get(ref2_node_name, None)
        if cref2_node is not None:
            if attr == "paired_output":
                node.pair_with_output(cnodes[ref2_node_name]["HN_ref"])
            # for parent NodeFrames, set parent location means change all sons' locations
            else:
                node.location = Vector(cnode["location"]) + node_offset
                setattr(node, attr, cnodes[ref2_node_name]["HN_ref"])
        # dont have paired output in our data, remove input in late set list
        elif attr == "paired_output":
            # node.location = Vector(cnode["location"]) + node_offset
            del later_setup_cnodes[cnode["name"]]
        
    # Late Attribute Set, for nodes refering to another node
    for node, cnode in later_setup_cnodes.values():
        set_attrs(node, cnode)
        
    # Late Set, for some attributes that should be set in last
    # set location at the end, because parent assign will destroy the location
    for cnode in cnodes.values():
        # set location
        # XXX deselect frames, otherwise the move ops will be wrong. Must have some better way to solve this... May be rewriting a move ops?
        if cnode["bl_idname"] == "NodeFrame":
            # node's real location = node location + frame location. so dont apply duplicated offset to frames
            cnode["HN_ref"].location = Vector(cnode["location"])
        else:
            cnode["HN_ref"].location = Vector(cnode["location"]) + node_offset
        
        
def set_links(links, clinks, cnodes, link_group_io=True):
    for clink in clinks:
        HN_from_socket_idx = clink['HN_from_socket_idx']
        HN_to_socket_idx = clink['HN_to_socket_idx']
        
        from_node = cnodes[clink['HN_from_node_name']]["HN_ref"]
        to_node = cnodes[clink['HN_to_node_name']]["HN_ref"]
		
        if link_group_io or (from_node.bl_idname != "NodeGroupInput" and to_node.bl_idname != "NodeGroupOutput"):
            if (HN_from_socket_idx < len(from_node.outputs) and HN_to_socket_idx < len(to_node.inputs)):
                from_socket = from_node.outputs[HN_from_socket_idx]
                to_socket = to_node.inputs[HN_to_socket_idx]
                links.new(from_socket, to_socket)
            

def set_node_tree(node_tree: bpy.types.NodeTree, cnode_tree, cnode_trees, node_offset=Vector((0.0, 0.0)), set_tree_io=False, link_group_io=True):
    global failed_tex_num
    nodes = node_tree.nodes
    links = node_tree.links
    interface = node_tree.interface
    
    # Deselect Nodes
    for node in nodes:
        node.select = False
        
    # Setup Tree Interface if there are group io nodes in the preset
    if set_tree_io:
        set_interface(interface, cnode_tree["interface"])
            
    cnodes = cnode_tree["nodes"]
    # Generate Nodes & Set Node Attributes & Set IO Socket Value
    set_nodes(nodes, cnodes, cnode_trees, node_offset=node_offset, set_tree_io=set_tree_io)

    # Generate Links
    set_links(links, cnode_tree['links'], cnodes, link_group_io=link_group_io)
            

def apply_preset(context: bpy.types.Context, preset_name: str, pack_name="", apply_offset=False):
    '''Set nodes for the current edit tree'''
    global failed_tex_num
    failed_tex_num = 0
    space_data = context.space_data
    node_groups = bpy.data.node_groups
    # maybe cdata, but we call it cnode_trees
    cnode_trees = file.load_preset(preset_name, pack_name=pack_name)
    cnode_trees = versioning.ensure_preset_version(preset_name, cnode_trees)
    
    # Generate Node Groups
    for cname, cnode_tree in cnode_trees.items():
        if cname in ("HN_edit_tree", "HN_preset_data"):
            continue
        # commpare exist tree
        cname_body, cint_suffix = utils.split_name_suffix(cname)
        if cint_suffix == 0:
            # compare all the ngs that has a cname like body and blender style rename suffix, like cname.001
            found_same = False
            for full_name in node_groups.keys():
                name, int_suffix = utils.split_name_suffix(full_name)
                if name == cname:
                    cexist_tree = node_parser.parse_node_tree(node_groups[cname], parse_all=True)
                    if compare_same(cexist_tree, cnode_tree, ignore_attr_owners=(("location", "", "nodes"),)):
                        cnode_tree["HN_ref"] = node_groups[cname]
                        found_same = True
                        break
            if found_same:
                continue
        # if preset it self have suffix, just compare the one with the same suffix
        else:
            if node_groups.find(cname) != -1:
                cexist_tree = node_parser.parse_node_tree(node_groups[cname], parse_all=True)
                # may be just use == is ok...
                if compare_same(cexist_tree, cnode_tree, ignore_attr_owners=(("location", "", "nodes"),)):
                    cnode_tree["HN_ref"] = node_groups[cname]
                    continue
        # didnt find the same tree, create one
        cname = utils.ensure_unique_name(cname, -1, node_groups.keys())
        node_tree = node_groups.new(cname, cnode_tree["bl_idname"])
        set_node_tree(node_tree, cnode_tree, cnode_trees, set_tree_io=True)
        cnode_tree["HN_ref"] = node_tree
        
    # Generate Main Node Tree To Current Editing Tree
    edit_tree = space_data.edit_tree
    cedit_interface = node_parser.parse_interface(edit_tree)
    # if is base node tree, skip setting io for trees except geo tree
    if edit_tree is space_data.node_tree and edit_tree.bl_idname != "GeometryNodeTree":
        set_tree_io = False
        link_group_io = False
    # if the existing tree interface is capatibale with our preset, just use it
    elif compare_same(cedit_interface, cnode_trees["HN_edit_tree"]["interface"]):
        set_tree_io = False
        link_group_io = True
    # if tree io is not capatible and has group io node, let user to choose whether to reset tree io or not
    elif check_group_io_node(cnode_trees["HN_edit_tree"]["nodes"]):
        set_tree_io = context.preferences.addons[__package__].preferences.overwrite_tree_io
        link_group_io = set_tree_io
    # if dont have group io node, dont need to set tree io
    else:
        set_tree_io = False
        link_group_io = True
    if apply_offset:
        cnode_center = cnode_trees["HN_preset_data"]["node_center"]
        cursor_location = space_data.cursor_location
        node_offset = cursor_location - Vector(cnode_center)
    else:
        node_offset = Vector((0.0, 0.0))
    set_node_tree(edit_tree, cnode_trees["HN_edit_tree"], cnode_trees, node_offset=node_offset, set_tree_io=set_tree_io, link_group_io=link_group_io)
    
    return failed_tex_num