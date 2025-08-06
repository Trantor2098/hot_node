import csv
import os

def gen_translations_dict(csv_path):
    translations = {
        "en_US": {},
        "zh_HANS": {},
    }
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            msgctxt = row["msgctxt"]
            msgid = row["msgid"]
            zh_HANS = row["zh_HANS"]
            key = (msgctxt, msgid)
            translations["en_US"][key] = msgid
            translations["zh_HANS"][key] = zh_HANS
    return translations

def write_to_i18n_py(translations, i18n_py_path):
    # 只替换 Translations 类中的 translations 字典
    with open(i18n_py_path, encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    in_class = False
    replaced = False
    for line in lines:
        if line.strip().startswith('class Translations'):
            in_class = True
            new_lines.append(line)
            continue
        if in_class and line.strip().startswith('translations ='):
            new_lines.append(f'    translations = {repr(translations)}\n')
            replaced = True
            in_class = False
            continue
        if not (in_class and not replaced):
            new_lines.append(line)
    with open(i18n_py_path, 'w', encoding="utf-8") as f:
        f.writelines(new_lines)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    csv_path = os.path.join(base_dir, 'dev', 'tools', 'translations.csv')
    i18n_py_path = os.path.join(base_dir, 'services', 'i18n.py')
    translations = gen_translations_dict(csv_path)
    write_to_i18n_py(translations, i18n_py_path)
