import bpy
import rna_keymap_ui

kms_kmis = []

def draw_kmis(box):
    
    wm = bpy.context.window_manager
    kc = getattr(wm.keyconfigs, "user", None)
    km = kc.keymaps["Node Editor"]

    # TODO optimize this search
    for kmi in km.keymap_items:
        if kmi.idname == "wm.call_menu":
            menu_name = getattr(kmi.properties, "name", "")
            if menu_name == "HOTNODE_MT_merged_add_nodes_packs":
                add_nodes_menu_kmi = kmi
            elif menu_name == "HOTNODE_MT_merged_save_nodes_packs":
                save_nodes_menu_kmi = kmi
        
    box.context_pointer_set("keymap", km)
    rna_keymap_ui.draw_kmi([], kc, km, add_nodes_menu_kmi, box, 0)
    
    box.context_pointer_set("keymap", km)
    rna_keymap_ui.draw_kmi([], kc, km, save_nodes_menu_kmi, box, 0)
    
    kmi = km.keymap_items.get("hotnode.overwrite_clipboard_preset_with_selection")
    box.context_pointer_set("keymap", km)
    rna_keymap_ui.draw_kmi([], kc, km, kmi, box, 0)
    
    kmi = km.keymap_items.get("hotnode.add_clipboard_preset_nodes_to_tree")
    box.context_pointer_set("keymap", km)
    rna_keymap_ui.draw_kmi([], kc, km, kmi, box, 0)

def register():
    wm = bpy.context.window_manager
    kc: bpy.types.KeyConfig = wm.keyconfigs.addon
    if not kc:
        print("[Hot Node] Keymap registration failed, no keyconfig found.")
        return

    # register to Node Editor Table
    km = kc.keymaps.new(name="Node Editor", space_type='NODE_EDITOR') # type: bpy.types.KeyMap
    kmis = km.keymap_items
    # menu caller is actually a ops, we need to set it's properties, 
    # the name is the name of the menu to be called
    
    kmi = kmis.new("wm.call_menu", "A", "PRESS", ctrl=1, shift=1)
    kmi.properties.name = "HOTNODE_MT_merged_add_nodes_packs"
    kms_kmis.append((km, kmi))
    
    kmi = kmis.new("wm.call_menu", "A", "PRESS", ctrl=1, shift=1, alt=1)
    kmi.properties.name = "HOTNODE_MT_merged_save_nodes_packs"
    kms_kmis.append((km, kmi))
    
    kmi = kmis.new("hotnode.overwrite_clipboard_preset_with_selection", "C", "PRESS", ctrl=1, shift=1)
    kms_kmis.append((km, kmi))
    
    kmi = kmis.new("hotnode.add_clipboard_preset_nodes_to_tree", "V", "PRESS", ctrl=1, shift=1)
    kms_kmis.append((km, kmi))
    
    
def unregister():
    for km, kmi in kms_kmis:
        km.keymap_items.remove(kmi)

    kms_kmis.clear()
    # pass
