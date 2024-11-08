import json
file_path = r"C:\Users\Trantor\AppData\Roaming\Blender Foundation\Blender\4.2\extensions\user_default\hot_node\preset_packs\Pack\Preset.json"
with open(file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)
with open(file_path, 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=1)