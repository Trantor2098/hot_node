import os
import re
import subprocess
from pathlib import Path


def write_version_to_files(version_str: str):
    """
    Update version in utils/constants.py, __init__.py, and blender_manifest.toml.
    
    :param version_str: The version string to set, e.g. "1.0.0", "1.2.21-alpha.3".
    """
    dash_index = version_str.find('-')
    suffix = ""
    if dash_index != -1:
        version_str_body = version_str[:dash_index]
        suffix = version_str[dash_index:]
    else:
        version_str_body = version_str
        
    version_tuple = tuple(map(int, version_str_body.split('.')))
    version_list = [int(x) for x in version_str_body.split('.')]
    
    # 1. Update utils/constants.py
    constants_path = Path(__file__).parent.parent.parent / "utils" / "constants.py"
    with constants_path.open("r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r'HOT_NODE_VERSION\s*=\s*\[[^\]]*\]', f'HOT_NODE_VERSION = {version_list}', content)
    with constants_path.open("w", encoding="utf-8") as f:
        f.write(new_content)

    # 2. Update __init__.py
    init_path = Path(__file__).parent.parent.parent / "__init__.py"
    with init_path.open("r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r'("version"\s*:\s*)\([^)]*\)', f'"version": {version_tuple}', content)
    with init_path.open("w", encoding="utf-8") as f:
        f.write(new_content)

    # 3. Update blender_manifest.toml
    manifest_path = Path(__file__).parent.parent.parent / "blender_manifest.toml"
    with manifest_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("version ="):
            lines[i] = f'version = "{version_str}"\n'
            break
    with manifest_path.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def check_code():
    import ast
    constants_path = Path(__file__).parent.parent.parent / "utils" / "constants.py"
    with constants_path.open("r", encoding="utf-8") as f:
        content = f.read()
    file_indent = None
    app_data_dir_name = None
    for line in content.splitlines():
        if line.strip().startswith("FILE_INDENT"):
            try:
                file_indent = ast.literal_eval(line.split("=", 1)[1].strip())
            except Exception:
                file_indent = line.split("=", 1)[1].strip()
        if line.strip().startswith("HOT_NODE_APP_DATA_DIR_NAME"):
            try:
                app_data_dir_name = ast.literal_eval(line.split("=", 1)[1].strip())
            except Exception:
                app_data_dir_name = line.split("=", 1)[1].strip()
    
    print()
    print("---------------- Code Checking Results ----------------")
    if file_indent is None:
        print("✔  FILE_INDENT")
    else:
        print(f"⚠  FILE_INDENT: {file_indent} (should be None in release)")
    if app_data_dir_name == "HotNodeAddon":
        print("✔  HOT_NODE_APP_DATA_DIR_NAME")
    else:
        print(f"⚠  HOT_NODE_APP_DATA_DIR_NAME: {app_data_dir_name} (should be HotNodeAddon in release)")
    print("-------------------------------------------------------")


def build(
    blender_path="blender",
    source_dir=None,
    output_dir=None,
    output_filepath=None,
    valid_tags_json=None,
    split_platforms=False,
    verbose=False
):
    cmd = [blender_path, "--command", "extension", "build"]
    if source_dir:
        cmd += ["--source-dir", source_dir]
    if output_dir:
        cmd += ["--output-dir", output_dir]
    if output_filepath:
        cmd += ["--output-filepath", output_filepath]
    if valid_tags_json:
        cmd += ["--valid-tags", valid_tags_json]
    if split_platforms:
        cmd.append("--split-platforms")
    if verbose:
        cmd.append("--verbose")

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)
    os.startfile(output_dir)


def main():
    # Write the version to __init__.py, blender_manifest.toml, and utils/constants.py
    write_version_to_files("1.0.2")
    
    # build settings are defined in blender_manifest.toml
    build(
        blender_path=r"D:\Software\Software_B\Blender\Blender 4.5\blender.exe",
        source_dir=str(Path(__file__).parent.parent.parent),
        output_dir=r"E:\Alpha\Proj\hot_node\builds",
    )
    check_code()
    
if __name__ == "__main__":
    main()