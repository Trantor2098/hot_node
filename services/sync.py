import os
import time

import bpy
from bpy.app.handlers import persistent

from . import ServiceBase

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.blender.ui_context import UIContext
    from ..core.context.context import Context

@persistent
def sync_persistent(_):
    if SyncService.is_enabled:
        SyncService.sync()


class SyncService(ServiceBase):
    last_check_time = 0.0
    
    context_cls: 'Context' = None # Context Class, need to inject
    uic_cls: 'UIContext' = None # UIContext Class, need to inject
    
    @classmethod
    def on_enable(cls):
        if sync_persistent not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(sync_persistent)
        cls.read_sync_meta()
        
    @classmethod
    def on_disable(cls):
        if sync_persistent in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(sync_persistent)

    @classmethod
    def inject_dependencies(cls, context_cls: 'Context', uic_cls: 'UIContext'):
        cls.context_cls = context_cls
        cls.uic_cls = uic_cls

    @classmethod
    def sync(cls):
        prev_pack_selected_name = cls.context_cls.pack_selected.name if cls.context_cls.pack_selected else ""
        cls.context_cls.initialize(prev_pack_selected_name)
        cls.uic_cls.initialize()
        cls.save_sync_meta(cls.context_cls.pack_selected)
        # print("[Hot Node] Synced.")

    @classmethod
    def late_sync(cls):
        """Call this to ensure the context is synced after Blender's UI is ready."""
        bpy.app.timers.register(cls.sync)

    @classmethod
    def ensure_sync_on_interval(cls, interval: float = 1.0):
        """Use packmeta proccess_id to ensure the context is synced on a regular interval."""
        current_time = time.time()
        if current_time - cls.last_check_time > interval:
            if not cls.is_id_sync():
                cls.late_sync()
        cls.last_check_time = current_time

    @classmethod
    def save_sync_meta(cls, pack_changed=None):
        """Save the current context to disk root meta."""
        meta = {
            "id": cls.ID,
            "pack_changed_name": pack_changed.name if pack_changed else "",
        }
        cls.fm.write_json(cls.fm.sync_meta_path, meta)
        
    @classmethod
    def read_sync_meta(cls):
        """Read the sync meta from disk."""
        meta = cls.fm.read_json(cls.fm.sync_meta_path)
        return meta

    @classmethod
    def is_id_sync(cls):
        """Check if the context's id matches the disk's id."""
        id = cls.read_sync_meta().get("id")
        is_sync = id == cls.ID
        return is_sync