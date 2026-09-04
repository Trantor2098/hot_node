import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
import mathutils


PACKAGE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PACKAGE_DIR.parent))

from hot_node.core.serialization.manager import SerializationManager
from hot_node.core.serialization.serialize import serializer as serializer_module
from hot_node.core.serialization.deserialize import deserializer as deserializer_module


class TestPreferences:
    node_tree_reuse_mode = 'ALWAYS_NEW'
    is_overwrite_tree_io = True
    dir_to_match_image = ""
    image_name_filter = ""


def make_context(tree):
    return SimpleNamespace(
        space_data=SimpleNamespace(
            edit_tree=tree,
            node_tree=tree,
            cursor_location=mathutils.Vector((0.0, 0.0)),
        ),
        active_object=None,
    )


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Pass the preset JSON path after --")
    preset_path = Path(sys.argv[sys.argv.index("--") + 1])
    jpreset = json.loads(preset_path.read_text(encoding="utf-8"))
    main_tree_data = jpreset["HN@node_trees"]["HN@main_tree"]
    tree = bpy.data.node_groups.new("HN@Asset Regression", main_tree_data["bl_idname"])
    manager = SerializationManager()
    prefs = TestPreferences()
    original_ser_prefs = serializer_module.utils.get_user_prefs
    original_deser_prefs = deserializer_module.utils.get_user_prefs
    serializer_module.utils.get_user_prefs = lambda _context=None: prefs
    deserializer_module.utils.get_user_prefs = lambda _context=None: prefs
    try:
        manager.deserialize_preset(make_context(tree), copy.deepcopy(jpreset), tree, is_add_nodes_to_new_tree=True)
        expected_nodes = {
            key for key in main_tree_data["nodes"]
            if not key.startswith("HN@")
        }
        expected_links = len(main_tree_data["links"])
        assert len(tree.nodes) == len(expected_nodes), (len(tree.nodes), len(expected_nodes))
        assert len(tree.links) == expected_links, (len(tree.links), expected_links)
        assert len(tree.nodes["Closure Output"].input_items) == 1
        assert len(tree.nodes["Closure Output"].output_items) == 1
        assert len(tree.nodes["Closure to List"].list_items) == 1
        assert len(tree.nodes["Viewer"].viewer_items) == 1
        print("PRESET_ASSET_ROUNDTRIP_OK", preset_path)
    finally:
        serializer_module.utils.get_user_prefs = original_ser_prefs
        deserializer_module.utils.get_user_prefs = original_deser_prefs
        bpy.data.node_groups.remove(tree)


if __name__ == "__main__":
    main()
