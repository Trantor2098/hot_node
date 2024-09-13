import bpy
import rna_keymap_ui

kms_kmis = []


def draw_kmis(layout):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    km = kc.keymaps['Node Editor']
    for km, kmi in kms_kmis:
        if kmi:
            rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0)
    kmi = km.keymap_items.get("node.hot_node_preset_apply", None)


def register():
    wm = bpy.context.window_manager
    kc: bpy.types.KeyConfig = wm.keyconfigs.addon
    if not kc:
        print("Hot Node: Keymap registration failed, no keyconfig found.")
        return

    # register to object tab
    km = kc.keymaps.new(name="Node Editor", space_type='NODE_EDITOR') # type: bpy.types.KeyMap
    # menu caller is actually a ops, we need to set it's properties, the name is the name of the menu to be called
    kmi = km.keymap_items.new("wm.call_menu", "L", "PRESS", ctrl=1, shift=1)
    kmi.properties.name = "HOTNODE_MT_nodes_add_in_one"
    kms_kmis.append((km, kmi))
    
    kmi = km.keymap_items.new("node.hot_node_preset_apply", "K", "PRESS", shift=1)
    kms_kmis.append((km, kmi))
    
    kmi = km.keymap_items.new("wm.call_menu", "A", "DOUBLE_CLICK", shift=1)
    kmi.properties.name = "HOTNODE_MT_nodes_add_in_one"
    kms_kmis.append((km, kmi))
    
    
def unregister():
    for km, kmi in kms_kmis:
        km.keymap_items.remove(kmi)

    kms_kmis.clear()
