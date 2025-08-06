import os

import bpy
from bpy.app.handlers import persistent

from . import ServiceBase
from ..core.serialization.manager import SerializationManager
from ..utils.legacy import node_parser, node_setter
from ..utils import utils
from ..utils import constants

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.blender.ui_context import UIContext
    from ..core.context.context import Context
    from ..core.context.pack import Pack
    from ..core.context.preset import Preset


class UpdaterBase:
    version = [0, 0, 0]
    @staticmethod
    def update(preset_name, jpreset):
        raise NotImplementedError("Subclasses must implement this method.")


class Updater_0_X_X(UpdaterBase):
    min_version = [0, 0, 0]
    max_version = [0, 7, 11]
    @staticmethod
    def update(preset_name, jpreset):
        # Implement the update logic for version 0.X.X
        return jpreset


class VersioningService(ServiceBase):
    sm = SerializationManager()
    updaters = [
        Updater_0_X_X,
    ]
    
    @classmethod
    def on_enable(cls):
        pass

    @classmethod
    def on_disable(cls):
        pass
    
    @classmethod
    def inject_dependencies(cls, context_cls: 'Context'):
        cls.context_cls = context_cls
    
    @classmethod
    def update_preset(cls, preset_name, jpreset):
        jmeta = jpreset.get("HN@meta")
        preset_hot_node_version = jmeta.get("hot_node_version") if jmeta else None
        
        if preset_hot_node_version != constants.HOT_NODE_VERSION:
            for updater in cls.updaters:
                if updater.min_version <= preset_hot_node_version <= updater.max_version:
                    jpreset = updater.update(preset_name, jpreset)
                    break
        return jpreset
    
    @classmethod
    def convert_pack_of_0_X_X(cls, bl_context, pack: 'Pack'):
        def try_remove_trees(node_groups, tree_names):
            for tree_name in tree_names:
                tree = node_groups.get(tree_name)
                if tree:
                    node_groups.remove(tree)
                    
        uic: 'UIContext' = bl_context.window_manager.hot_node_ui_context
        preset_file_names = cls.fm.read_dir_file_names(pack.pack_dir, ".json", cull_suffix=False)
        
        node_groups = bpy.data.node_groups
        ori_node_groups = [node_group for node_group in node_groups]
        for node_group in node_groups:
            node_group.name = "HN@TEMP_NODE_TREE_FOR_ORI_" + node_group.name
        temp_shader_node_tree = node_groups.new("HN@TEMP_SHADER_NODE_TREE_FOR_CONVERT", constants.SHADER_NODE_TREE_IDNAME)
        temp_geometry_node_tree = node_groups.new("HN@TEMP_GEOMETRY_NODE_TREE_FOR_CONVERT", constants.GEOMETRY_NODE_TREE_IDNAME)
        temp_texture_node_tree = node_groups.new("HN@TEMP_TEXTURE_NODE_TREE_FOR_CONVERT", constants.TEXTURE_NODE_TREE_IDNAME)
        temp_compositor_node_tree = node_groups.new("HN@TEMP_COMPOSITOR_NODE_TREE_FOR_CONVERT", constants.COMPOSITOR_NODE_TREE_IDNAME)
        tree_map = {
            constants.SHADER_NODE_TREE_IDNAME: temp_shader_node_tree,
            constants.GEOMETRY_NODE_TREE_IDNAME: temp_geometry_node_tree,
            constants.TEXTURE_NODE_TREE_IDNAME: temp_texture_node_tree,
            constants.COMPOSITOR_NODE_TREE_IDNAME: temp_compositor_node_tree,
        }

        failed_preset_names = []
        for preset_file_name in preset_file_names:
            if ".metadata" in preset_file_name:
                continue
            preset_name = preset_file_name[:-5]  # Remove .json suffix
            preset_path = pack.pack_dir / preset_file_name
            jpreset = cls.fm.read_json(preset_path)
            jpreset_data = jpreset.get("HN_preset_data", {})
            if not jpreset_data:
                print(f"[Hot Node] Failed to update preset from Hot Node: [{pack.name}] {preset_name}.: No preset data found.")
                continue
            ov = jpreset_data["version"]
            new_tree_names = [tree_name for tree_name in jpreset.keys() if not tree_name.startswith("HN")]
            dst_tree = tree_map[jpreset_data["tree_type"]]
            dst_tree.nodes.clear()
            dst_tree.links.clear()
            dst_tree.interface.clear()
            
            is_success = True
            try:
                node_setter.apply_preset(bl_context, preset_name, jpreset, dst_tree)
            except Exception as e:
                is_success = False
                failed_preset_names.append(preset_name)
                
            preset = pack.create_preset(preset_name)
            pack.add_preset(preset)
            pack.overwrite_preset(preset, bl_context, main_tree=dst_tree)
            pack.set_preset_separator(preset)
            if is_success:
                print(f"[Hot Node] Updated preset from Hot Node v{utils.version_list_to_str(ov)} to v{utils.version_list_to_str(constants.HOT_NODE_VERSION)}: [{pack.name}] {preset_name}.")
            else:
                print(f"[Hot Node] Failed to update preset from Hot Node v{utils.version_list_to_str(ov)} to v{utils.version_list_to_str(constants.HOT_NODE_VERSION)}: [{pack.name}] {preset_name}.: Parsing error.")

            try_remove_trees(node_groups, new_tree_names)

        pack.save_metas()
        
        legacy_meta_path = pack.pack_dir / ".metadata.json"
        
        legacy_meta = {}
        if legacy_meta_path.exists():
            legacy_meta = cls.fm.read_json(legacy_meta_path)  # Ensure the file is read before deletion
            cls.fm.remove_file(legacy_meta_path)

        # Ensure trees renamed / removed, the most robust way
        for node_group in node_groups:
            if node_group.name.startswith("HN@TEMP_NODE_TREE_FOR_ORI_"):
                node_group.name = node_group.name[26:]
            elif node_group.name.startswith("HN@TEMP_"):
                node_groups.remove(node_group)
        
        return failed_preset_names, legacy_meta