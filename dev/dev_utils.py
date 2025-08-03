import bpy
import json

from ..utils import constants

def add_all_nodes_to_edit_tree(context=None):
    """
    Add all kind of nodes of the current edit tree to the current edit tree.
    This function will automatically detect the current edit tree type.
    """
    # get current edit tree
    edit_tree = bpy.context.space_data.edit_tree
    edit_tree_type_name = edit_tree.bl_idname if edit_tree else None
    new_nodes = []
    
    if not edit_tree_type_name:
        print("HotNode: No edit tree found.")
        return
    
    # get tree node type name (ShaderNode, GeometryNode, ...) of edit_tree
    for tree_node_type_name in constants.TREE_NODE_IDNAMES: # ShaderNode, GeometryNode, CompositorNode, ...
        if tree_node_type_name in edit_tree_type_name:
            break
    # get tree node type (bpy.types.ShaderNode, ...)
    for tree_node_type in bpy.types.NodeInternal.__subclasses__():
        if tree_node_type_name == tree_node_type.__name__:
            break
    # new all nodes of tree_node_type to avoid lazy load
    for node_type_name in dir(bpy.types):
        if tree_node_type_name in node_type_name:
        # if node_type_name.startswith(tree_node_type_name):
            try:
                new_nodes.append(edit_tree.nodes.new(type=node_type_name))
            except RuntimeError:
                # some nodes may not be created directly, skip these nodes
                pass

    node_types = tree_node_type.__subclasses__()
    print(f"HotNode: {len(node_types)} node types found in {edit_tree_type_name}.")
    print([node.bl_rna.identifier for node in node_types])
    
    arrange_nodes_loc(new_nodes, padding_x=10, padding_y=10)
    
    return new_nodes

import bpy

def arrange_nodes_loc(nodes: list[bpy.types.Node], padding_x: float = 5, padding_y: float = 5):
    """
    Arrange nodes in a grid layout with specified padding.

    :param nodes: List of nodes to arrange.
    :param padding_x: Horizontal padding between nodes.
    :param padding_y: Vertical padding between nodes.
    """
    if not nodes:
        return

    current_x = 0
    current_y = 0

    col_idx = 0
    nodes_by_width = {}
    nodes_widths_str = nodes_by_width.keys()
    
    for node in nodes:
        node_width_str = str(node.width)
        if not node_width_str in nodes_widths_str:
            nodes_by_width[node_width_str] = []
            col_idx += 1
        nodes_by_width[node_width_str].append(node)
            
            
    # TODO reget selected nodes to update the height
    # TODO use color to filter
    for width, nodes in nodes_by_width.items():
        for node in nodes:
            # Set node location
            node.location = (current_x, current_y)

            # Update current row width and height
            current_y += node.bl_height_default + padding_y

            # If exceeding a certain width (e.g., 2000), wrap to the next line
            if current_y > 1000:
                current_y = 0
                current_x += node.width + padding_x
                
        # wrap to the next line for next width group
        current_y = 0
        current_x += node.width + padding_x