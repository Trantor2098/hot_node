from . import ServiceBase
from ..utils import constants

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.context.context import Context


class UnsupportedPresetVersion(ValueError):
    pass


class PresetUpdater:
    from_version: tuple[int, int, int]
    to_version: tuple[int, int, int]

    @classmethod
    def update(cls, preset_name: str, jpreset: dict) -> dict:
        raise NotImplementedError("Subclasses must implement this method.")


class VersioningService(ServiceBase):
    oldest_supported_version = (1, 0, 0)
    updaters: tuple[type[PresetUpdater], ...] = ()
    
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
    def update_preset(cls, preset_name: str, jpreset: dict) -> dict:
        jmeta = jpreset.get("HN@meta")
        version = jmeta.get("hot_node_version") if isinstance(jmeta, dict) else None
        if not isinstance(version, list) or len(version) != 3 or not all(isinstance(item, int) for item in version):
            raise UnsupportedPresetVersion(f"Preset '{preset_name}' has no supported Hot Node version metadata.")

        current_version = tuple(constants.HOT_NODE_VERSION)
        preset_version = tuple(version)
        if preset_version < cls.oldest_supported_version:
            raise UnsupportedPresetVersion(f"Preset '{preset_name}' was created by unsupported Hot Node {'.'.join(map(str, version))}.")
        if preset_version > current_version:
            raise UnsupportedPresetVersion(f"Preset '{preset_name}' was created by a newer Hot Node version.")

        updater_by_version = {updater.from_version: updater for updater in cls.updaters}
        while preset_version < current_version:
            updater = updater_by_version.get(preset_version)
            if updater is None:
                break
            jpreset = updater.update(preset_name, jpreset)
            preset_version = updater.to_version
        return jpreset