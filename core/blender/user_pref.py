import bpy
from bpy.types import AddonPreferences
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatVectorProperty,
    StringProperty,
    IntProperty,
)
from bpy.app.translations import pgettext_iface as iface_

from ...utils import constants
from ...utils.file_manager import FileManager
from ...utils import utils
from . import ui
from ...services.sync import SyncService as SS
from ...services.history import HistoryService as HS
from ...services.i18n import I18nService as IS


def translate_default_name(user_prefs: 'HotNodeUserPrefs'):
    """Translate default pack and preset names to the current locale."""
    locale = bpy.app.translations.locale
    
    # optimize for en_US, no need to loop
    if locale == "en_US":
        if (
            user_prefs.sidebar_category == "Hot Node"
            and user_prefs.default_pack_name == "NodesPack"
            and user_prefs.default_preset_name == "Nodes"
            and user_prefs.merged_add_nodes_menu_label == "Add Nodes"
            and user_prefs.merged_save_nodes_menu_label == "Save Nodes"
        ):
            return 
    
    # loop to find the default translated names.
    default_translated_names = IS.get_msg_from_all_locales("Hot Node")
    if user_prefs.sidebar_category in default_translated_names.values() and user_prefs.sidebar_category != default_translated_names.get(locale, "Hot Node"):
        user_prefs.sidebar_category = default_translated_names.get(locale, "Hot Node")
    
    default_translated_names = IS.get_msg_from_all_locales("NodesPack")
    if user_prefs.default_pack_name in default_translated_names.values() and user_prefs.default_pack_name != default_translated_names.get(locale, "NodesPack"):
        user_prefs.default_pack_name = default_translated_names.get(locale, "NodesPack")
    
    default_translated_names = IS.get_msg_from_all_locales("Nodes")
    if user_prefs.default_preset_name in default_translated_names.values() and user_prefs.default_preset_name != default_translated_names.get(locale, "Nodes"):
        user_prefs.default_preset_name = default_translated_names.get(locale, "Nodes")

    default_translated_names = IS.get_msg_from_all_locales("Add Nodes")
    if user_prefs.merged_add_nodes_menu_label in default_translated_names.values() and user_prefs.merged_add_nodes_menu_label != default_translated_names.get(locale, "Add Nodes"):
        user_prefs.merged_add_nodes_menu_label = default_translated_names.get(locale, "Add Nodes")
        
    default_translated_names = IS.get_msg_from_all_locales("Save Nodes")
    if user_prefs.merged_save_nodes_menu_label in default_translated_names.values() and user_prefs.merged_save_nodes_menu_label != default_translated_names.get(locale, "Save Nodes"):
        user_prefs.merged_save_nodes_menu_label = default_translated_names.get(locale, "Save Nodes")


def sidebar_category_update(self: 'HotNodeUserPrefs', context):
    panel_classes = [
        ui.HOTNODE_PT_main,
        ui.HOTNODE_PT_edit,
    ]
    
    if self.is_dev and FileManager().is_path_exist(constants.HOT_NODE_ADDON_PATH / "dev"):
        from ...dev import dev_ui
        panel_classes.append(dev_ui.HOTNODE_PT_dev_run)

    for cls in panel_classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        if cls is ui.HOTNODE_PT_main:
            cls.bl_label = self.sidebar_category
        cls.bl_category = self.sidebar_category
        bpy.utils.register_class(cls)
        
        
def add_nodes_menu_mode_update(self: 'HotNodeUserPrefs', context):
    pmm = ui.PackMenuManager()
    pmm.remove_merged_add_nodes_packs_menu()
    pmm.remove_list_add_nodes_pack_menu()
    
    if self.add_nodes_menu_mode == 'MERGE':
        pmm.append_merged_add_nodes_packs_menu()
    elif self.add_nodes_menu_mode == 'LIST':
        pmm.append_list_add_nodes_pack_menu()
        
        
def save_nodes_menu_mode_update(self: 'HotNodeUserPrefs', context):
    pmm = ui.PackMenuManager()
    pmm.remove_merged_save_nodes_packs_menu()
    pmm.remove_list_save_nodes_pack_menu()

    if self.save_nodes_menu_mode == 'MERGE':
        pmm.append_merged_save_nodes_packs_menu()
    elif self.save_nodes_menu_mode == 'LIST':
        pmm.append_list_save_nodes_pack_menu()
        
is_skip_data_dir_update = False

def data_dir_update(self: 'HotNodeUserPrefs', context):
    global is_skip_data_dir_update
    if is_skip_data_dir_update:
        return
    
    fm = FileManager()

    if not fm.is_path_exist(self.data_dir) or not fm.is_valid_dir_str(self.data_dir):
        is_skip_data_dir_update = True
        self.data_dir = str(fm.app_data_dir)
        is_skip_data_dir_update = False
        return
    
    fm.define_app_data_dir_structure(self.data_dir)
    fm.ensure_app_dir_structure()
    SS.sync()
    HS.load_history()
    
    
def is_filter_pack_by_tree_type_update(self: 'HotNodeUserPrefs', context):
    SS.sync()


def is_dev_update(self, context):
    if FileManager().is_path_exist(constants.HOT_NODE_ADDON_PATH / "dev"):
        from ... import dev
        if self.is_dev:
            dev.register()
            constants.IS_DEV = True
            constants.FILE_INDENT = 1
        else:
            dev.unregister()
            constants.IS_DEV = False
            constants.FILE_INDENT = None


class HotNodeUserPrefs(AddonPreferences):
    bl_idname = constants.HOT_NODE_PKG

    # Nodes Adding
    is_overwrite_tree_io: BoolProperty(
        name="Overwrite Tree I/O",
        description="Allow overwriting of current edit tree interface if there's Group Input / Output nodes with different interface in the preset.",
        default=False,
    ) # type: ignore
    
    node_tree_reuse_mode: EnumProperty(
        name="Node Tree Reuse",
        description="Decide what to do when a node tree with the same name already exists.",
        items=[
            ('TRY_TO_REUSE', "Try to Reuse", "Only create new node tree if the node tree interface is different."),
            ('ALWAYS_NEW', "Always New", "Always create a new node tree, even if the two trees are the same."),
        ],
        default='TRY_TO_REUSE',
    ) # type: ignore
    
    dir_to_match_image: StringProperty(
        name="Directory to Match Images",
        description="Directory to match and load images from when getting nodes from preset.",
        default="",
        subtype='DIR_PATH'
    ) # type: ignore

    image_name_filter: StringProperty(
        name="Image Name Filter",
        description="Filter for image names when loading images.",
        default="",
    ) # type: ignore
    
    # UI
    sidebar_category: StringProperty(
        name="Sidebar Category",
        description="Addon panel category to show in the UI sidebar.",
        default="Hot Node",
        update=sidebar_category_update,
    ) # type: ignore
    
    default_preset_name: StringProperty(
        name="Default Preset Name",
        description="Name of the default preset for creating nodes preset.",
        default=IS.msg("Nodes"),
    ) # type: ignore
    
    default_pack_name: StringProperty(
        name="Default Pack Name",
        description="Name of the default pack for creating pack.",
        default=IS.msg("NodesPack"),
    ) # type: ignore
    
    is_filter_pack_by_tree_type: BoolProperty(
        name="Filter Pack by Tree Type",
        description="Filter packs in the add-on panel by the current node tree type in the node editor",
        default=False,
        update=is_filter_pack_by_tree_type_update,
    ) # type: ignore

    add_nodes_menu_mode: EnumProperty(
        name="Add Nodes Menu",
        description="Extend the node add menu (Shift + A menu) to access and add your custom nodes.",
        items=[
            ('DISABLE', "Disable", "Disable the add nodes menu."),
            ('MERGE', "Merge", "Extend the add nodes menu with a menu containing custom packs."),
            ('LIST', "List", "Extend the add nodes menu with a list of custom pack menu."),
        ],
        default='MERGE',
    ) # type: ignore
    
    save_nodes_menu_mode: EnumProperty(
        name="Save Nodes Menu",
        description="Extend the context menu (Right-click menu) to save custom nodes.",
        items=[
            ('DISABLE', "Disable", "Disable the save nodes menu."),
            ('MERGE', "Merge", "Extend the context menu with a menu containing custom packs for saving nodes."),
            ('LIST', "List", "Extend the context menu with a list of custom pack menu."),
        ],
        default='MERGE',
    ) # type: ignore
    
    merged_add_nodes_menu_label: StringProperty(
        name="Merged Add Nodes Menu Label",
        description="Name of the extended menu for adding custom nodes.",
        default=IS.msg("Add Nodes"),
        update=add_nodes_menu_mode_update,
    ) # type: ignore

    merged_save_nodes_menu_label: StringProperty(
        name="Merged Save Nodes Menu Label",
        description="Name of the extended menu for saving custom nodes.",
        default=IS.msg("Save Nodes"),
        update=save_nodes_menu_mode_update,
    ) # type: ignore
    
    sidebar_items: EnumProperty(
        name="Sidebar Items",
        description="Items to show in the add-on panel's side bar",
        items=[
            ('OVERWRITE_TREE_IO', "Overwrite Tree I/O", "Show overwrite tree I/O toggle in the side bar."),
            ('PACKS', "Packs", "Show packs in the side bar to select."),
            ('TRANSFER_PRESET', "Duplicate / Copy / Move Preset", "Show duplicate / copy / move preset button in the side bar."),
            ('UNDO_REDO', "Undo / Redo", "Show undo / redo button in the side bar."),
            ('REFRESH', "Refresh", "Show refresh button in the side bar."),
            ('PREFERENCES', "Preferences", "Show preferences button in the side bar."),
        ],
        options={'ENUM_FLAG'}
    ) # type: ignore
    
    min_ui_list_length: IntProperty(
        name="Min UI List Length",
        description="Minimum length of the list to show in UI",
        default=3,
        min=3,
        soft_max=100,
    ) # type: ignore
    
    is_show_addon_new_version_info: BoolProperty(
        name="Show Add-on New Version Info",
        description="Show the infos and special operations for the new version of add-on in the UI.",
        default=True,
    ) # type: ignore

    # Data
    is_use_custom_undo_steps: BoolProperty(
        name="Use Custom Undo Steps",
        description="Enable custom undo steps for the add-on instead of using the default Blender undo steps.",
        default=False,
    ) # type: ignore
    
    undo_steps: IntProperty(
        name="Undo Steps",
        description="Number of undo steps to keep",
        default=32,
    ) # type: ignore
    
    autosave_retention_days: IntProperty(
        name="Autosave Retention Days",
        description="Number of days to keep autosave files",
        default=7,
        min=1,
        max=365,
    ) # type: ignore
    
    data_dir: StringProperty(
        name="Addon Data Directory",
        description="Root directory to store Hot Node data",
        default=str(FileManager().get_default_app_data_dir()),
        subtype='DIR_PATH',
        update=data_dir_update,
    ) # type: ignore
    
    # Development Mode
    is_dev: BoolProperty(
        name="Development Mode",
        description="Enable development mode for Hot Node (Wont having any effect in the release version).",
        default=False,
        update=is_dev_update,
    ) # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        # Nodes Adding
        col = layout.column()
        col.label(text="Nodes Adding")
        col.prop(self, "is_overwrite_tree_io")
        row = col.row(align=True)
        row.prop(self, "node_tree_reuse_mode", expand=True)
        col.separator()
        sub = col.column(align=True)
        iii = sub.row(align=True)
        sub.prop(self, "dir_to_match_image", icon='FILE_IMAGE', placeholder="Directory to match images")
        iii = sub.row(align=True)
        iii.active = self.dir_to_match_image != ""
        iii.prop(self, "image_name_filter", icon='FILTER', placeholder="Only match images having this key")

        # UI & Custom
        col.separator()
        col.separator(type='LINE')
        col.label(text="Customize")
        col.prop(self, "sidebar_category")
        
        col.separator()
        col.prop(self, "default_pack_name", text="Default Pack Name")
        col.prop(self, "default_preset_name", text="Default Preset Name")
        
        col.separator()
        col.prop(self, "is_filter_pack_by_tree_type")
        
        col.separator()
        col.prop(self, "min_ui_list_length")
        col.separator()
        col.prop(self, "sidebar_items")
        
        col.separator()
        sub = col.column(align=True)
        iii = sub.row(align=True)
        iii.prop(self, "add_nodes_menu_mode", expand=True)
        if self.add_nodes_menu_mode == 'MERGE':
            iii = sub.row(align=True)
            iii.prop(self, "merged_add_nodes_menu_label", text="Merged Menu Label")

        col.separator()
        sub = col.column(align=True)
        iii = sub.row(align=True)
        iii.prop(self, "save_nodes_menu_mode", expand=True)
        if self.save_nodes_menu_mode == 'MERGE':
            iii = sub.row(align=True)
            iii.prop(self, "merged_save_nodes_menu_label", text="Merged Menu Label")
        
        # Data
        col.separator()
        col.separator(type='LINE')
        col.label(text="Data")
        col.prop(self, "autosave_retention_days", text="Autosave Retention Days")
        
        row = col.row(align=True, heading="Custom Undo Steps")
        sub = row.row(align=True)
        sub.prop(self, "is_use_custom_undo_steps", text="")
        sub = sub.row(align=True)
        sub.active = self.is_use_custom_undo_steps
        sub.prop(self, "undo_steps", text="")
        col.prop(self, "data_dir", icon='ASSET_MANAGER')
        
        # Others
        col.separator()
        col.separator(type='LINE')
        col.label(text="Others")
        col.prop(self, "is_show_addon_new_version_info")

        # Experimental
        col.separator()
        col.separator(type='LINE')
        col.label(text="Experimental")
        col.prop(self, "is_dev", text="⚠ Development Mode")


def register():
    try:
        bpy.utils.register_class(HotNodeUserPrefs)
    except:
        pass
    
    fm = FileManager()
    user_prefs = utils.get_user_prefs()
    
    if user_prefs:
        translate_default_name(user_prefs)
        sidebar_category_update(user_prefs, bpy.context)
        fm.define_app_data_dir_structure(user_prefs.data_dir)
        fm.ensure_app_dir_structure()
        
        if user_prefs.is_dev and fm.is_path_exist(constants.HOT_NODE_ADDON_PATH / "dev"):
            from ... import dev
            dev.register()
            constants.IS_DEV = True
            constants.FILE_INDENT = 1


def unregister():
    try:
        bpy.utils.unregister_class(HotNodeUserPrefs)
    except:
        pass
    
    fm = FileManager()
    user_prefs = utils.get_user_prefs()
    
    if user_prefs:
        if user_prefs.is_dev and fm.is_path_exist(constants.HOT_NODE_ADDON_PATH / "dev"):
            from ... import dev
            dev.unregister()