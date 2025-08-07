import shutil
import os

def ignore_git(dir, files):
    return {'.git'} if '.git' in files else set()

def dispatch_pkg(src_dir, dst_dir):
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir, ignore=ignore_git)

if __name__ == "__main__":
    src = r"c:\Users\Trantor\AppData\Roaming\Blender Foundation\Blender\5.0\extensions\user_default\hot_node"
    dst = r"c:\Users\Trantor\AppData\Roaming\Blender Foundation\Blender\4.3\extensions\user_default\hot_node"
    dispatch_pkg(src, dst)