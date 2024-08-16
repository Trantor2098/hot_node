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


# Cache of Packs & Presets
class Pack():
    def __init__(self, name, mtime):
        self.name = name
        self.mtime = mtime
        
        
# packs will be loaded once the blender open
gl_packs = {}
# for script to get current selected pack, for CRUDing it.
gl_pack_selected: Pack = None
# only for checking rename as a name cache, wont be used to get preset
gl_preset_selected = ""


# When invoking helper ops, these will be passed into the helper to decide helper's actions.
helper_mode = 'NONE'
helper_param = None