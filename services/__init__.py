import time

from ..utils.file_manager import FileManager


def enable_all():
    """Enable all services in the Hot Node system."""
    from .autosave import AutosaveService
    from .history import HistoryService
    from .sync import SyncService
    from .i18n import I18nService
    from .versioning import VersioningService
    from ..core.context.context import Context
    from ..core.blender.ui import HOTNODE_PT_main
    from ..core.blender import operators
    from ..core.blender.ui_context import UIContext, UpdateHandler
    
    AutosaveService.enable(Context)
    HistoryService.enable(HOTNODE_PT_main, operators, UpdateHandler)
    I18nService.enable()
    SyncService.enable(Context, UIContext)
    VersioningService.enable(Context)


def disable_all():
    """Disable all services in the Hot Node system."""
    from .autosave import AutosaveService
    from .history import HistoryService
    from .i18n import I18nService
    from .sync import SyncService
    from .versioning import VersioningService
    
    AutosaveService().disable()
    HistoryService().disable()
    I18nService().disable()
    SyncService().disable()
    VersioningService().disable()
    
    
def enable_i18n():
    """Enable the I18nService."""
    from .i18n import I18nService
    I18nService.enable()


class ServiceBase:
    """Base class for all services in the Hot Node system."""
    is_enabled = False
    fm = FileManager()

    @classmethod
    def enable(cls, *args, **kwargs):
        if not cls.is_enabled:
            cls.is_enabled = True
            cls.ID = str(time.time())
            if cls.inject_dependencies is not ServiceBase.inject_dependencies:
                cls.inject_dependencies(*args, **kwargs)
            cls.on_enable()
    
    @classmethod
    def disable(cls):
        """Disable the service."""
        if cls.is_enabled:
            cls.is_enabled = False
            cls.on_disable()

    @classmethod
    def on_enable(cls):
        """Override this method to define what happens when the service starts."""
        pass

    @classmethod
    def on_disable(cls):
        """Override this method to define what happens when the service stops."""
        pass
    
    @classmethod
    def inject_dependencies(cls, *args, **kwargs):
        """Override this method to inject dependencies into the service."""
        pass