import copy
import math
import traceback
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable

import bpy
import mathutils

from ..core.serialization.manager import SerializationManager
from ..core.serialization.serialize import serializer as serializer_module
from ..core.serialization.deserialize import deserializer as deserializer_module


@dataclass(frozen=True)
class RoundTripCase:
    name: str
    tree_type: str
    build: Callable[[bpy.types.NodeTree], None]
    compare_layout: bool = True


@dataclass
class RoundTripResult:
    name: str
    passed: bool
    messages: list[str] = field(default_factory=list)
    traceback_text: str = ""


@dataclass
class RoundTripReport:
    results: list[RoundTripResult]

    @property
    def passed(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed

    def format(self) -> str:
        lines = [f"Hot Node semantic round trips: {self.passed} passed, {self.failed} failed"]
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"[{status}] {result.name}")
            lines.extend(f"  - {message}" for message in result.messages)
            if result.traceback_text:
                lines.append(result.traceback_text.rstrip())
        return "\n".join(lines)


class TestPreferences:
    node_tree_reuse_mode = 'ALWAYS_NEW'
    is_overwrite_tree_io = True
    dir_to_match_image = ""
    image_name_filter = ""


class NodeSemanticRoundTripTester:
    def __init__(self, bl_context=None, keep_trees=False):
        self.bl_context = bl_context or bpy.context
        self.manager = SerializationManager()
        self.test_prefs = TestPreferences()
        self.created_trees: list[bpy.types.NodeTree] = []
        self.keep_trees = keep_trees
        self.visual_trees: list[bpy.types.NodeTree] = []

    def run_all(self) -> RoundTripReport:
        self.visual_trees = []
        results = [self.run_case(case) for case in default_cases()]
        report = RoundTripReport(results)
        print(report.format())
        return report

    def run_case(self, case: RoundTripCase) -> RoundTripResult:
        trees_before = {tree.as_pointer() for tree in bpy.data.node_groups}
        self.created_trees = []
        source = self.new_tree(f"HN@RT SRC {case.name}", case.tree_type)
        destination = self.new_tree(f"HN@RT DST {case.name}", case.tree_type)
        original_get_ser_prefs = serializer_module.utils.get_user_prefs
        original_get_deser_prefs = deserializer_module.utils.get_user_prefs
        serializer_module.utils.get_user_prefs = lambda _context=None: self.test_prefs
        deserializer_module.utils.get_user_prefs = lambda _context=None: self.test_prefs

        try:
            case.build(source)
            fixture_tree_names = {
                node.node_tree.name
                for node in source.nodes
                if getattr(node, "node_tree", None) is not None
            }
            for tree_name in fixture_tree_names:
                tree = bpy.data.node_groups.get(tree_name)
                if tree is not None and tree not in self.created_trees:
                    self.created_trees.append(tree)
            for node in source.nodes:
                node.select = True

            source_snapshot = semantic_tree_snapshot(source)
            self.reset_strategy_state()
            jpreset = self.manager.serialize_preset(self.make_context(source), source)
            self.reset_strategy_state()
            self.manager.deserialize_preset(
                self.make_context(destination),
                copy.deepcopy(jpreset),
                destination,
                is_add_nodes_to_new_tree=True,
            )
            for tree in bpy.data.node_groups:
                if tree.as_pointer() not in trees_before and tree not in self.created_trees:
                    self.created_trees.append(tree)
            destination_snapshot = semantic_tree_snapshot(destination)
            messages = compare_semantics(source_snapshot, destination_snapshot, case.compare_layout)
            if self.keep_trees:
                source.name = f"HN RT {case.name} SOURCE"
                destination.name = f"HN RT {case.name} RESTORED"
                self.visual_trees.extend((source, destination))
            return RoundTripResult(case.name, not messages, messages)
        except Exception as exception:
            return RoundTripResult(
                case.name,
                False,
                [f"{type(exception).__name__}: {exception}"],
                traceback.format_exc(),
            )
        finally:
            serializer_module.utils.get_user_prefs = original_get_ser_prefs
            deserializer_module.utils.get_user_prefs = original_get_deser_prefs
            if not self.keep_trees:
                for tree in reversed(self.created_trees):
                    if tree.name in bpy.data.node_groups:
                        bpy.data.node_groups.remove(tree)

    def show_visual_tree(self):
        if not self.visual_trees:
            return None
        tree = next((tree for tree in self.visual_trees if tree.name.endswith("RESTORED")), self.visual_trees[0])
        space = getattr(self.bl_context, "space_data", None)
        if isinstance(space, bpy.types.SpaceNodeEditor):
            space.tree_type = tree.bl_idname
            space.pin = True
            space.path.start(tree)
            for node in tree.nodes:
                node.select = True
            tree.nodes.active = next(iter(tree.nodes), None)
        return tree

    def reset_strategy_state(self):
        self.manager.ser_stgs.node_tree.parse_all = False
        self.manager.ser_stgs.node_tree.is_main_tree = False
        self.manager.ser_stgs.nodes.parse_all = False
        self.manager.ser_stgs.links.parse_all = False
        self.manager.deser_stgs.node_tree.is_set_tree_io = False
        self.manager.deser_stgs.node_links.is_link_group_io = False

    def new_tree(self, name: str, tree_type: str):
        tree = bpy.data.node_groups.new(name, tree_type)
        self.created_trees.append(tree)
        return tree

    def make_context(self, tree):
        space = SimpleNamespace(
            edit_tree=tree,
            node_tree=tree,
            cursor_location=mathutils.Vector((0.0, 0.0)),
        )
        return SimpleNamespace(space_data=space, active_object=None)


def clear_visual_roundtrip_trees():
    for tree in list(bpy.data.node_groups):
        if tree.name.startswith(("HN RT ", "HN@RT ")):
            bpy.data.node_groups.remove(tree)


def normalize_value(value):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (int, bool, str)) or value is None:
        return value
    if isinstance(value, (mathutils.Vector, mathutils.Color, mathutils.Euler, mathutils.Quaternion)):
        return tuple(round(component, 6) for component in value)
    if isinstance(value, bpy.types.ID):
        return (value.__class__.__name__, value.name)
    if isinstance(value, bpy.types.bpy_struct):
        return (
            value.__class__.__name__,
            getattr(value, "name", None),
            getattr(value, "identifier", None),
        )
    try:
        return tuple(round(float(component), 6) for component in value)
    except (TypeError, ValueError):
        return str(value)


def writable_properties(obj, excluded=()):
    result = {}
    for prop in obj.bl_rna.properties:
        name = prop.identifier
        if name in excluded or name == "rna_type" or prop.is_readonly or prop.type == 'COLLECTION':
            continue
        try:
            result[name] = normalize_value(getattr(obj, name))
        except Exception:
            continue
    return result


def socket_snapshot(socket, index):
    result = {
        "index": index,
        "name": socket.name,
        "bl_idname": socket.bl_idname,
        "is_multi_input": socket.is_multi_input,
    }
    if hasattr(socket, "default_value"):
        try:
            result["default_value"] = normalize_value(socket.default_value)
        except Exception:
            pass
    return result


def collection_snapshot(collection):
    items = []
    for item in collection:
        item_data = writable_properties(
            item,
            excluded=("name", "identifier", "socket_type", "index", "position"),
        )
        item_data.update({
            "type": item.__class__.__name__,
            "name": getattr(item, "name", None),
            "identifier": getattr(item, "identifier", None),
            "socket_type": getattr(item, "socket_type", None),
        })
        items.append(item_data)
    return items


def interface_snapshot(tree):
    if not hasattr(tree, "interface"):
        return []
    items = []
    for item in tree.interface.items_tree:
        data = writable_properties(
            item,
            excluded=("name", "identifier", "socket_type", "item_type", "index", "position"),
        )
        data.update({
            "item_type": item.item_type,
            "name": item.name,
            "socket_type": getattr(item, "socket_type", None),
            "in_out": getattr(item, "in_out", None),
            "parent": item.parent.name if item.parent else None,
        })
        items.append(data)
    return items


def node_role(node):
    return node.label or node.name


def semantic_tree_snapshot(tree):
    nodes = {}
    for node in tree.nodes:
        role = node_role(node)
        collections = {}
        for prop in node.bl_rna.properties:
            if prop.type != 'COLLECTION' or prop.identifier in ("inputs", "outputs", "internal_links"):
                continue
            try:
                collections[prop.identifier] = collection_snapshot(getattr(node, prop.identifier))
            except Exception:
                continue

        nodes[role] = {
            "bl_idname": node.bl_idname,
            "properties": writable_properties(
                node,
                excluded=(
                    "name", "label", "location", "location_absolute", "select", "dimensions",
                    "type", "bl_idname", "parent", "node_tree", "ui_short_label",
                ),
            ),
            "location": normalize_value(node.location_absolute),
            "parent": node_role(node.parent) if node.parent else None,
            "paired_output": node_role(node.paired_output) if getattr(node, "paired_output", None) else None,
            "inputs": [socket_snapshot(socket, index) for index, socket in enumerate(node.inputs)],
            "outputs": [socket_snapshot(socket, index) for index, socket in enumerate(node.outputs)],
            "collections": collections,
            "node_tree": node.node_tree.bl_idname if getattr(node, "node_tree", None) else None,
            "node_tree_interface": interface_snapshot(node.node_tree) if getattr(node, "node_tree", None) else None,
        }

    links = []
    for link in tree.links:
        links.append({
            "from_node": node_role(link.from_node),
            "from_socket": socket_key(link.from_node.outputs, link.from_socket),
            "to_node": node_role(link.to_node),
            "to_socket": socket_key(link.to_node.inputs, link.to_socket),
            "is_valid": link.is_valid,
        })
    links.sort(key=lambda link: str(link))

    return {
        "tree_type": tree.bl_idname,
        "interface": interface_snapshot(tree),
        "nodes": nodes,
        "links": links,
    }


def socket_key(sockets, socket):
    index = next(index for index, candidate in enumerate(sockets) if candidate == socket)
    return {
        "name": socket.name,
        "bl_idname": socket.bl_idname,
        "index": index,
    }


def compare_semantics(expected, actual, should_compare_layout=True):
    messages = []
    if expected["tree_type"] != actual["tree_type"]:
        messages.append(f"tree type: expected {expected['tree_type']}, got {actual['tree_type']}")
    if expected["interface"] != actual["interface"]:
        messages.append("tree interface differs")

    expected_roles = set(expected["nodes"])
    actual_roles = set(actual["nodes"])
    if expected_roles != actual_roles:
        messages.append(f"node roles differ: missing={sorted(expected_roles - actual_roles)}, extra={sorted(actual_roles - expected_roles)}")

    common_roles = sorted(expected_roles & actual_roles)
    for role in common_roles:
        compare_node(
            role,
            expected["nodes"][role],
            actual["nodes"][role],
            messages,
        )

    if should_compare_layout:
        compare_layout(expected["nodes"], actual["nodes"], common_roles, messages)

    if expected["links"] != actual["links"]:
        messages.append(f"links differ: expected={expected['links']}, actual={actual['links']}")
    return messages


def compare_node(role, expected, actual, messages):
    for key in ("bl_idname", "parent", "paired_output", "node_tree", "node_tree_interface"):
        if expected[key] != actual[key]:
            messages.append(f"{role}.{key}: expected {expected[key]!r}, got {actual[key]!r}")
    if expected["properties"] != actual["properties"]:
        messages.append(f"{role}.properties differ: {dict_diff(expected['properties'], actual['properties'])}")
    if expected["inputs"] != actual["inputs"]:
        messages.append(f"{role}.inputs differ: expected={expected['inputs']}, actual={actual['inputs']}")
    if expected["outputs"] != actual["outputs"]:
        messages.append(f"{role}.outputs differ: expected={expected['outputs']}, actual={actual['outputs']}")
    if expected["collections"] != actual["collections"]:
        messages.append(f"{role}.collections differ: expected={expected['collections']}, actual={actual['collections']}")


def compare_layout(expected_nodes, actual_nodes, roles, messages):
    for index, left_role in enumerate(roles):
        for right_role in roles[index + 1:]:
            expected_delta = vector_delta(
                expected_nodes[left_role]["location"],
                expected_nodes[right_role]["location"],
            )
            actual_delta = vector_delta(
                actual_nodes[left_role]["location"],
                actual_nodes[right_role]["location"],
            )
            if not vector_close(expected_delta, actual_delta):
                messages.append(
                    f"layout {left_role}->{right_role}: expected {expected_delta}, got {actual_delta}"
                )


def vector_delta(left, right):
    return tuple(round(right[index] - value, 6) for index, value in enumerate(left))


def dict_diff(expected, actual):
    keys = set(expected) | set(actual)
    return {
        key: (expected.get(key), actual.get(key))
        for key in sorted(keys)
        if expected.get(key) != actual.get(key)
    }


def vector_close(expected, actual, tolerance=1e-4):
    if not isinstance(expected, tuple) or not isinstance(actual, tuple) or len(expected) != len(actual):
        return expected == actual
    return all(math.isclose(left, right, abs_tol=tolerance) for left, right in zip(expected, actual))


def add_node(tree, bl_idname, role, location):
    node = tree.nodes.new(bl_idname)
    node.label = role
    node.location = location
    return node


def build_shader_math(tree):
    value_a = add_node(tree, "ShaderNodeValue", "value-a", (-500, 120))
    value_a.outputs[0].default_value = 2.75
    value_b = add_node(tree, "ShaderNodeValue", "value-b", (-500, -80))
    value_b.outputs[0].default_value = -1.25
    math_node = add_node(tree, "ShaderNodeMath", "multiply-add", (-220, 80))
    math_node.operation = 'MULTIPLY_ADD'
    math_node.use_clamp = True
    math_node.inputs[2].default_value = 4.5
    map_range = add_node(tree, "ShaderNodeMapRange", "map-range", (80, 80))
    map_range.clamp = False
    map_range.interpolation_type = 'SMOOTHERSTEP'
    map_range.inputs[1].default_value = -2.0
    map_range.inputs[2].default_value = 8.0
    tree.links.new(value_a.outputs[0], math_node.inputs[0])
    tree.links.new(value_b.outputs[0], math_node.inputs[1])
    tree.links.new(math_node.outputs[0], map_range.inputs[0])


def build_frame_layout(tree):
    frame = add_node(tree, "NodeFrame", "frame", (-300, 100))
    frame.label_size = 28
    frame.shrink = False
    value = add_node(tree, "ShaderNodeValue", "framed-value", (40, 50))
    value.outputs[0].default_value = 6.25
    value.parent = frame
    reroute = add_node(tree, "NodeReroute", "reroute", (280, 50))
    tree.links.new(value.outputs[0], reroute.inputs[0])


def build_geometry_multi_input(tree):
    cube = add_node(tree, "GeometryNodeMeshCube", "cube", (-500, 120))
    grid = add_node(tree, "GeometryNodeMeshGrid", "grid", (-500, -100))
    join = add_node(tree, "GeometryNodeJoinGeometry", "join", (-120, 60))
    tree.links.new(cube.outputs[0], join.inputs[0])
    tree.links.new(grid.outputs[0], join.inputs[0])


def build_geometry_dynamic(tree):
    value = add_node(tree, "ShaderNodeValue", "switch-value", (-520, 220))
    value.outputs[0].default_value = 3.5
    switch = add_node(tree, "GeometryNodeSwitch", "switch", (-250, 220))
    switch.input_type = 'FLOAT'
    switch.inputs[0].default_value = True
    switch.inputs[1].default_value = 1.25
    tree.links.new(value.outputs[0], switch.inputs[2])

    geometry_switch = add_node(tree, "GeometryNodeSwitch", "geometry-switch", (-250, 80))
    geometry_switch.input_type = 'GEOMETRY'
    vector_switch = add_node(tree, "GeometryNodeSwitch", "vector-switch", (-250, -60))
    vector_switch.input_type = 'VECTOR'

    index_switch = add_node(tree, "GeometryNodeIndexSwitch", "index-switch", (40, 220))
    index_switch.data_type = 'FLOAT'
    index_switch.index_switch_items.new()
    index_switch.inputs[0].default_value = 2
    index_switch.inputs[1].default_value = 10.0
    index_switch.inputs[2].default_value = 20.0
    index_switch.inputs[3].default_value = 30.0
    tree.links.new(switch.outputs[0], index_switch.inputs[1])

    bundle = add_node(tree, "NodeCombineBundle", "bundle", (-250, -120))
    bundle.bundle_items.new('FLOAT', "Weight")
    bundle.bundle_items.new('VECTOR', "Direction")
    separate = add_node(tree, "NodeSeparateBundle", "separate", (40, -120))
    separate.bundle_items.new('FLOAT', "Weight")
    separate.bundle_items.new('VECTOR', "Direction")
    tree.links.new(bundle.outputs[0], separate.inputs[0])

    viewer_source = add_node(tree, "GeometryNodeInputIndex", "viewer-source", (340, -120))
    viewer = add_node(tree, "GeometryNodeViewer", "viewer", (600, -120))
    viewer_item = viewer.viewer_items.new('FLOAT', "Value")
    viewer_item.auto_remove = False
    tree.links.new(viewer_source.outputs[0], viewer.inputs[0])
    viewer_item.auto_remove = True



def build_geometry_group(tree):
    group_tree = bpy.data.node_groups.new("HN@RT Nested Geometry", "GeometryNodeTree")
    group_tree.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    scale_socket = group_tree.interface.new_socket("Scale", in_out='INPUT', socket_type='NodeSocketFloat')
    scale_socket.default_value = 1.75
    group_tree.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    group_input = add_node(group_tree, "NodeGroupInput", "nested-input", (-250, 0))
    group_output = add_node(group_tree, "NodeGroupOutput", "nested-output", (250, 0))
    group_tree.links.new(group_input.outputs[0], group_output.inputs[0])

    group = add_node(tree, "GeometryNodeGroup", "nested-group", (0, 0))
    group.node_tree = group_tree


def build_geometry_zones(tree):
    simulation_output = add_node(tree, "GeometryNodeSimulationOutput", "simulation-output", (0, 260))
    simulation_output.state_items.new('FLOAT', "Value")
    simulation_input = add_node(tree, "GeometryNodeSimulationInput", "simulation-input", (-320, 260))
    simulation_input.pair_with_output(simulation_output)
    simulation_input.inputs[1].default_value = 2.25
    tree.links.new(simulation_input.outputs[1], simulation_output.inputs[1])
    tree.links.new(simulation_input.outputs[2], simulation_output.inputs[2])

    repeat_output = add_node(tree, "GeometryNodeRepeatOutput", "repeat-output", (0, 0))
    repeat_output.repeat_items.new('FLOAT', "Value")
    repeat_input = add_node(tree, "GeometryNodeRepeatInput", "repeat-input", (-320, 0))
    repeat_input.pair_with_output(repeat_output)
    repeat_input.inputs[0].default_value = 7
    repeat_input.inputs[2].default_value = 4.75
    tree.links.new(repeat_input.outputs[1], repeat_output.inputs[0])
    tree.links.new(repeat_input.outputs[2], repeat_output.inputs[1])

    closure_output = add_node(tree, "NodeClosureOutput", "closure-output", (0, -280))
    closure_output.input_items.new('FLOAT', "Captured")
    closure_output.output_items.new('VECTOR', "Result")
    closure_input = add_node(tree, "NodeClosureInput", "closure-input", (-320, -280))
    closure_input.pair_with_output(closure_output)
    tree.links.new(closure_input.outputs[0], closure_output.inputs[0])


def build_geometry_menu(tree):
    menu = add_node(tree, "GeometryNodeMenuSwitch", "menu-switch", (0, 0))
    menu.data_type = 'INT'
    while len(menu.enum_items) > 0:
        menu.enum_items.remove(menu.enum_items[-1])
    menu.enum_items.new("Low")
    menu.enum_items.new("Medium")
    menu.enum_items.new("High")
    menu.inputs[0].default_value = "Medium"
    menu.inputs[1].default_value = 0
    menu.inputs[2].default_value = 1
    menu.inputs[3].default_value = 2

    index_switch = add_node(tree, "GeometryNodeIndexSwitch", "menu-index-switch", (260, 0))
    index_switch.data_type = 'FLOAT'
    index_switch.index_switch_items.new()
    index_switch.inputs[1].default_value = 0.25
    index_switch.inputs[2].default_value = 0.5
    index_switch.inputs[3].default_value = 0.75
    tree.links.new(menu.outputs[0], index_switch.inputs[0])


def build_compositor_file_output(tree):
    color = add_node(tree, "CompositorNodeRGB", "color", (-350, 0))
    color.outputs[0].default_value = (0.2, 0.4, 0.8, 1.0)
    gamma = add_node(tree, "ShaderNodeGamma", "gamma", (-100, 0))
    gamma.inputs[1].default_value = 1.8
    output = add_node(tree, "CompositorNodeOutputFile", "file-output", (220, 0))
    output.directory = "//hot-node-roundtrip"
    output.file_name = "beauty_####"
    output.format.media_type = 'IMAGE'
    output.format.file_format = 'PNG'
    output.format.color_mode = 'RGBA'
    output.format.color_depth = '16'
    output.format.compression = 27
    item = output.file_output_items.new('RGBA', "Beauty")
    item.override_node_format = True
    item.format.media_type = 'IMAGE'
    item.format.file_format = 'OPEN_EXR'
    item.format.color_depth = '32'
    tree.links.new(color.outputs[0], gamma.inputs[0])
    tree.links.new(gamma.outputs[0], output.inputs[0])


def default_cases():
    return (
        RoundTripCase("shader-math-properties-links", "ShaderNodeTree", build_shader_math),
        RoundTripCase("frame-parent-layout", "ShaderNodeTree", build_frame_layout),
        RoundTripCase("geometry-multi-input-links", "GeometryNodeTree", build_geometry_multi_input),
        RoundTripCase("geometry-dynamic-items", "GeometryNodeTree", build_geometry_dynamic, compare_layout=False),
        RoundTripCase("geometry-nested-group-interface", "GeometryNodeTree", build_geometry_group),
        RoundTripCase("geometry-zones-closures", "GeometryNodeTree", build_geometry_zones),
        RoundTripCase("geometry-menu-switch", "GeometryNodeTree", build_geometry_menu),
        RoundTripCase("compositor-file-output", "CompositorNodeTree", build_compositor_file_output),
    )
