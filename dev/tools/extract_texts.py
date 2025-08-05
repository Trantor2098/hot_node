"""This script extracts text items from Python files in the Hot Node add-on directory for translation purposes."""

import os
import re
import csv

def find_text_strings(root_dir):
    text_strings = set()
    patterns = [
        r'text\s*=\s*[\'"](.*?)[\'"]',
        r'report_error\s*\(\s*[\'"](.*?)[\'"]',
        r'report_warning\s*\(\s*[\'"](.*?)[\'"]',
        r'report_finish\s*\(\s*[\'"](.*?)[\'"]',
        r'iface_\s*\(\s*[\'"](.*?)[\'"]',
        r'bl_label\s*=\s*[\'"](.*?)[\'"]',
        r'bl_description\s*=\s*[\'"](.*?)[\'"]',
        r'placeholder\s*=\s*[\'"](.*?)[\'"]',
        r'description\s*=\s*[\'"](.*?)[\'"]',
        r'heading\s*=\s*[\'"](.*?)[\'"]',
        r'title\s*=\s*[\'"](.*?)[\'"]',
        r'confirm_text\s*=\s*[\'"](.*?)[\'"]',
        r'message\s*=\s*[\'"](.*?)[\'"]',
    ]
    exclude_dirs = {os.path.join(root_dir, 'dev'), os.path.join(root_dir, 'utils')}
    for folder, _, files in os.walk(root_dir):
        # exclude dev, utils
        if any(os.path.abspath(folder).startswith(os.path.abspath(ex)) for ex in exclude_dirs):
            continue
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(folder, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # Special pattern for user_pref.py
                    if os.path.basename(file_path) in ('user_pref.py', 'ui_context.py'):
                        name_matches = re.findall(r'name\s*=\s*[\'"](.*?)[\'"]', content)
                        filtered_name = [m for m in name_matches if m.strip()]
                        if filtered_name:
                            text_strings.update(filtered_name)
                        for text in filtered_name:
                            print(f"{file} (name): {text}")
                    for pat in patterns:
                        matches = re.findall(pat, content)
                        filtered = [m for m in matches if m.strip()]
                        if filtered:
                            text_strings.update(filtered)
                        for text in filtered:
                            print(f"{file}: {text}")
                except Exception:
                    pass
    return text_strings

def read_existing_msgids(csv_path):
    msgids = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            msgids.add(row['msgid'])
    return msgids

def append_new_msgids(csv_path, new_msgids):
    # check enter
    with open(csv_path, 'rb+') as f:
        f.seek(0, os.SEEK_END)
        if f.tell() > 0:
            f.seek(-1, os.SEEK_END)
            last_char = f.read(1)
            if last_char != b'\n':
                f.write(b'\n')
    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for msgid in new_msgids:
            writer.writerow(['*', msgid])
            
def extract_texts():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    module_dir = base_dir
    
    csv_path = os.path.join(base_dir, "dev", "tools", 'translations.csv')
    temp_csv_path = os.path.join(base_dir, "dev", "tools", "translations_wip.csv")
    
    text_strings = find_text_strings(module_dir)
    existing_msgids = read_existing_msgids(csv_path)
    new_msgids = [s for s in text_strings if s and s not in existing_msgids]
    
    if new_msgids:
        print()
        print("--------- Extract Results ---------")
        append_new_msgids(temp_csv_path, new_msgids)
        print(f"Added {len(new_msgids)} text items to translations.csv")
    else:
        print("No new text items found to add.")
    return text_strings
    
def collect_unused_texts(needed_text_strings):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    module_dir = base_dir
    
    csv_path = os.path.join(base_dir, "dev", "tools", 'translations.csv')
    temp_csv_path = os.path.join(base_dir, "dev", "tools", "translations_unused.csv")
    
    existing_msgids = read_existing_msgids(csv_path)

    unused_msgids = [s for s in existing_msgids if s and s not in needed_text_strings]
    if unused_msgids:
        print()
        print("------- Unused Results ---------")
        append_new_msgids(temp_csv_path, unused_msgids)
        print(f"Collected {len(unused_msgids)} unused text items.")
    else:
        print("No unused text items found.")

def main():
    text_strings = extract_texts()
    collect_unused_texts(text_strings)

if __name__ == '__main__':
    main()
