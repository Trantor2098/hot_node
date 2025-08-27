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


def _collect_python_files():
    """Collect all python file contents (excluding dev directory)."""
    root_dir = Path(__file__).parent.parent.parent
    dev_dir = root_dir / "dev"
    files = {}
    for path in root_dir.rglob('*.py'):
        try:
            path.relative_to(dev_dir)
            continue
        except ValueError:
            pass
        try:
            files[path] = path.read_text(encoding='utf-8')
        except Exception:
            continue
    return root_dir, files


def check_file_indent(file_text: str):
    import ast
    file_indent = None
    for line in file_text.splitlines():
        if line.strip().startswith("FILE_INDENT"):
            try:
                file_indent = ast.literal_eval(line.split("=", 1)[1].strip())
            except Exception:
                file_indent = line.split("=", 1)[1].strip()
            break
    if file_indent is None:
        print("✔  FILE_INDENT")
    else:
        print(f"⚠  FILE_INDENT: {file_indent} (should be None in release)")
        return False
    return True


def check_app_data_dir_name(file_text: str):
    import ast
    app_data_dir_name = None
    for line in file_text.splitlines():
        if line.strip().startswith("HOT_NODE_APP_DATA_DIR_NAME"):
            try:
                app_data_dir_name = ast.literal_eval(line.split("=", 1)[1].strip())
            except Exception:
                app_data_dir_name = line.split("=", 1)[1].strip()
            break
    if app_data_dir_name == "HotNodeAddon":
        print("✔  HOT_NODE_APP_DATA_DIR_NAME")
    else:
        print(f"⚠  HOT_NODE_APP_DATA_DIR_NAME: {app_data_dir_name} (should be \"HotNodeAddon\" in release)")
        return False
    return True


def check_print_statements(root_dir: Path, files: dict):
    import tokenize, io

    def first_arg_starts_with_hot_node(args_src: str) -> bool:
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(args_src).readline))
        except tokenize.TokenError:
            return False
        for tok_type, tok_str, *_ in tokens:
            if tok_type == tokenize.STRING:
                m = re.match(r'(?i)^[furb]*([\'\"])(.*)\1$', tok_str)
                if not m:
                    inner = tok_str.lstrip('fFrRuUbB')
                    if len(inner) >= 2 and inner[0] in ('"', "'") and inner[-1] == inner[0]:
                        inner = inner[1:-1]
                else:
                    inner = m.group(2)
                return inner.startswith('[Hot Node]')
            elif tok_type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
                continue
            else:
                return False
        return False

    offenders = []
    for path, text in files.items():
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            code_part = line.split('#', 1)[0]
            idx = code_part.find('print(')
            if idx == -1:
                i += 1
                continue
            after = code_part[idx + len('print('):]
            paren_depth = 1
            collected = after
            j = i
            while paren_depth > 0 and j < len(lines):
                tmp = re.sub(r'".*?"|\'.*?\'', '', collected)
                paren_depth = paren_depth - tmp.count(')') + tmp.count('(')
                if paren_depth > 0:
                    j += 1
                    if j < len(lines):
                        collected += '\n' + lines[j]
            args_src = collected.rsplit(')', 1)[0]
            if not first_arg_starts_with_hot_node(args_src):
                rel_path = path.relative_to(root_dir)
                offenders.append((str(rel_path), i + 1, line.strip()))
            i = j + 1 if j > i else i + 1

    if not offenders:
        print("✔  No unexpected print statements.")
    else:
        for rel_path, lineno, snippet in offenders:
            print(f"⚠  {rel_path}:{lineno}: {snippet}")
        return False
    return True


def check_existing_builds(output_dir, hot_node_version, is_overwrite_build):
    if not os.path.exists(output_dir):
        print(f"⚠  {output_dir} does not exist.")
        return False

    output_zip = os.path.join(output_dir, f"hot_node-{hot_node_version}.zip")
    if os.path.exists(output_zip) and not is_overwrite_build:
        print(f"⚠  {output_zip} already exists.")
        return False
    print(f"✔  Output zip path is valid.")
    return True


def check(output_dir, hot_node_version, is_overwrite_build):
    root_dir, files = _collect_python_files()
    constants_path = root_dir / 'utils' / 'constants.py'
    constants_text = files.get(constants_path, '')
    print()
    print("---------------- Start Code Checking Results ----------------")
    result = check_existing_builds(output_dir, hot_node_version, is_overwrite_build)
    result &= check_file_indent(constants_text)
    result &= check_app_data_dir_name(constants_text)
    result &= check_print_statements(root_dir, files)
    print("----------------- End Code Checking Results -----------------")
    print()
    return result


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
    hot_node_version = "1.0.8"
    is_overwrite_build = False
    
    blender_path=r"D:\Software\Software_B\Blender\Blender 4.5\blender.exe"
    source_dir=str(Path(__file__).parent.parent.parent)
    output_dir=r"E:\Alpha\Proj\hot_node\builds"

    if not check(output_dir, hot_node_version, is_overwrite_build):
        print("Build Canceled")
        return

    write_version_to_files(hot_node_version)
    
    # build settings are defined in blender_manifest.toml
    build(
        blender_path=blender_path,
        source_dir=source_dir,
        output_dir=output_dir,
    )
    
if __name__ == "__main__":
    main()