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


def call_helper_ops_directly():
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')


def call_helper_ops(mode: str, param):
    '''Call helpder ops, pass <mode> <param> into the ops.
    
    - mode: Enum in 'PACK_RENAME', 'PACK_SELECT'.'''
    props_py.helper_mode = mode
    props_py.helper_param = param
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')
    
    
def late_call_helper_ops(mode, param):
    props_py.helper_mode = mode
    props_py.helper_param = param
    bpy.app.timers.register(call_helper_ops_directly)


def refresh():
    bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')

    
def late_refresh(interval=0.0):
    bpy.app.timers.register(refresh, first_interval=interval)
    
    
def update_pack_menu_for_pack_renaming(new_pack_name):
    props_py.helper_mode = 'PACK_RENAME'
    props_py.helper_param = new_pack_name
    bpy.ops.node.hot_node_helper('EXEC_DEFAULT')