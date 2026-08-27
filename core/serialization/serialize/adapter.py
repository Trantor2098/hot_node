from ..registry import StgRegistry, StgSpec
from .stg import (
    BasicStg,
    BpyPropCollectionStg,
    CommonTypeStg,
    FallbackStg,
    FlatVectorStg,
    ImageStg,
    InterfaceStg,
    LinkStg,
    NodeGroupStg,
    NodeItemStg,
    NodeLinksStg,
    NodesStg,
    NodeSocketStg,
    NodeStg,
    NodeTreeInterfaceItemStg,
    NodeTreeStg,
    PresetStg,
)


SPECS = (
    StgSpec("basic", BasicStg, ("core", "interface_item", "all")),
    StgSpec("flat_vector", FlatVectorStg, ("core", "interface_item", "all")),
    StgSpec("common_type", CommonTypeStg, ("core", "interface_item", "all")),
    StgSpec("bpy_prop_collection", BpyPropCollectionStg, ("core", "interface_item", "all")),
    StgSpec("image", ImageStg, ("core", "all")),
    StgSpec("node_item", NodeItemStg, ("core", "all")),
    StgSpec("node_socket", NodeSocketStg, ("core", "interface_item", "all")),
    StgSpec("node_group", NodeGroupStg, ("core", "node", "interface_item", "all")),
    StgSpec("node", NodeStg, ("core", "node", "interface_item", "all")),
    StgSpec("link", LinkStg, ("all",)),
    StgSpec("nodes", NodesStg, ("all",)),
    StgSpec("links", NodeLinksStg, ("all",)),
    StgSpec("interface_item", NodeTreeInterfaceItemStg, ("interface_item", "all")),
    StgSpec("interface", InterfaceStg, ("all",)),
    StgSpec("node_tree", NodeTreeStg, ("all",)),
    StgSpec("preset", PresetStg, ("all",)),
    StgSpec("fallback", FallbackStg, ("core", "interface_item", "all")),
)


class Adapter:
    """Build serialization strategies and their ordered dispatch roles."""

    registry = StgRegistry(SPECS, ("core", "node", "interface_item", "all"))

    def __init__(self, blender_version: list[int]):
        self.blender_version = blender_version
        self.stgs = self.registry.build(blender_version)

    def get_stgs(self):
        return self.stgs
