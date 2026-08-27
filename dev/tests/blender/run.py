import sys
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PACKAGE_DIR.parent))

from hot_node.core.serialization.manager import SerializationManager
from hot_node.core.serialization.registry import StgRegistry, StgSpec
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


def main():
    test_registry()
    test_version_boundary()
    print("HOT_NODE_UPGRADE_TESTS_OK")


if __name__ == "__main__":
    main()