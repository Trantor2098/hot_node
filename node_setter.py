import bpy

import os
from mathutils import Vector

from . import file, utils, node_parser, versioning, constants, i18n

# NOTE 
# In our code, you can see many "HN_ref" key, they are used to escaping get wrong ref because of blender's rename logic.
# NOTE 
# Attributes starts with "HN" means it's not correspond to blender's data structures, 
# so cant be put in the has/get/setattr(). They are just for convenience.
# NOTE 
# Assign the "socket_type" will change default_value, min_value, max_value back to default!

# <type>, <black attrs>, <special_set_func> | Black list for parsing attributes, escaping assigning some attrs that is read-only, 
# or have side effect, or customized like HN prefixed attrs, etc.
# The lowest type should be in the front, if there are parent relation between two types.
# special_set_func is used as a late setter for some special attributes.
type_b_attrs_setter = (
    ((bpy.types.NodeTreeInterfaceItem, ),
    ("location", "item_type", "socket_type", "in_out", "identifier", "index", "position"),
    None),
    # (bpy.types.NodeTreeInterfaceSocketMenu,
    # ("location", ),
    # "set_interface_socket_menu"),
    (bpy.types.NodeSocket,
    ("location", "label", ),
    None),
    (bpy.types.Image,
    ("location", "filepath", "name"),
    None),
)

failed_tex_num = 0
late_setter_funcs = []

# bug report
current_node_bl_idname = ""
current_node_name = ""
current_cnode = None
bug_infos = []

class SpecialSetter():
    
    @staticmethod
    def set_interface_socket_menu(obj: bpy.types.NodeTreeInterfaceSocketMenu, cobj):
        pass
                
    
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
def report(ops: bpy.types.Operator|None, type, msg: str):
    if ops is None:
        print("Hot Node: A report is required but the ops is None.")
        print(msg)
        return
    ops.report(type, msg)
    
    
def print_error(e, node_bl_idname, obj, cobj, attr_name):
    print()
    print("===== HOT NODE ERROR INFO =====")
    print(e)
    # traceback.print_exc()
    print("------ node ------")
    print(current_node_bl_idname)
    print("------ obj ------")
    print(obj)
    # print("------ cobj ------")
    # print(cobj)
    print("------ attr_name ------")
    print(attr_name)
    print()


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
    
    - ignore_attr_owners: ((attr1, owner1, grand_owner1), (attr2, owner2, grand_owner2), ...), "" means any owner is ok. For list elements the owner and the grand_owner will be the attr who own the list.
    - owner: Only for recursively call.
    - grand_owner: Only for recursively call.
    - great_owner: Only for recursively call, for list to get their grand owner.'''
    if isinstance(obj1, (bool, int, float, str)) and isinstance(obj2, (bool, int, float, str)):
        if not obj1 == obj2:
            # print("obj1, obj2 not same:")
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
                # print("list elements not same:")
                # print(obj1[i])
                # print()
                # print(obj2[i])
                return False
    elif isinstance(obj1, dict) and isinstance(obj2, dict):
        keys1 = list(obj1.keys())
        keys2 = list(obj2.keys())
        # length1 = len(keys1)
        # length2 = len(keys2)
        # if length1 != length2:
        #     print("dict keys length not same:")
        #     return False
        # for i in range(length1):
        #     if keys1[i] != keys2[i] and not is_ignore_attr(ignore_attr_owners, keys2[i], owner, grand_owner):
        #         print("dict keys not same:")
        #         print(keys1[i], keys2[i])
        #         return False
        if keys1 != keys2:
            return False
        for key in keys1:
            if is_ignore_attr(ignore_attr_owners, key, owner, grand_owner):
                continue
            if not compare_same(obj1[key], obj2[key], ignore_attr_owners=ignore_attr_owners, owner=key, grand_owner=owner, great_owner=great_owner):
                # print("dict values not same:")
                # print(obj1[key], obj2[key])
                return False
    elif not obj1 == obj2:
        # print("obj1, obj2 not same:")
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
        if tex_name is None:
            return 'NO_MATCHED_TEX'
        tex_path = os.path.join(tex_dir_path, tex_name)
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
        tex_path = os.path.join(tex_dir_path, tex_name)
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
                tex_path = os.path.join(tex_dir_path, tex_name)
        
    images = bpy.data.images
    # if have the tex in data
    if images.find(tex_name) != -1:
        old_tex_path = bpy.data.images[tex_name].filepath
        old_tex = bpy.data.images[tex_name]
        # if different with the existing tex or the existing tex is lost, 
        # load a new tex and ensure using an unique name
        if not file.exist_path(old_tex_path) or not utils.compare_size_same(old_tex_path, tex_path):
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


def new_element(obj, cobj, attr_name, ops: None|bpy.types.Operator=None):
    '''New an element of bpy_prop_collection by new() function in blender
    
    - obj: bpy prop collection
    - cattr: An element of the collection, will be used as new()'s input parameter
    - attr_name: Attributs' name, will be used to find what new() to use'''
    def new(*parameter):
        getattr(obj, "new")(*parameter)
    # XXX it's weak. we should use some other way to specify it. maybe need to add an attr_owner... or may be the type of obj (this is right, we should use type)
    
    # i forgot what this is...
    if attr_name == "elements":
        new(cobj["position"])
    # curve[i].points, for curvemap
    elif attr_name == "points":
        new(cobj["location"][0], cobj["location"][1])
    elif attr_name == "enum_items":
        new(cobj["name"])
        
        
def try_setattr(obj, cobj, attr, cvalue, ops: None|bpy.types.Operator=None, invoker: str|int|None=None):
    '''setattr with try catch. When debug, use setattr directly to find out bugs, rather than try catch.'''
    try:
        setattr(obj, attr, cvalue)
    # Setting Read-only attr may cause this
    except AttributeError as e:
        # read-only usually wont cause any problem...
        if "read-only" not in e.args[0]:
            report(ops, {'WARNING'}, i18n.msg["rpt_warning_setter_soft_error_universal"])
            print(invoker)
            print(f"Hot Node Setter AttributeError: Attribute \"{attr}\" can't be set to the object {obj}, the cvalue is: {cvalue}. Node type: {current_node_bl_idname}, Node name \"{current_node_name}\".")
    # Set an unexist enum item to a enum socket may cause this
    except TypeError as e:
        # 1. Edge case: Menu Node linked to the group io will have a "" default_value but it's fine.
        # 2. Group IO's menu default_value is depend on the Menu Node, but when setting the IO, the Menu Node is not be created yet.
        if isinstance(obj, bpy.types.NodeSocketMenu) and attr == "default_value":
            pass
        # Imgae Format Settings' color_mode and color_depth enum items is depended on file_format, so we set file_format first.
        elif isinstance(obj, bpy.types.ImageFormatSettings) and isinstance(cvalue, str):
            setattr(obj, "file_format", cobj.get("file_format", "PNG"))
            setattr(obj, attr, cvalue)
        else:
            report(ops, {'WARNING'}, i18n.msg["rpt_warning_setter_soft_error_universal"])
            print(invoker)
            # BUG bpy.types.ImageFormatSettings.view_settings.look's enum item name can't match the exact name in the enum_items, e.g. High Contrast v.s. AgX - High Contrast 
            # items = obj.bl_rna.properties["look"].enum_items
            # for item in items:
            #     print(item.identifier)
            # print(e)
            print(f"Hot Node Setter TypeError: Attribute \"{attr}\" can't be set to the object {obj}, the cvalue is: {cvalue}. Node type: {current_node_bl_idname}, Node name \"{current_node_name}\".")
    # Set float to Vector may cause this (blender record 0.0x4 as 0.0?)
    except ValueError:
        if hasattr(obj, attr):
            import mathutils
            obj_attr = getattr(obj, attr)
            if isinstance(cvalue, float) and isinstance(obj_attr, (mathutils.Vector, 
                                                                   mathutils.Euler, 
                                                                   mathutils.Color, 
                                                                   bpy.types.bpy_prop_array)):
                cvalue = len(obj_attr) * [cvalue]
                setattr(obj, attr, cvalue)
            else:
                # XXX for the preset saved by 0.7.2 or before, reroute's i/o default value make this warning (but everything is fine).
                if current_node_bl_idname != "NodeReroute":
                    report(ops, {'WARNING'}, i18n.msg["rpt_warning_setter_soft_error_universal"])
                    print(invoker)
                    print(f"Hot Node Setter ValueError: Attribute \"{attr}\" can't be set to the object {obj}, the cvalue is: {cvalue}. Node type: {current_node_bl_idname}, Node name \"{current_node_name}\".")
        else:
            report(ops, {'WARNING'}, i18n.msg["rpt_warning_setter_soft_error_universal"])
            print(invoker)
            print(f"Hot Node Setter ValueError: object {obj} do not have attribute \"{attr}\". Node type: {current_node_bl_idname}, Node name: \"{current_node_name}\".")
    except Exception as e:
        report(ops, {'ERROR'}, i18n.msg["rpt_error_setter_universal"])
        print(invoker)
        print_error(e, current_node_bl_idname, obj, cobj, attr)


def set_attrs_direct(obj, cobj, *attr_names: str):
    '''Set obj's attributes by given attr_names.
    
    - obj: The object to set it's attributes.
    - cattrs: The object's mirror in hot node data json format.'''
    for attr in attr_names:
        try_setattr(obj, cobj, attr, cobj[attr], invoker=335)
    cobj["HN_ref"] = obj


def set_attrs(obj, cobj, attr_name: str=None, attr_owner=None, ops: None|bpy.types.Operator=None):
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
    # if set_special is not None:
    #     set_special(obj, cobj)
    if isinstance(cobj, list):
        length = len(obj)
        clength = len(cobj)
        max_HN_idx = cobj[clength - 1]["HN_idx"]
        if length == clength:
            for i in range(clength):
                set_attrs(obj[i], cobj[i], attr_name=attr_name, ops=ops)
        elif length < clength:
            # may be the new node should append list manually, like curve[i].points, simulationInputs, etc. here we do this.
            for i in range(clength):
                if i >= length:
                    new_element(obj, cobj[i], attr_name)
                try:
                    set_attrs(obj[i], cobj[i], attr_name=attr_name, ops=ops)
                except IndexError as e:
                    report(ops, {'ERROR'}, i18n.msg["rpt_error_setter_universal"] + " (Index Error)")
                    print_error(e, current_node_bl_idname, obj, cobj, attr_name)
                except Exception as e:
                    report(ops, {'ERROR'}, i18n.msg["rpt_error_setter_universal"])
                    print_error(e, current_node_bl_idname, obj, cobj, attr_name)
        # XXX This branch solves the Risk below, and it's a universal way for node that has custom sockets. 
        # XXX but im not sure is it safe... because there are too many uncertain things in new() progress...
        # elif length < max_HN_idx + 1:
        #     for cvalue in cobj:
        #         HN_idx = cvalue["HN_idx"]
        #         if HN_idx > length - 1:
        #             new_element(obj, cvalue, attr_name)
        #             length += 1
        #         if HN_idx < length:
        #             set_attrs(obj[HN_idx], cvalue, attr_name=attr_name)
        else:
            # length > clength, for when we only recorded part of the list
            # TODO Risk: if max HN_idx actually is bigger than the length, but clength is lower...
            # NOTE This Risk will be solved by the special logic in set_nodes() because we will create the needed items first.
            for i in range(clength):
                HN_idx = cobj[i]["HN_idx"]
                # we may recorded a virtual input whose idx is bigger than the length, but we dont need to set it.
                if HN_idx < length:
                    set_attrs(obj[cobj[i]["HN_idx"]], cobj[i], attr_name=attr_name, ops=ops)
    elif isinstance(cobj, dict):
        for attr, cvalue in cobj.items():
            if attr in black_attrs or attr.startswith("HN_"):
                continue
            elif isinstance(cvalue, list) and not check_common(cvalue):
                sub_obj = getattr(obj, attr)
                set_attrs(sub_obj, cobj[attr], attr_name=attr, attr_owner=obj, ops=ops)
            elif isinstance(cvalue, dict) and not check_common(cvalue.values()):
                sub_obj = getattr(obj, attr)
                set_attrs(sub_obj, cobj[attr], attr_name=attr, attr_owner=obj, ops=ops)
            else:
                # BUG sometimes (often after Ctrl + G and the node group interface is autoly created) tree interface socket's subtype is "", 
                # but it is supposed to be 'NONE'. maybe a blender bug? here we check this to avoid TypeError except.
                if attr == "subtype" and cvalue == "":
                    cvalue = 'NONE'
                # XXX [TEMP SOLUTION] To help handle socket defination order in node group interface, we set the default_value of the socket menu in late setter.
                elif isinstance(obj, bpy.types.NodeTreeInterfaceSocketMenu) and attr == "default_value":
                    global late_setter_funcs
                    def socket_menu_solver(params):
                        obj, attr, cvalue = params
                        try_setattr(obj, cobj, attr, cvalue, ops=ops, invoker=412)
                    late_setter_funcs.append((socket_menu_solver, (obj, attr, cvalue)))
                    continue
                try_setattr(obj, cobj, attr, cvalue, ops, invoker=415)
        cobj["HN_ref"] = obj
    elif attr_name not in black_attrs:
        obj = cobj

        
def set_interface(interface: bpy.types.NodeTreeInterface, cinterface, ops: None|bpy.types.Operator=None):
    interface.clear()
    clength = len(cinterface)
    panels_citems = []
    child_parent_pairs = []
    # dont know why, after we newed all the items, their index will change. so we store references.
    for i in range(clength):
        citem = cinterface[i]
        name = citem["name"]
        # set "" to the socket name will crash blender, so we set it to "UNNAMED"
        if name == "":
            citem["name"] = "UNNAMED"
            name = "UNNAMED"
        item_type = citem["item_type"]
        # invoke new() to create item
        if item_type == 'SOCKET':
            in_out = citem["in_out"]
            socket_type = citem["socket_type"]
            item = interface.new_socket(name, in_out=in_out, socket_type=socket_type)
        elif item_type == 'PANEL':
            item = interface.new_panel(name)
            panels_citems.append((item, citem))
        # get ref
        citem["HN_ref"] = item
        
        # move position (order)
        interface.move(item, citem["position"])
            
        # set item attributes
        set_attrs(item, citem, ops=ops)
        
        # get parent relations
        if citem["HN_parent_idx"] != -1:
            child_parent_pairs.append((item, citem["HN_parent_idx"], citem["position"]))
    
    # set item parent
    for item, HN_parent_idx, to_position in child_parent_pairs:
        interface.move_to_parent(item, cinterface[HN_parent_idx]["HN_ref"], to_position)
        
    # putting items into the panel makes the panel go to the top of the interface, 
    # so we set the panel's position again after all items are created
    for panel, citem in panels_citems:
        interface.move(panel, citem["position"])
        
def set_nodes(node_tree, nodes, cnodes, cnode_trees, node_offset=Vector((0.0, 0.0)), set_tree_io=False, ops: None|bpy.types.Operator=None):
    global failed_tex_num
    global current_node_bl_idname
    global current_node_name
    global current_cnode
    node_cnode_attr_ref2nodenames = []
    later_setup_cnodes = {}
    for cnode in cnodes.values():
        bl_idname = cnode["bl_idname"]
        current_node_bl_idname = bl_idname
        current_node_name = cnode["name"]
        current_cnode = cnode
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
            if cnode.get("HN_nt_name", None) is not None:
                ref_node_tree = cnode_trees[cnode["HN_nt_name"]]["HN_ref"]
                if node_tree != ref_node_tree:
                    node.node_tree = ref_node_tree
                # nesting a node group inside of itself is not allowed
                else:
                    set_attrs_direct(node, cnode, "bl_idname", "name", "location")
                    ops.report({'WARNING'}, i18n.msg["rpt_warning_setter_ng_nesting"].format(tree_name=node_tree.name))
                    continue
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
        # TODO more beautiful...
        # All items, especially sockets, should be newed here, and set later
        elif bl_idname == "GeometryNodeSimulationOutput":
            # node.state_items.clear()
            cstate_items = cnode.get("state_items", [])
            clength = len(cstate_items)
            max_HN_idx = cstate_items[clength - 1]["HN_idx"] if clength > 0 else 0
            # HACK idx 0 is a build-in geometry socket, skip it
            for i in range(1, max_HN_idx + 1):
            # for i in range(0, max_HN_idx + 1):
                # if citem is not the default one, it will always be recorded by our parser logic, 
                # so dont worry about citems dont have idx i, only idx 0 may not be recorded.
                citem = cstate_items[i]
                node.state_items.new(citem["socket_type"], citem["name"])
        elif bl_idname == "GeometryNodeRepeatOutput":
            # node.repeat_items.clear()
            crepeat_items = cnode.get("repeat_items", [])
            clength = len(crepeat_items)
            max_HN_idx = crepeat_items[clength - 1]["HN_idx"] if clength > 0 else 0
            # HACK idx 0 is a build-in geometry socket, skip it
            for i in range(1, max_HN_idx + 1):
            # for i in range(0, max_HN_idx + 1):
                # if citem is not the default one, it will always be recorded by our parser logic, 
                # so dont worry about citems dont have idx i, only idx 0 may not be recorded.
                citem = crepeat_items[i]
                # node.repeat_items.new(citem["socket_type"], citem["name"])
                node.repeat_items.new(citem["socket_type"], citem["name"])
        elif bl_idname == "GeometryNodeCaptureAttribute":
            capture_items = cnode.get("capture_items", [])
            for citem in capture_items:
                node.capture_items.new(citem["HN_socket_type"], citem["name"])
        elif bl_idname == "GeometryNodeBake":
            # node.bake_items.clear()
            cbake_items = cnode.get("bake_items", [])
            clength = len(cbake_items)
            max_HN_idx = cbake_items[clength - 1]["HN_idx"] if clength > 0 else 0
            for i in range(1, max_HN_idx + 1):
                # node.bake_items.new(citem["socket_type"], citem["name"])
                # citems may dont have idx i (default cull), so new the item but set it later
                node.bake_items.new('BOOLEAN', "")
        # set by pairring output
        elif bl_idname in ("GeometryNodeSimulationInput", "GeometryNodeRepeatInput"):
            later_setup_cnodes[cnode['name']] = (node, cnode)
            continue
        # FIXME less than default...
        elif bl_idname == "GeometryNodeMenuSwitch":
            cenum_items = cnode.get("enum_items", None)
            if cenum_items is not None:
                node.enum_items.clear()
                clength = len(cenum_items)
                max_HN_idx = cenum_items[clength - 1]["HN_idx"] if clength > 0 else 0
                # inputs idx 0, 1 are enum items that is created by default, skip them
                for i in range(2, max_HN_idx + 1):
                # for i in range(0, max_HN_idx + 1):
                    node.enum_items.new("")
        elif bl_idname == "GeometryNodeIndexSwitch":
            cindex_switch_items = cnode.get("index_switch_items", None)
            if cindex_switch_items is not None:
                clength = len(cindex_switch_items)
                max_HN_idx = cindex_switch_items[clength - 1]["HN_idx"] if clength > 0 else 0
                # inputs idx 0, 1 are enum items that is created by default, skip them
                for i in range(2, max_HN_idx + 1):
                    node.index_switch_items.new()
        elif bl_idname == "CompositorNodeOutputFile":
            cfile_slots = cnode.get("file_slots", [])
            clength = len(cfile_slots)
            max_HN_idx = cfile_slots[clength - 1]["HN_idx"] if clength > 0 else 0
            # idx 1 is a file slot that is created by default, skip it
            for i in range(1, max_HN_idx + 1):
                node.file_slots.new("")
        
        # set attributes, io sockets
        set_attrs(node, cnode, ops=ops)
            
    # Set Referenced Nodes to The Nodes refering to them
    for node, cnode, attr, ref2_node_name in node_cnode_attr_ref2nodenames:
        current_node_bl_idname = node.bl_idname
        cref2_node = cnodes.get(ref2_node_name, None)
        if cref2_node is not None:
            if attr == "paired_output":
                node.pair_with_output(cnodes[ref2_node_name]["HN_ref"])
            # for parent NodeFrames, set parent location means change all sons' locations
            else:
                node.location = Vector(cnode["location"]) + node_offset
                try_setattr(node, cnode, attr, cnodes[ref2_node_name]["HN_ref"], ops, invoker=597)
        # dont have paired output in our data, remove input in late set list
        elif attr == "paired_output":
            # node.location = Vector(cnode["location"]) + node_offset
            del later_setup_cnodes[cnode["name"]]
        
    # Late Attribute Set, for nodes refering to another node
    for node, cnode in later_setup_cnodes.values():
        current_node_bl_idname = node.bl_idname
        set_attrs(node, cnode, ops=ops)
        
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
        
        
def set_links(node_tree, links, clinks, cnodes, link_group_io=True, ops: None|bpy.types.Operator=None):
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
            

def set_node_tree(node_tree: bpy.types.NodeTree, cnode_tree, cnode_trees, node_offset=Vector((0.0, 0.0)), set_tree_io=False, link_group_io=True, ops: None|bpy.types.Operator=None):
    global failed_tex_num
    nodes = node_tree.nodes
    links = node_tree.links
    interface = node_tree.interface
    
    # Deselect Nodes
    for node in nodes:
        node.select = False
        
    # Setup Tree Interface if there are group io nodes in the preset or it's a ng
    if set_tree_io:
        set_interface(interface, cnode_tree["interface"], ops=ops)
            
    cnodes = cnode_tree["nodes"]
    # Generate Nodes & Set Node Attributes & Set IO Socket Value
    set_nodes(node_tree, nodes, cnodes, cnode_trees, node_offset=node_offset, set_tree_io=set_tree_io, ops=ops)

    # Generate Links
    set_links(node_tree, links, cnode_tree['links'], cnodes, link_group_io=link_group_io, ops=ops)
    
    # Late Setter
    # try:
    for func, params in late_setter_funcs:
        func(params)
    # except:
    #     print(f"Hot Node Setter Error: Late Setter Function {func} failed.")
    late_setter_funcs.clear()
            

def apply_preset(context: bpy.types.Context, preset_name: str, pack_name="", apply_offset=False, new_tree=False, ops: None|bpy.types.Operator=None):
    '''Set nodes for the current edit tree'''
    global failed_tex_num
    failed_tex_num = 0
    space_data = context.space_data
    node_groups = bpy.data.node_groups
    # maybe cdata, but we call it cnode_trees
    cnode_trees = file.load_preset(preset_name, pack_name=pack_name)
    cnode_trees = versioning.ensure_preset_version(preset_name, cnode_trees)
    cdata = cnode_trees["HN_preset_data"]
    
    # Generate Node Groups
    for cname, cnode_tree in cnode_trees.items():
        if cname in ("HN_edit_tree", "HN_preset_data"):
            continue
        # XXX The ideal way is to compare all the ngs that have the same name body and reuse the same one no matter what the suffix is.
        # XXX but, the ng name can't pass the compare. so for now, we just compare the one with the same name.
        # # commpare exist tree with the same name body
        # cname_body, cint_suffix = utils.split_name_suffix(cname)
        # if cint_suffix == 0:
        #     # compare all the ngs that has a cname like body and blender style rename suffix, like cname.001
        #     # BUG sometimes the setted ng wont be same as the ng in the preset, so the ng actually will always be created...
        #     # XXX the attr "identifier" of the node group socket items like "SOCKET_2" may cause this bug
        #     found_same = False
        #     for full_name in node_groups.keys():
        #         name, int_suffix = utils.split_name_suffix(full_name)
        #         if name == cname:
        #             cexist_tree, _ = node_parser.parse_node_tree(node_groups[full_name], parse_all=True)
        #             if compare_same(cexist_tree, cnode_tree, ignore_attr_owners=(("location", "", "nodes"), )):
        #                 cnode_tree["HN_ref"] = node_groups[full_name]
        #                 found_same = True
        #                 break
        #     if found_same:
        #         continue
        # # if preset it self has suffix, just compare the one with the same suffix
        # else:
        
        # compare and reuse the same tree
        if node_groups.find(cname) != -1:
            # BUG ngs with node "Gamma" cant pass the compare, it's a blender bug maybe, it throws a warning:
            # WARN (bpy.rna): C:\Users\blender\git\blender-v420\blender.git\source\blender\python\intern\bpy_rna.cc:1366 pyrna_enum_to_py: current value '13' matches no enum in 'NodeTreeInterfaceSocketFloat', 'Gamma', 'subtype'
            cexist_tree, _ = node_parser.parse_node_tree(node_groups[cname], parse_all=True)
            # reuse the same tree
            if compare_same(cexist_tree, cnode_tree, ignore_attr_owners=(("location", "", "nodes"), )):
                cnode_tree["HN_ref"] = node_groups[cname]
                continue
        # didnt find the same tree, create one
        cname = utils.ensure_unique_name(cname, -1, node_groups.keys())
        node_tree = node_groups.new(cname, cnode_tree["bl_idname"])
        cnode_tree["HN_ref"] = node_tree
        set_node_tree(node_tree, cnode_tree, cnode_trees, set_tree_io=True, ops=ops)
        
    # Generate Main Node Tree to a new tree
    if new_tree:
        cname = cnode_trees["HN_preset_data"]["preset_name"]
        tree_type = cdata["tree_type"]
        edit_tree = node_groups.new(cname, tree_type)
        if tree_type == "GeometryNodeTree":
            nodes_modifier = context.active_object.modifiers.new(name=cname, type='NODES')
            nodes_modifier.node_group = edit_tree
            nodes_modifier.name = edit_tree.name
    # Generate Main Node Tree To Current Editing Tree
    else:
        edit_tree = space_data.edit_tree
    cedit_interface = node_parser.parse_interface(edit_tree)
    if new_tree:
        if check_group_io_node(cnode_trees["HN_edit_tree"]["nodes"]):
            set_tree_io = True
            link_group_io = True
        else:
            set_tree_io = False
            link_group_io = False
    # if is base node tree, skip setting io for trees except geo tree
    elif edit_tree is space_data.node_tree and edit_tree.bl_idname != "GeometryNodeTree":
        set_tree_io = False
        link_group_io = False
    elif cnode_trees["HN_edit_tree"].get("interface", None) is not None:
        # if the existing tree interface is capatibale with our preset, just use it
        if compare_same(cedit_interface, cnode_trees["HN_edit_tree"]["interface"]):
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
    else:
        set_tree_io = False
        link_group_io = True
    if apply_offset and not new_tree:
        cnode_center = cnode_trees["HN_preset_data"]["node_center"]
        cursor_location = space_data.cursor_location
        node_offset = cursor_location - Vector(cnode_center)
    else:
        node_offset = Vector((0.0, 0.0))
    set_node_tree(edit_tree, cnode_trees["HN_edit_tree"], cnode_trees, node_offset=node_offset, set_tree_io=set_tree_io, link_group_io=link_group_io, ops=ops)
    
    return failed_tex_num