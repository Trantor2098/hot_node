# BEGIN GPL LICENSE BLOCK #####
#
# This file is part of Hot Node.
#
# Hot Node is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# Hot Node is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hot Node. If not, see <https://www.gnu.org/licenses/>.
#
# END GPL LICENSE BLOCK #####


import bpy

from collections import deque
from abc import abstractmethod, ABCMeta

from . import file


history = deque(maxlen=16)


class IStep(metaclass=ABCMeta):
    
    ori_path = ""
    his_path = ""
    
    def record(self, ori_path):
        self.ori_path = ori_path
        self.his_path = file.save_history(ori_path)
    
    @abstractmethod
    def undo(self, context: bpy.types.Context):
        pass
    @abstractmethod
    def redo(self, context: bpy.types.Context):
        pass


class PackCreate(IStep):
    
    def record(self, context):
        pass
    def undo(self, context):
        pass
    def redo(self, context):
        pass
    
    
class PackDelete(IStep):
    
    def __init__(self, pack_name):
        super().record((file.get_pack_path(pack_name)))
    
    def undo(self, context):
        pass
    def redo(self, context):
        pass


def record(mode: str):
    if mode == 'PACK_CREATE':
        pass
    elif mode == 'PACK_DELETE':
        pass
    elif mode == 'PACK_RENAME':
        pass
    elif mode == 'PRESET_CREATE':
        pass
    elif mode == 'PRESET_DELETE':
        pass
    elif mode == 'PRESET_SAVE':
        pass
    elif mode == 'PRESET_RENAME':
        pass
    elif mode == 'PRESET_CLEAR':
        pass
    elif mode == 'PRESET_MOVE':
        pass


def undo():
    pass