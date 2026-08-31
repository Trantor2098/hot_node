import sys
from pathlib import Path

import bpy


PACKAGE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PACKAGE_DIR.parent))

from hot_node.core.serialization.manager import SerializationManager
from hot_node.core.serialization.registry import StgRegistry, StgSpec
from hot_node.core.blender import ui, ui_context
from hot_node.dev.roundtrip import NodeSemanticRoundTripTester
from hot_node.services.autosave import AutosaveService
from hot_node.services.history import HistoryService, set_history_service_start_time
from hot_node.services.sync import SyncService, sync_from_timer
from hot_node.services.versioning import UnsupportedPresetVersion, VersioningService


class DummyStg:
    pass


def expect_raises(exception_type, callback):
    try:
        callback()
    except exception_type:
        return
    raise AssertionError(f"Expected {exception_type.__name__}")


def test_registry():
    manager = SerializationManager()
    assert manager.ser_stgs.stg_list_all[-1] is manager.ser_stgs.fallback
    assert manager.deser_stgs.stg_list_all[-1] is manager.deser_stgs.fallback
    assert manager.ser_stgs.stg_list_node == [manager.ser_stgs.node_group, manager.ser_stgs.node]
    assert manager.deser_stgs.stg_list_node[-1] is manager.deser_stgs.node

    duplicate_specs = (
        StgSpec("duplicate", DummyStg, ("all",)),
        StgSpec("duplicate", DummyStg, ("all",)),
    )
    expect_raises(ValueError, lambda: StgRegistry(duplicate_specs, ("all",)).build((5, 2, 0)))


def test_version_boundary():
    current = {"HN@meta": {"hot_node_version": [1, 2, 1]}}
    assert VersioningService.update_preset("current", current) is current
    expect_raises(
        UnsupportedPresetVersion,
        lambda: VersioningService.update_preset("legacy", {"HN_preset_data": {}}),
    )
    expect_raises(
        UnsupportedPresetVersion,
        lambda: VersioningService.update_preset("future", {"HN@meta": {"hot_node_version": [99, 0, 0]}}),
    )


def test_file_output_52():
    tree = bpy.data.node_groups.new("HN@Test File Output", "CompositorNodeTree")
    try:
        node = tree.nodes.new("CompositorNodeOutputFile")
        manager = SerializationManager()
        manager.deser_context.__init__()
        manager.deser_context.node = node
        manager.deser_context.obj_tree = [node]

        jnode = {
            "directory": "//renders",
            "file_name": "beauty_####",
            "format": {
                "media_type": "IMAGE",
                "file_format": "PNG",
                "color_mode": "RGB",
                "color_depth": "16",
                "compression": 42,
            },
            "file_output_items": {
                "0": {"name": "Beauty", "socket_type": "RGBA", "override_node_format": False},
                "1": {
                    "name": "Depth",
                    "socket_type": "FLOAT",
                    "override_node_format": True,
                    "format": {"media_type": "IMAGE", "file_format": "OPEN_EXR", "color_depth": "32"},
                },
            },
        }
        manager.deser_stgs.compositor_node_output_file.set(node, jnode)
        assert node.directory == "//renders"
        assert node.file_name == "beauty_####"
        assert node.format.file_format == "PNG"
        assert node.format.color_depth == "16"
        assert len(node.file_output_items) == 2
        assert node.file_output_items[1].socket_type == "FLOAT"
        assert node.file_output_items[1].format.file_format == "OPEN_EXR"
    finally:
        bpy.data.node_groups.remove(tree)


def test_dynamic_collections_52():
    manager = SerializationManager()
    collection_stg = manager.deser_stgs.bpy_prop_collection
    cases = (
        ("NodeCombineBundle", "bundle_items"),
        ("NodeSeparateBundle", "bundle_items"),
        ("NodeClosureOutput", "input_items"),
        ("NodeClosureOutput", "output_items"),
        ("NodeEvaluateClosure", "input_items"),
        ("NodeEvaluateClosure", "output_items"),
        ("GeometryNodeViewer", "viewer_items"),
    )
    for node_type, attribute in cases:
        tree = bpy.data.node_groups.new(f"HN@Test {node_type} {attribute}", "GeometryNodeTree")
        try:
            node = tree.nodes.new(node_type)
            collection = getattr(node, attribute)
            jitems = {
                "0": {"socket_type": "FLOAT", "name": "Value"},
                "1": {"socket_type": "VECTOR", "name": "Vector"},
            }
            collection_stg.deserialize(collection, jitems)
            assert len(collection) == 2
            assert collection[0].name == "Value"
            assert collection[1].socket_type == "VECTOR"
        finally:
            bpy.data.node_groups.remove(tree)


def test_socket_resolution():
    resolver = SerializationManager().deser_stgs.node_links.find_socket
    sockets = [
        SimpleSocket("first", "NodeSocketFloat", "Value"),
        SimpleSocket("stable-id", "NodeSocketVector", "Vector"),
    ]
    assert resolver(sockets, {"HN@fs_id": "stable-id", "HN@fs_i": 0}, "HN@fs") is sockets[1]
    assert resolver(sockets, {"HN@fs_bid": "NodeSocketVector", "HN@fs_n": "Vector"}, "HN@fs") is sockets[1]
    assert resolver(sockets, {"HN@fs_n": "Value"}, "HN@fs") is sockets[0]
    assert resolver(sockets, {"HN@fs_i": 1}, "HN@fs") is sockets[1]
    assert resolver(sockets, {"HN@fs_i": 9}, "HN@fs") is None


class SimpleSocket:
    def __init__(self, identifier, bl_idname, name):
        self.identifier = identifier
        self.bl_idname = bl_idname
        self.name = name


def test_lifecycle_52():
    AutosaveService.context_cls = type("ContextStub", (), {"get_packs": staticmethod(lambda: {})})
    AutosaveService.autosave_packs("test.blend")

    SyncService.is_enabled = False
    SyncService.late_sync()
    SyncService.late_sync()
    assert SyncService.sync_pending
    assert bpy.app.timers.is_registered(sync_from_timer)
    SyncService.on_disable()
    assert not bpy.app.timers.is_registered(sync_from_timer)

    HistoryService.is_enabled = False
    bpy.app.timers.register(set_history_service_start_time)
    HistoryService.on_disable()
    assert not bpy.app.timers.is_registered(set_history_service_start_time)

    bpy.app.timers.register(ui_context.initialize_ui_context_from_timer)
    bpy.app.timers.unregister(ui_context.initialize_ui_context_from_timer)
    assert not bpy.app.timers.is_registered(ui_context.initialize_ui_context_from_timer)

    bpy.app.timers.register(ui.register_pack_menus_from_timer)
    bpy.app.timers.unregister(ui.register_pack_menus_from_timer)
    assert not bpy.app.timers.is_registered(ui.register_pack_menus_from_timer)


def test_empty_deserialization_cleanup():
    manager = SerializationManager()
    manager.deser_context.obj_tree.clear()
    manager.deserializer.dispatch_deserialize(object(), None)
    manager.deserializer.search_deserialize(object(), None)
    manager.deserializer.specify_deserialize(object(), None, manager.deser_stgs.fallback)
    assert manager.deser_context.obj_tree == []


def test_node_semantic_round_trips():
    report = NodeSemanticRoundTripTester(bpy.context).run_all()
    assert report.failed == 0, report.format()


def main():
    test_registry()
    test_version_boundary()
    test_file_output_52()
    test_dynamic_collections_52()
    test_socket_resolution()
    test_lifecycle_52()
    test_empty_deserialization_cleanup()
    test_node_semantic_round_trips()
    print("HOT_NODE_UPGRADE_TESTS_OK")


if __name__ == "__main__":
    main()