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

from . import props_py


def refresh():
    bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')
    
    
def late_refresh():
    bpy.app.timers.register(refresh)


def update_pack_menu_for_pack_renaming(new_pack_name):
    props_py.helper_mode = 'PACK_RENAME'
    props_py.helper_param = new_pack_name
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')