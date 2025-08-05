import time
from collections import deque
from pathlib import Path

import bpy
from bpy.app.translations import (
    pgettext_iface as iface_,
)


from . import ServiceBase
from .sync import SyncService
from ..utils import utils
from ..utils.reporter import Reporter

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.blender.ui import HOTNODE_PT_main
    from ..core.blender.ui_context import UpdateHandler, UIContext
    from ..core.blender import operators
    
# NOTE In our undo/redo func, use str rather than ref to represent the pack, preset, because sync will change the ref.

class Step():
    def __init__(self, service: 'HistoryService', name: str|None = None, pusher: 'bpy.types.Operator|UpdateHandler|None' = None, jstep: dict = None):
        """Pass name and pusher if no jstep is given."""
        self.service = service
        self.fm = service.fm
        
        # load jstep
        if jstep:
            self.deserialize(jstep)
            return
        # create new step
        elif not name or not pusher:
            raise ValueError("Step must have a name and a pusher if no jstep is given.")
        
        self.name = name
        self.pusher = pusher if isinstance(pusher, type) else pusher.__class__
        
        self.born_time = time.time()
        self.deleted_paths = []
        self.changed_paths = []
        self.created_paths = []
        self.his_deleted_paths = []
        self.his_changed_paths = []
        self.his_created_paths = []
        self.undo_callback = None
        self.redo_callback = None
        self.undo_callback_params = []
        self.redo_callback_params = []
        
    def serialize(self) -> dict:
        """Serialize this step to a dictionary."""
        return {
            "name": self.name,
            "pusher": self.pusher.__name__,
            "born_time": self.born_time,
            "deleted_paths": [str(path) for path in self.deleted_paths],
            "changed_paths": [str(path) for path in self.changed_paths],
            "created_paths": [str(path) for path in self.created_paths],
            "his_deleted_paths": [str(path) for path in self.his_deleted_paths],
            "his_changed_paths": [str(path) for path in self.his_changed_paths],
            "his_created_paths": [str(path) for path in self.his_created_paths],
            "undo_callback": self.undo_callback.__name__ if self.undo_callback else None,
            "redo_callback": self.redo_callback.__name__ if self.redo_callback else None,
            "undo_callback_params": self.undo_callback_params if self.undo_callback_params else [],
            "redo_callback_params": self.redo_callback_params if self.redo_callback_params else [],
        }
        
    def deserialize(self, jstep: dict):
        """Deserialize this step from a dictionary."""
        self.name = jstep["name"]
        self.pusher = getattr(self.service.operators_module, jstep["pusher"]) if jstep["pusher"] != "UpdateHandler" else self.service.update_handler_cls
        self.born_time = jstep["born_time"]
        self.deleted_paths = [Path(path) for path in jstep["deleted_paths"]]
        self.changed_paths = [Path(path) for path in jstep["changed_paths"]]
        self.created_paths = [Path(path) for path in jstep["created_paths"]]
        self.his_deleted_paths = [Path(path) for path in jstep["his_deleted_paths"]]
        self.his_changed_paths = [Path(path) for path in jstep["his_changed_paths"]]
        self.his_created_paths = [Path(path) for path in jstep["his_created_paths"]]
        self.undo_callback = getattr(self.pusher, jstep["undo_callback"])
        self.redo_callback = getattr(self.pusher, jstep["redo_callback"])
        self.undo_callback_params = jstep["undo_callback_params"] if jstep["undo_callback_params"] else []
        self.redo_callback_params = jstep["redo_callback_params"] if jstep["redo_callback_params"] else []

    def set_deleted_paths(self, *deleted_paths: Path):
        """Set the deleted paths for this step."""
        self.deleted_paths = deleted_paths
        self.his_deleted_paths = self.push_his_files(deleted_paths, type="delete")
        
    def set_changed_paths(self, *changed_paths: Path):
        """Set the changed paths for this step."""
        self.changed_paths = changed_paths
        self.his_changed_paths = self.push_his_files(changed_paths, type="change")
        
    def set_created_paths(self, *created_paths: Path):
        """Set the created paths for this step."""
        self.created_paths = created_paths
        
    def add_deleted_paths(self, *deleted_paths: Path):
        """Add deleted paths for this step."""
        self.deleted_paths.extend(deleted_paths)
        self.his_deleted_paths.extend(self.push_his_files(deleted_paths, type="delete"))
        
    def add_changed_paths(self, *changed_paths: Path):
        """Add changed paths for this step."""
        self.changed_paths.extend(changed_paths)
        self.his_changed_paths.extend(self.push_his_files(changed_paths, type="change"))
        
    def add_created_paths(self, *created_paths: Path):
        """Add created paths for this step."""
        self.created_paths.extend(created_paths)
        self.his_created_paths.extend(self.push_his_files(created_paths, type="create"))

    def set_undo(self, undo_callback, *undo_callback_params):
        """Set the undo callback and its parameters. Can pass tuple."""
        self.undo_callback = undo_callback
        self.undo_callback_params = undo_callback_params
        
    def set_redo(self, redo_callback, *redo_callback_params):
        """Set the redo callback and its parameters. Can pass tuple."""
        self.redo_callback = redo_callback
        self.redo_callback_params = redo_callback_params
        
    def set_undo_redo(self, undo_redo_callback, *undo_redo_callback_params):
        """Set both undo and redo callbacks and their parameters. Can pass tuple."""
        self.set_undo(undo_redo_callback, *undo_redo_callback_params)
        self.set_redo(undo_redo_callback, *undo_redo_callback_params)
        
    def push_his_files(self, src_paths: list[Path], type: str) -> list:
        his_paths = []
        current_time = time.time()
        for i, src_path in enumerate(src_paths):
            identifier = "_".join((str(current_time), str(i), type))
            dot_suffix = utils.get_dot_suffix(str(src_path), ".zip", ".json", ".meta")
            if dot_suffix is None:
                his_path = self.fm.history_file_dir / identifier
                self.fm.copy_tree(src_path, his_path)
            else:
                dst_name = "".join((identifier, dot_suffix))
                his_path = self.fm.history_file_dir / dst_name
                self.fm.copy_file(src_path, his_path)
            his_paths.append(his_path)
        return his_paths
    
    def pull_his_files(self, his_paths: list[Path], src_paths: list[Path]) -> list:
        """Pull the history files from his_paths."""
        path_num = len(src_paths)
        for i in range(path_num):
            src_path = src_paths[i]
            his_path = his_paths[i]
            dot_suffix = utils.get_dot_suffix(str(src_path), ".zip", ".json", ".meta")
            if dot_suffix is None:
                self.fm.remove_tree(src_path) # remove renamed new items if exists
                self.fm.copy_tree(his_path, src_path)
                self.fm.remove_tree(his_path)
            else:
                self.fm.remove_file(src_path) # remove renamed new items if exists
                self.fm.copy_file(his_path, src_path)
                self.fm.remove_file(his_path)
    
    def remove_his_files(self):
        """Remove the history files of this step."""
        self.fm.remove_paths(self.his_changed_paths)
        self.fm.remove_paths(self.his_created_paths)
        self.fm.remove_paths(self.his_deleted_paths)

    def undo(self, uic: 'UIContext'):
        # Create Undo: push files to history
        self.his_created_paths = self.push_his_files(self.created_paths, "create")
        self.fm.remove_paths(self.created_paths)
        # Delete Undo: pull files back
        self.pull_his_files(self.his_deleted_paths, self.deleted_paths)
        # Change Undo: Push new to history and pull old from history
        new_his_changed_paths = self.push_his_files(self.changed_paths, "change")
        self.pull_his_files(self.his_changed_paths, self.changed_paths)
        self.his_changed_paths = new_his_changed_paths
        
        if self.undo_callback is not None:
            self.undo_callback(uic, *self.undo_callback_params)

    def redo(self, uic: 'UIContext'):
        # Create Redo
        self.pull_his_files(self.his_created_paths, self.created_paths)
        # Delete Redo
        self.his_deleted_paths = self.push_his_files(self.deleted_paths, "delete")
        self.fm.remove_paths(self.deleted_paths)
        # Change Redo
        new_his_changed_paths = self.push_his_files(self.changed_paths, "change")
        self.pull_his_files(self.his_changed_paths, self.changed_paths)
        self.his_changed_paths = new_his_changed_paths
        
        if self.redo_callback is not None:
            self.redo_callback(uic, *self.redo_callback_params)
        
          
class HistoryService(ServiceBase):
    jsteps: deque[dict] = deque(maxlen=256)
    jundone_steps: list[dict] = []
    
    is_service_session_match = False
    
    main_panel_cls: 'HOTNODE_PT_main' = None # Main Panel Class, need to inject
    operators_module: 'operators' = None
    update_handler_cls: 'UpdateHandler' = None

    @classmethod
    def on_enable(cls):
        cls.service_start_time = str(time.time()) # Blender FloatProperty cuts float tail, use str
        def set_service_start_time():
            bpy.context.window_manager.hot_node_ui_context.history_service_start_time = cls.service_start_time
        bpy.app.timers.register(set_service_start_time)
        
        cls.load_history()
        
    @classmethod
    def on_disable(cls):
        pass
        
    @classmethod
    def inject_dependencies(cls, main_panel_cls: 'HOTNODE_PT_main', operators_module: 'operators', update_handler_cls: 'UpdateHandler'):
        cls.main_panel_cls = main_panel_cls
        cls.operators_module = operators_module
        cls.update_handler_cls = update_handler_cls

    @classmethod
    def step(cls, name: str, pusher: 'bpy.types.Operator|UpdateHandler'):
        step = Step(cls, name, pusher)
        return step
    
    @classmethod
    def set_deleted_paths(cls, step: Step, *deleted_paths: Path):
        """Set the current step's deleted paths."""
        step.deleted_paths = deleted_paths
        step.his_deleted_paths = step.push_his_files(deleted_paths, type="delete")
        
    @classmethod
    def set_created_paths(cls, step: Step, *created_paths: Path):
        """Set the current step's created paths."""
        step.created_paths = created_paths
        
    @classmethod
    def set_changed_paths(cls, step: Step, *changed_paths: Path):
        """Set the current step's changed paths."""
        step.changed_paths = changed_paths
        step.his_changed_paths = step.push_his_files(changed_paths, type="change")

    @classmethod
    def add_deleted_paths(cls, step: Step, *deleted_paths: Path):
        """Add deleted paths for this step."""
        step.deleted_paths.extend(deleted_paths)
        step.his_deleted_paths.extend(step.push_his_files(deleted_paths, type="delete"))
        
    @classmethod
    def add_changed_paths(cls, step: Step, *changed_paths: Path):
        """Add changed paths for this step."""
        step.changed_paths.extend(changed_paths)
        step.his_changed_paths.extend(step.push_his_files(changed_paths, type="change"))
        
    @classmethod
    def add_created_paths(cls, step: Step, *created_paths: Path):
        """Add created paths for this step."""
        step.created_paths.extend(created_paths)
        step.his_created_paths.extend(step.push_his_files(created_paths, type="create"))

    @classmethod
    def set_undo(cls, step: Step, undo_callback, *undo_callback_params):
        """Set the current step's undo callback. Dont need to pass uic!"""
        step.set_undo(undo_callback, *undo_callback_params)

    @classmethod
    def set_redo(cls, step: Step, redo_callback, *redo_callback_params):
        """Set the current step's redo callback. Dont need to pass uic!"""
        step.set_redo(redo_callback, *redo_callback_params)
        
    @classmethod
    def set_undo_redo(cls, step: Step, undo_redo_callback, *undo_redo_callback_params):
        """Set the current step's redo callback. Dont need to pass uic!"""
        step.set_undo(undo_redo_callback, *undo_redo_callback_params)
        step.set_redo(undo_redo_callback, *undo_redo_callback_params)
        
    @classmethod
    def ensure_sync(cls):
        if SyncService.is_enabled:
            if not SyncService.is_id_sync():
                cls.load_history()
        else:
            cls.load_history() # XXX costly

    @classmethod
    def load_history(cls):
        """Read the history meta from disk."""
        history_meta = cls.fm.read_json(cls.fm.history_meta_path)
        cls.jsteps = deque(history_meta.get("steps", []), maxlen=256)
        cls.jundone_steps = history_meta.get("undone_steps", [])
        cls.clamp_step_num()
        
    @classmethod
    def save_history(cls):
        """Save the history meta to disk."""
        history_meta = {
            "id": cls.ID,
            "steps": list(cls.jsteps),
            "undone_steps": cls.jundone_steps,
        }
        cls.fm.write_json(cls.fm.history_meta_path, history_meta)
        
    @classmethod
    def save_step(cls, step: Step):
        """Save the history meta to disk."""
        cls.ensure_sync()
        cls.jsteps.appendleft(step.serialize())
        cls.discard_jsteps(cls.jundone_steps)
        cls.clamp_step_num()
        cls.save_history()
        
    @classmethod
    def undo(cls, uic: 'UIContext'):
        """Undo the last step."""
        cls.ensure_sync()
        if cls.jsteps:
            jstep = cls.jsteps.popleft()
            step = Step(cls, jstep=jstep)
            step.undo(uic)
            jstep = step.serialize()
            cls.jundone_steps.append(jstep)
            cls.save_history()
        return step
            
    @classmethod
    def redo(cls, uic: 'UIContext'):
        """Redo the last undone step."""
        cls.ensure_sync()
        if cls.jundone_steps:
            jstep = cls.jundone_steps.pop()
            step = Step(cls, jstep=jstep)
            step.redo(uic)
            jstep = step.serialize()
            cls.jsteps.appendleft(jstep)
            cls.save_history()
        return step
            
    @classmethod
    def discard_jstep(cls, jstep: dict):
        """Discard jstep directly, remove its history files. Faster then Step(jstep=jstep).discard()."""
        his_changed_paths = [Path(path) for path in jstep.get("his_changed_paths", [])]
        his_created_paths = [Path(path) for path in jstep.get("his_created_paths", [])]
        his_deleted_paths = [Path(path) for path in jstep.get("his_deleted_paths", [])]
        cls.fm.remove_paths(his_changed_paths)
        cls.fm.remove_paths(his_created_paths)
        cls.fm.remove_paths(his_deleted_paths)

    @classmethod
    def discard_jsteps(cls, jsteps: list[dict]|deque[dict]):
        """Delete history files."""
        for jstep in jsteps:
            cls.discard_jstep(jstep)
        jsteps.clear()
            
    @classmethod
    def clear_cached_steps(cls):
        cls.jsteps.clear()
        cls.jundone_steps.clear()

    @classmethod
    def clamp_step_num(cls):
        """Discard the steps that exceed the user set max length."""
        maxlen = bpy.context.preferences.edit.undo_steps
        while len(cls.jsteps) > maxlen:
            jstep = cls.jsteps.pop()
            cls.discard_jstep(jstep)
            
    @classmethod
    def has_steps(cls) -> bool:
        """Check if there are steps in the history."""
        return bool(cls.jsteps)
    
    @classmethod
    def has_undone_steps(cls) -> bool:
        """Check if there are undone steps in the history."""
        return bool(cls.jundone_steps)