import json
import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path

from ..utils import constants
from ..utils import utils


class FileManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            
            # set flags
            self.is_init_run = False # is the addon firstly installed (by detecting default app data dir)
            self.is_init_autosave_dir_exists = False # is the autosave dir exists, used to decide whether to auto update the legacy packs from 0.X
            
            if not self.get_default_app_data_dir().exists():
                self.is_init_run = True
            if self.autosave_dir.exists():
                self.is_init_autosave_dir_exists = True

            # NOTE the structure is build in ..core.blender.user_pref
            
    # data paths
    
    @property
    def app_data_dir(self) -> Path:
        return self._app_data_dir
    
    @property
    def packs_dir(self) -> Path:
        return self._packs_dir
    
    @property
    def runtime_dir(self) -> Path:
        return self._runtime_dir
    
    @property
    def history_file_dir(self) -> Path:
        return self._history_file_dir
    
    @property
    def sync_meta_path(self) -> Path:
        return self._sync_meta_path
    
    @property
    def history_meta_path(self) -> Path:
        return self._history_meta_path

    # add-on paths
    
    @property
    def app_dir(self) -> Path:
        return constants.HOT_NODE_ADDON_PATH
    
    @property
    def translations_csv_path(self) -> Path:
        return self.app_dir / "services" / "translations.csv"
    
    # temp paths
    @property
    def temp_dir(self) -> Path:
        return Path(tempfile.gettempdir())
    
    @property
    def autosave_dir(self) -> Path:
        return self.temp_dir / "hot_node_autosave"
    
    @staticmethod
    def get_default_app_data_dir() -> Path:
        if sys.platform == "win32":
            base = os.getenv("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
            app_dir: Path = Path(base) / constants.HOT_NODE_APP_DATA_DIR_NAME
        elif sys.platform == "darwin": # macOS
            app_dir: Path = Path.home() / "Library" / "Application Support" / constants.HOT_NODE_APP_DATA_DIR_NAME
        else:  # Linux/Unix
            app_dir: Path = Path.home() / constants.HOT_NODE_APP_DATA_DIR_NAME
        return app_dir

    def define_app_data_dir_structure(self, app_data_dir: Path|str|None = get_default_app_data_dir()):
        if isinstance(app_data_dir, str):
            app_data_dir = Path(app_data_dir)
        self._app_data_dir = app_data_dir
        self._packs_dir = self._app_data_dir / "packs"
        self._runtime_dir = self._app_data_dir / "runtime"
        self._history_file_dir = self._app_data_dir / "runtime" / "history_file"
        self._sync_meta_path = self._runtime_dir / ".sync.json"
        self._history_meta_path = self._runtime_dir / ".history.json"
    
    def ensure_app_dir_structure(self):
        self.ensure_dir(self._app_data_dir)
        self.ensure_dir(self._packs_dir)
        self.ensure_dir(self._runtime_dir)
        self.ensure_dir(self._history_file_dir)
        self.ensure_json(self._sync_meta_path)
        self.ensure_json(self._history_meta_path)
        
    def write_json(self, file_path: str, data: dict):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=constants.FILE_INDENT) # release None, dev 2

    def read_json(self, file_path) -> dict:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
        
    def ensure_dir(self, dir_path: Path):
        """Ensure that the specified directory exists, creating it if necessary."""
        dir_path.mkdir(parents=True, exist_ok=True)
        
    def ensure_json(self, file_path: Path):
        """Ensure that the specified file exists, creating an empty file if it does not."""
        if not file_path.exists():
            self.write_json(file_path, {})
            
    def copy_tree(self, src: Path, dst: Path):
        """Copy a directory tree from src to dst, wont overwrite if dst exists."""
        shutil.copytree(src, dst, dirs_exist_ok=True)
        
    def copy_file(self, src: Path, dst: Path):
        """Copy a file from src to dst."""
        shutil.copyfile(src, dst)
        
    def remove_tree(self, dir_path: Path):
        """Remove a directory and all its contents if path exists."""
        if dir_path.exists() and dir_path.is_dir():
            shutil.rmtree(dir_path)
            
    def remove_file(self, file_path: Path):
        """Remove a file if it exists."""
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            
    def remove_path(self, path: Path):
        """Remove a file or directory if path exists."""
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            
    def remove_paths(self, paths: list[Path]):
        """Remove multiple files or directories if path exists."""
        for path in paths:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.is_file():
                    path.unlink()
        
    def rename_path_tail(self, file_or_dir_path: Path, new_name: str, suffix: str = ""):
        os.rename(file_or_dir_path, file_or_dir_path.parent / (new_name + suffix))
        
    def read_dir_file_names(self, dir_path, suffix, cull_suffix=True):
        """Read file names in a directory with a specific suffix."""
        existing_file_names = os.listdir(dir_path)
        filtered_file_names: list[str] = []
        if cull_suffix:
            suffix_length = len(suffix)
            for file_name in existing_file_names:
                if file_name.endswith(suffix):
                    filtered_file_names.append(file_name[:-suffix_length])
        else:
            for file_name in existing_file_names:
                if file_name.endswith(suffix):
                    filtered_file_names.append(file_name)
        return filtered_file_names
    
    def read_dir_file_names_with_suffixes(self, dir_path, suffixes: tuple):
        """Read file names in a directory with specific suffixes. The result contains suffix."""
        file_names = os.listdir(dir_path)
        file_names = [file_name for file_name in file_names if file_name.endswith(suffixes)]
        return file_names
                
    def unzip_to(self, src_zip_path: Path, dst_dir_path: Path):
        """dst_zip_path is the dir that contains the unzipped files, not the dir containing the unzipped dir."""
        file = zipfile.ZipFile(src_zip_path)
        file.extractall(dst_dir_path)
        file.close()
        
    def zip_to(self, src_dir_path: Path, dst_zip_path: Path):
        zip = zipfile.ZipFile(dst_zip_path, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(src_dir_path):
            relative_root = os.path.relpath(root, src_dir_path)
            if relative_root == '.':
                relative_root = ''
            else:
                relative_root += os.sep
            for filename in files:
                zip.write(os.path.join(root, filename), relative_root + filename)
        zip.close()
        
    def ensure_path_is_dir(self, path: Path):
        """Ensure that the given path is a directory, if it's a file path, get the file's parent dir path."""
        # if it's a file path, get the dir path of it using dirname()
        path = Path(path)
        if path.is_dir():
            return path
        return path.parent
    
    def is_path_exist(self, path: Path|str) -> bool:
        """Check if the given path exists."""
        if isinstance(path, str):
            path = Path(path)
        return path.exists()
    
    def join_str_to_path(self, *args: str) -> Path:
        """Join multiple path components into a single path."""
        return Path(*args)
    
    def join_strs_to_str_path(self, *args: str) -> str:
        """Join multiple string path components into a single Path object."""
        return str(Path(*args))
    
    def path_to_str(self, path: Path) -> str:
        """Convert a Path object to a string."""
        return str(path)
    
    def str_to_path(self, path_str: str) -> Path:
        """Convert a string to a Path object."""
        return Path(path_str)
    
    def get_base_name(self, path: Path|str) -> str:
        """Get the base name of a file or directory."""
        if isinstance(path, str):
            path = Path(path)
        return path.name
    
    def get_base_names(self, paths: list[Path|str]) -> list[str]:
        """Get the base names of multiple files or directories."""
        return [self.get_base_name(path) for path in paths]
    
    def abspath(self, path: Path|str) -> str:
        """Get the absolute path of a file or directory."""
        if isinstance(path, str):
            path = Path(path)
        return str(path.resolve())
    
    def is_valid_dir_str(self, path: str):
        if not path or not isinstance(path, str):
            return False
        if any(char in path for char in '<>"|?*'):
            return False
        if len(path) > 260:
            return False
        if not os.path.isdir(path):
            return False
        return True

    def open_path_with_default_browser(self, path: Path|str):
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', path])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            pass