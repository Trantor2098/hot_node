from .pack import Pack
from .preset import Preset
from ..serialization.manager import SerializationManager
from ...utils.file_manager import FileManager
from ...utils import constants


class Context:
    fm = FileManager() # FileManager instance (singleton)
    sm = SerializationManager()
    ser_context = sm.ser_context
    deser_context = sm.deser_context
    
    # USE GET SET
    pack_selected: Pack = None
    preset_selected: Preset = None
    packs: dict[str, Pack] = {}
    ordered_packs: list[Pack] = []
    
    on_packs_changed_callbacks = [] # callbacks to call when packs are changed
    
    # Runtime Flags
    current_pack_for_menu_drawing: Pack = None


    @classmethod
    def initialize(cls, select_pack_name: str = ""):
        """Initialize the context from disk safely."""
        cls.pack_selected: Pack = None # selected pack
        cls.preset_selected: Preset = None # selected preset in selected pack
        cls.packs: dict[str, Pack] = {}
        cls.load_packs_and_add()
        if cls.packs:
            for pack_name, pack in Context.packs.items():
                if pack_name == select_pack_name:
                    Context.select_pack(pack)
                    break
            if not cls.pack_selected:
                cls.select_first_pack_or_none()
        cls.trigger_packs_changed()

    @classmethod
    def reset(cls):
        """Reset the context, this will be called on Blender shutdown."""
        cls.pack_selected: Pack = None # selected pack
        cls.preset_selected: Preset = None # selected preset in selected pack
        cls.packs.clear()
        cls.trigger_packs_changed()
        pass
    
    @classmethod
    def add_packs_changed_listener(cls, callback):
        """Register a callback to be called when packs are changed."""
        cls.on_packs_changed_callbacks.append(callback)
        
    @classmethod
    def remove_packs_changed_listener(cls, callback):
        """Remove a callback from the packs changed listeners."""
        if callback in cls.on_packs_changed_callbacks:
            cls.on_packs_changed_callbacks.remove(callback)

    @classmethod
    def trigger_packs_changed(cls):
        cls.order_packs()
        for callback in cls.on_packs_changed_callbacks:
            callback()

    @classmethod
    def load_pack(cls, pack_name: str):
        """Load a pack by name and load it. Wont add to Context."""
        pack = Pack(pack_name)
        pack.load()
        return pack

    @classmethod
    def load_packs_and_add(cls):
        """Load all packs from the packs directory, the current context will be cleared. Packs will be added to Context."""
        for pack_dir in cls.fm.packs_dir.iterdir():
            if pack_dir.is_dir() and (pack_dir / ".meta").exists():
                pack_name = pack_dir.name
                pack = cls.load_pack(pack_name)
                cls.add_pack(pack)
        cls.trigger_packs_changed()

    @classmethod
    def get_packs(cls) -> dict[str, Pack]:
        """Get all packs in the context."""
        return cls.packs

    @classmethod
    def get_pack(cls, pack_name: str) -> Pack|None:
        return cls.packs.get(pack_name)
    
    @classmethod
    def get_ordered_packs(cls) -> list[Pack]:
        """Get all ordered packs in the context."""
        return cls.ordered_packs
    
    @classmethod
    def get_ordered_packs_by_tree_type(cls, tree_type: str) -> list[Pack]:
        """Get all ordered packs in the context filtered by tree type."""
        packs = [
            pack for pack in cls.get_ordered_packs() if (
                tree_type in pack.meta.tree_types 
                or constants.UNIVERSAL_NODE_TREE_IDNAME in pack.meta.tree_types 
                or not pack.meta.tree_types
            )
        ]
        return packs
        # if packs:
        #     return packs
        # return cls.ordered_packs

    @classmethod
    def get_prev_pack(cls, old_pack: Pack|str|None, packs: list[Pack]|None = None) -> Pack|None:
        """Get the pack before the selected pack, None if no pack selected."""
        if old_pack is None:
            return None
        if cls.ordered_packs == [old_pack]:
            return None
        if packs is None:
            packs = cls.ordered_packs
        if isinstance(old_pack, str):
            old_pack = cls.get_pack(old_pack)
        if not packs:
            return old_pack
        if old_pack not in packs:
            return packs[0]
        idx = packs.index(old_pack)
        if idx == 0:
            return packs[-1]
        return packs[idx - 1]

    @classmethod
    def get_next_pack(cls, old_pack: Pack|str|None, packs: list[Pack]|None = None) -> Pack|None:
        """Get the pack after the selected pack, None if no pack selected."""
        if old_pack is None:
            return None
        if cls.ordered_packs == [old_pack]:
            return None
        if packs is None:
            packs = cls.ordered_packs
        if isinstance(old_pack, str):
            old_pack = cls.get_pack(old_pack)
        if not packs:
            return old_pack
        if old_pack not in packs:
            return packs[0]
        idx = packs.index(old_pack)
        if idx == len(packs) - 1:
            return packs[0]
        return packs[idx + 1]
    
    @classmethod
    def get_prev_pack_with_type(cls, old_pack: Pack|str|None, tree_type: str) -> Pack|None:
        """Get the pack before the selected pack with a specific tree type, None if no pack selected."""
        if old_pack is None:
            return None
        if isinstance(old_pack, str):
            pack_name = old_pack
        else:
            pack_name = old_pack.name
        # BUG preset (address) not in the ordered_packs, why? here use name. fuck fuck fuck
        idx = next((i for i, p in enumerate(cls.ordered_packs) if p.name == pack_name), None)
        if idx is None:
            return None
        for i in range(len(cls.ordered_packs)):
            prev_idx = (idx - i - 1) % len(cls.ordered_packs)
            if tree_type in cls.ordered_packs[prev_idx].meta.tree_types:
                return cls.ordered_packs[prev_idx]
        return None
    
    @classmethod
    def get_next_pack_with_type(cls, old_pack: Pack|str|None, tree_type: str) -> Pack|None:
        """Get the pack after the selected pack with a specific tree type, None if no pack selected."""
        if old_pack is None:
            return None
        if isinstance(old_pack, str):
            pack_name = old_pack
        else:
            pack_name = old_pack.name
        # BUG preset (address) not in the ordered_packs, why? here use name.
        idx = next((i for i, p in enumerate(cls.ordered_packs) if p.name == pack_name), None)
        if idx is None:
            return None
        for i in range(len(cls.ordered_packs)):
            next_idx = (idx + i + 1) % len(cls.ordered_packs)
            if tree_type in cls.ordered_packs[next_idx].meta.tree_types:
                return cls.ordered_packs[next_idx]
        return None
    
    @classmethod
    def get_pack_selected(cls) -> Pack:
        return cls.pack_selected
    
    @classmethod
    def get_pack_selected_name(cls) -> str:
        """Get the name of the selected pack, None to ""."""
        return cls.pack_selected.name if cls.pack_selected is not None else ""

    @classmethod
    def create_pack(cls, pack_name: str):
        """Create an empty pack. Wont add to Context."""
        pack = Pack(pack_name)
        return pack
    
    @classmethod
    def add_pack(cls, pack: Pack):
        cls.packs[pack.name] = pack
        cls.trigger_packs_changed()
        
    @classmethod
    def rename_pack(cls, pack: Pack|str, new_name):
        if isinstance(pack, str):
            pack = cls.get_pack(pack)
        cls.packs.pop(pack.name)
        pack.rename(new_name)
        pack.save_sync_meta()
        cls.packs[new_name] = pack
        cls.trigger_packs_changed()
            
    @classmethod
    def rename_pack_selected(cls, new_name: str):
        pack = cls.get_pack_selected()
        cls.packs.pop(pack.name)
        pack.rename(new_name)
        pack.save_sync_meta()
        cls.packs[new_name] = pack
        cls.trigger_packs_changed()
        
    @classmethod
    def remove_pack(cls, pack: Pack|str):
        if isinstance(pack, str):
            pack = cls.get_pack(pack)
        cls.packs.pop(pack.name)
        pack.save_sync_meta()
        pack.remove()
        cls.trigger_packs_changed()
        
    @classmethod
    def select_pack(cls, pack: Pack|str|None):
        """Wont select if pack is already selected."""
        if isinstance(pack, str):
            pack = cls.get_pack(pack)
        if pack is cls.pack_selected:
            return pack
        cls.pack_selected = pack
        cls.select_first_preset_or_none()
        return pack
    
    @classmethod
    def is_pack_selected(cls, pack: Pack|str|None):
        if pack is None:
            return cls.pack_selected is None
        pack_selected_name = cls.pack_selected.name if cls.pack_selected is not None else ""
        if isinstance(pack, str):
            return pack == pack_selected_name
        else:
            return pack.name == pack_selected_name
    
    @classmethod
    def select_first_pack_or_none(cls):
        """Select the first pack in the context, if it exists."""
        if cls.packs:
            cls.select_pack(next(iter(cls.packs)))
        else:
            cls.select_pack(None)
        cls.select_first_preset_or_none()
    
    @classmethod
    def order_packs(cls, mode: str = 'name') -> list[Pack]:
        """Order packs by name / mtime. The result will be saved to ordered_packs."""
        if mode == 'mtime':
            cls.ordered_packs = sorted(cls.packs.values(), key=lambda pack: pack.pack_dir.stat().st_mtime)
        else:
            cls.ordered_packs = sorted(cls.packs.values(), key=lambda pack: pack.name)
        return cls.ordered_packs
    
    @classmethod
    def get_preset_selected(cls) -> Preset:
        """Get the currently selected preset."""
        return cls.preset_selected
        
    @classmethod
    def select_preset(cls, preset: Preset|str|int|None):
        if isinstance(preset, str):
            preset = cls.pack_selected.presets.get(preset)
        elif isinstance(preset, int):
            preset = cls.pack_selected.ordered_presets[preset] if preset >= 0 and preset < len(cls.pack_selected.ordered_presets) else None
        cls.preset_selected = preset
        
    @classmethod
    def select_first_preset_or_none(cls):
        """Select the first preset in the selected pack."""
        if cls.pack_selected and cls.pack_selected.presets:
            cls.select_preset(next(iter(cls.pack_selected.presets)))
        else:
            cls.preset_selected = None