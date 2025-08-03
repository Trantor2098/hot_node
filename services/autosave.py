import re

import bpy

from datetime import datetime
from pathlib import Path

from . import ServiceBase
from ..utils import utils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.context.context import Context
    from ..core.context.pack import Pack

class AutosaveService(ServiceBase):
    context_cls: 'Context' = None # inject
    
    @staticmethod
    def generate_timestamp_str():
        """2025-01-01T12-00-00 format."""
        return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    @staticmethod
    def parse_timestamp_str_to_seconds(timestamp_str: str) -> int:
        """Parse a 2025-01-01T12-00-00 string into a Unix timestamp (seconds)."""
        t = datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S")
        return int(t.timestamp())

    @classmethod
    def on_enable(cls):
        # cls.autosave_packs()
        if cls.autosave_packs not in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.append(cls.autosave_packs)
    
    @classmethod
    def on_disable(cls):
        cls.autosave_packs()
        cls.clear_outdated_autosaves(utils.get_user_prefs().autosave_retention_days)
        if cls.autosave_packs in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(cls.autosave_packs)

    @classmethod
    def inject_dependencies(cls, context_cls: 'Context'):
        cls.context_cls = context_cls
        
    @classmethod
    def generate_autosave_zip_path(cls, pack: 'Pack'):
        """Generate the autosave zip path for a given pack."""
        timestamp = cls.generate_timestamp_str()
        return cls.fm.autosave_dir / f"{timestamp}_{pack.name}.zip"
    
    @classmethod
    def parse_autosave_zip_path(cls, zip_path: Path) -> tuple[str, str]:
        """Parse the autosave zip path to get the pack timestamp_str / pack_name."""
        return cls.parse_autosave_zip_stem(zip_path.stem)
    
    @classmethod
    def parse_autosave_zip_stem(cls, zip_stem: str) -> tuple[str, str]:
        """Parse the autosave zip stem to get the timestamp_str and pack_name."""
        splited_str = zip_stem.split("_", 1)
        timestamp_str = splited_str[0]
        pack_name = splited_str[1]
        return timestamp_str, pack_name
        
    @classmethod
    def is_timestamp_str_overdated(cls, timestamp_str: str, days: int = 7) -> bool:
        """Check if the timestamp is outdated by the given number of days."""
        timestamp = cls.parse_timestamp_str_to_seconds(timestamp_str)
        return int(datetime.now().timestamp()) - timestamp > days * 24 * 3600
    
    @classmethod
    def autosave_packs(cls):
        """Autosave the current context to disk."""
        for pack in cls.context_cls.get_packs().values():
            dst_zip_path = cls.generate_autosave_zip_path(pack)
            cls.fm.zip_to(pack.pack_dir, dst_zip_path)
            
    @classmethod
    def clear_outdated_autosaves(cls, days: int = 7):
        """Clear outdated autosaves."""
        for zip_path in cls.fm.autosave_dir.glob("*.zip"):
            pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}_.*\.zip$"
            zip_stem = zip_path.stem
            if re.match(pattern, zip_stem):
                timestamp_str, pack_name = cls.parse_autosave_zip_stem(zip_stem)
                if cls.is_timestamp_str_overdated(timestamp_str, days):
                    cls.fm.remove_file(zip_path)
            else:
                if "_deprecated_" in zip_stem:
                    # Handle legacy autosave files, only keep _autosave_ legacy files
                    cls.fm.remove_file(zip_path)