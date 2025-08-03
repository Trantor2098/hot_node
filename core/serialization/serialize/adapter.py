from .stg import *

class Adapter():
    """This class defines the stgs with adaption to the current Blender version."""
    class Stgs:
        """Activative strategies for the current Blender version."""
        def __init__(self, blender_version: list[int, int, int]):
            self.blender_version = blender_version
            self.fallback: FallbackStg = None
            self.preset: PresetStg = None
            self.node_tree: NodeTreeStg = None
            self.interface: InterfaceStg = None
            self.interface_item: NodeTreeInterfaceItemStg = None
            self.node_item: NodeItemStg = None
            self.nodes: NodesStg = None
            self.links: NodeLinksStg = None
            self.node: NodeStg = None
            self.link: LinkStg = None
            self.node_group: NodeGroupStg = None
            self.node_socket: NodeSocketStg = None
            self.image: ImageStg = None
            self.bpy_prop_collection: BpyPropCollectionStg = None
            self.flat_vector: FlatVectorStg = None
            self.common_type: CommonTypeStg = None
            self.basic: BasicStg = None
            self._stg_list_core: list[Stg] = None
            self._stg_list_node: list[Stg] = None
            self._stg_list_interface_item: list[Stg] = None
            self._stg_list_all: list[Stg] = None
            
        # use property to uncoupled stg/stg_list definitions for defferent versions
        @property
        def stg_list_core(self) -> list[Stg]:
            # the list of stgs for dispatching, excluding strongly customized stgs like preset, node_tree, etc.
            if self._stg_list_core is not None:
                return self._stg_list_core
            
            if self.blender_version == "2.93":
                pass
            else:
                self._stg_list_core = [
                    self.basic,
                    self.flat_vector,
                    self.common_type,
                    self.bpy_prop_collection,
                    self.image,
                    self.node_item,
                    self.node_socket,
                    self.node_group,
                    self.node, # special node stg should be in the front of me
                    self.fallback, # last stg will be used as fallback
                ]
            return self._stg_list_core
        
        @property
        def stg_list_node(self) -> list[Stg]:
            # the list of stgs for dispatching, excluding strongly customized stgs like preset, node_tree, etc.
            if self._stg_list_node is not None:
                return self._stg_list_node
            
            if self.blender_version == "2.93":
                pass
            else:
                self._stg_list_node = [
                    self.node_group,
                    self.node, # special node stg should be in the front of me
                ]
            return self._stg_list_core
        
        @property
        def stg_list_interface_item(self) -> list[Stg]:
            # the list of stgs for dispatching, excluding strongly customized stgs like preset, node_tree, etc.
            if self._stg_list_interface_item is not None:
                return self._stg_list_interface_item
            
            if self.blender_version == "2.93":
                pass
            else:
                self._stg_list_interface_item = [
                    self.basic,
                    self.flat_vector,
                    self.common_type,
                    self.bpy_prop_collection,
                    self.node_socket,
                    self.interface_item,
                    self.node_group,
                    self.node, # special node stg should be in the front of me
                    self.fallback, # last stg will be used as fallback
                ]
            return self._stg_list_core
        
        @property
        def stg_list_all(self) -> list[Stg]:
            # the list of all stgs. subclass should be in the front.
            if self._stg_list_all is not None:
                return self._stg_list_all
            
            if self.blender_version == "2.93":
                pass
            else:
                self._stg_list_all = [
                    self.basic,
                    self.flat_vector,
                    self.common_type,
                    self.bpy_prop_collection,
                    self.image,
                    self.node_item,
                    self.node_socket,
                    self.node_group,
                    self.node,
                    self.link,
                    self.nodes,
                    self.links,
                    self.interface_item,
                    self.interface,
                    self.node_tree,
                    self.preset,
                    self.fallback, # last stg will be used as fallback
                ]
            return self._stg_list_all

    def __init__(self, blender_version: list[int, int, int]):
        self.blender_version = blender_version
        self.stgs = Adapter.Stgs(blender_version)
        self._load_stgs(blender_version)
        # invoke the stg_list and stg_list_all properties to initialize them
        self.stgs.stg_list_core
        self.stgs.stg_list_node
        self.stgs.stg_list_interface_item
        self.stgs.stg_list_all
            
    def _load_stgs(self, blender_version: list[int, int, int]):
        stgs = self.stgs
        if blender_version == [2, 93, 0]:
            pass
        else:
            stgs.preset = PresetStg()
            stgs.node_tree = NodeTreeStg()
            stgs.interface = InterfaceStg()
            stgs.interface_item = NodeTreeInterfaceItemStg()
            stgs.nodes = NodesStg()
            stgs.links = NodeLinksStg()
            stgs.node_socket = NodeSocketStg()
            stgs.node_item = NodeItemStg()
            stgs.flat_vector = FlatVectorStg()
            stgs.common_type = CommonTypeStg()
            stgs.image = ImageStg()
            stgs.bpy_prop_collection = BpyPropCollectionStg()
            stgs.node_group = NodeGroupStg()
            stgs.node = NodeStg()
            stgs.link = LinkStg()
            stgs.basic = BasicStg()
            stgs.fallback = FallbackStg() # last stg will be used as fallback
        
    def get_stgs(self):
        return self.stgs