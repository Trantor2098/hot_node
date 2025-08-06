from .stg import *


# NOTE How to register a new stg:
# 1. Declare the stg in the Adapter.Stgs.__init__() method.
# 2. Add the stg to stg_list_all and some other relevant lists. 
#    stg_list_node is used for node deserialization, 
#    stg_list_core is used for cases where no specific list is given, 
#    and stg_list_all is used for registration so must be included.
# 3. New the instance of the stg in the Adapter._load_stgs() method with the blender version this stg supports.


class Adapter():
    """This class defines the stgs with adaption to the current Blender version."""
    class Stgs:
        """Activative strategies for the current Blender version."""
        def __init__(self, blender_version: list[int, int, int]):
            self._blender_version = blender_version
            self.set: SetStg = None
            self.hn: HNStg = None
            self.bpy_prop_collection: BpyPropCollectionStg = None
            self.image: ImageStg = None
            self.node_tree_interface_socket_menu_late: NodeTreeInterfaceSocketMenuLateStg = None
            self.node_tree_interface_socket_menu: NodeTreeInterfaceSocketMenuStg = None
            self.node_socket: NodeSocketStg = None
            self.node_set_late: NodeSetLateStg = None
            self.node_ref_late: NodeRefLateStg = None
            self.compositor_node_color_balance: CompositorNodeColorBalanceStg = None
            self.node_zone_input: NodeZoneInputStg = None
            self.node_zone_output: NodeZoneOutputStg = None
            # self.node_frame: NodeFrameStg = None
            self.node_group: NodeGroupStg = None
            self.node: NodeStg = None
            # self.node_link: NodeLinkStg = None
            self.nodes: NodesStg = None
            self.node_links: NodeLinksStg = None
            self.interface: InterfaceStg = None
            self.node_tree: NodeTreeStg = None
            self.preset: PresetStg = None
            self.fallback: FallbackStg = None
            self._stg_list_hn: list[Stg] = None
            self._stg_list_node: list[Stg] = None
            self._stg_list_core: list[Stg] = None
            self._stg_list_all: list[Stg] = None
            
        @property
        def stg_list_hn(self) -> list[Stg]:
            """HN stgs, used for HN@type"""
            if self._stg_list_hn is not None:
                return self._stg_list_hn
            if self._blender_version == [2, 93, 0]:
                pass
            else:
                self._stg_list_hn = [
                    self.hn,
                    self.fallback, # fallback is always the last one
                ]
            return self._stg_list_hn
            
        @property
        def stg_list_node(self) -> list[Stg]:
            """node stgs"""
            if self._stg_list_node is not None:
                return self._stg_list_node
            if self._blender_version == [2, 93, 0]:
                pass
            else:
                self._stg_list_node = [
                    self.node_zone_output,
                    self.node_zone_input,
                    # self.node_frame,
                    self.node_group,
                    self.compositor_node_color_balance,
                    self.node,
                ]
            return self._stg_list_node
        
        @property
        def stg_list_core(self) -> list[Stg]:
            """will be used for dispatching if no list was specified"""
            if self._stg_list_core is not None:
                return self._stg_list_core
            if self._blender_version == [2, 93, 0]:
                pass
            else:
                self._stg_list_core = [
                    self.bpy_prop_collection,
                    self.image,
                    self.node_tree_interface_socket_menu,
                    self.node_socket,
                    self.fallback, # fallback is always the last one
                ]
        
        @property
        def stg_list_all(self) -> list[Stg]:
            if self._stg_list_all is not None:
                return self._stg_list_all
            if self._blender_version == [2, 93, 0]:
                pass
            else:
                self._stg_list_all = [
                    self.set,
                    self.hn,
                    self.bpy_prop_collection,
                    self.image,
                    self.node_tree_interface_socket_menu_late,
                    self.node_tree_interface_socket_menu,
                    self.node_set_late,
                    self.node_ref_late,
                    self.node_socket,
                    self.compositor_node_color_balance,
                    self.node_zone_input,
                    self.node_zone_output,
                    self.node_group,
                    self.node,
                    # self.node_link,
                    self.nodes,
                    self.node_links,
                    self.interface,
                    self.node_tree,
                    self.preset,
                    self.fallback, # fallback is always the last one
                ]
            return self._stg_list_all
                
    def __init__(self, blender_version: list[int, int, int]):
        self.blender_version = blender_version
        self.stgs = Adapter.Stgs(blender_version)
        self._load_stgs(blender_version)
        # invoke the stg_list and stg_list_all properties to initialize them
        self.stgs.stg_list_core
        self.stgs.stg_list_node
        self.stgs.stg_list_all
            
    def _load_stgs(self, blender_version: list[int, int, int]):
        stgs = self.stgs
        if blender_version == [2, 93, 0]:
            pass
        else:
            stgs.set = SetStg()
            stgs.hn = HNStg()
            stgs.bpy_prop_collection = BpyPropCollectionStg()
            stgs.image = ImageStg()
            stgs.node_tree_interface_socket_menu_late = NodeTreeInterfaceSocketMenuLateStg()
            stgs.node_tree_interface_socket_menu = NodeTreeInterfaceSocketMenuStg()
            stgs.node_socket = NodeSocketStg()
            stgs.node_set_late = NodeSetLateStg()
            stgs.node_ref_late = NodeRefLateStg()
            stgs.compositor_node_color_balance = CompositorNodeColorBalanceStg()
            stgs.node_zone_input = NodeZoneInputStg()
            stgs.node_zone_output = NodeZoneOutputStg()
            # stgs.node_frame = NodeFrameStg()
            stgs.node_group = NodeGroupStg()
            stgs.node = NodeStg()
            # stgs.node_link = LinkStg()
            stgs.nodes = NodesStg()
            stgs.node_links = NodeLinksStg()
            stgs.interface = InterfaceStg()
            stgs.node_tree = NodeTreeStg()
            stgs.preset = PresetStg()
            stgs.fallback = FallbackStg()
            
    def _set_stg_list(self, *stgs):
        self.stgs._stg_list_core = list(stgs)
        
    def set_stg_list_all(self, *stgs):
        self.stgs._stg_list_all = list(stgs)
        
    def get_stgs(self):
        return self.stgs