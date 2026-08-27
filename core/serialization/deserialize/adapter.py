from ..registry import StgRegistry, StgSpec
from .stg import (
    BpyPropCollectionStg,
    ColorManagedViewSettingsStg,
    CompositorNodeColorBalanceStg,
    CompositorNodeOutputFileFileSlotStg,
    CompositorNodeOutputFileStg,
    FallbackStg,
    HNStg,
    ImageFormatSettingsStg,
    ImageStg,
    InterfaceStg,
    NodeGroupStg,
    NodeLinksStg,
    NodesStg,
    NodeSocketStg,
    NodeStg,
    NodeTreeInterfaceSocketStg,
    NodeTreeStg,
    NodeZoneInputStg,
    NodeZoneOutputStg,
    PresetStg,
    SetStg,
)


SPECS = (
    StgSpec("set", SetStg, ("all",)),
    StgSpec("hn", HNStg, ("hn", "all")),
    StgSpec("color_managed_view_settings", ColorManagedViewSettingsStg, ("all",)),
    StgSpec("image_format_settings", ImageFormatSettingsStg, ("all",)),
    StgSpec("compositor_node_output_file_file_slot", CompositorNodeOutputFileFileSlotStg, ("all",)),
    StgSpec("bpy_prop_collection", BpyPropCollectionStg, ("core", "all")),
    StgSpec("image", ImageStg, ("core", "all")),
    StgSpec("node_socket", NodeSocketStg, ("core", "all")),
    StgSpec("node_tree_interface_socket", NodeTreeInterfaceSocketStg, ("core", "all")),
    StgSpec("node_zone_output", NodeZoneOutputStg, ("node", "all")),
    StgSpec("node_zone_input", NodeZoneInputStg, ("node", "all")),
    StgSpec("node_group", NodeGroupStg, ("node", "all")),
    StgSpec("compositor_node_color_balance", CompositorNodeColorBalanceStg, ("node", "all")),
    StgSpec("compositor_node_output_file", CompositorNodeOutputFileStg, ("node", "all")),
    StgSpec("node", NodeStg, ("node", "all")),
    StgSpec("nodes", NodesStg, ("all",)),
    StgSpec("node_links", NodeLinksStg, ("all",)),
    StgSpec("interface", InterfaceStg, ("all",)),
    StgSpec("node_tree", NodeTreeStg, ("all",)),
    StgSpec("preset", PresetStg, ("all",)),
    StgSpec("fallback", FallbackStg, ("hn", "core", "all")),
)


class Adapter:
    """Build deserialization strategies and their ordered dispatch roles."""

    registry = StgRegistry(SPECS, ("hn", "node", "core", "all"))

    def __init__(self, blender_version: list[int]):
        self.blender_version = blender_version
        self.stgs = self.registry.build(blender_version)

    def get_stgs(self):
        return self.stgs
