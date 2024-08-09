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


bl_info = {
    "name": "Hot Node",
    "author": "Trantor2098",
    "version": (0, 5, 0),
    "blender": (4, 2, 0),
    "location": "Node Editor > Sidebar > Hot Node",
    "description": "Save nodes, add nodes as adding node",
    "warning": "",
    "wiki_url": "https://github.com/Trantor2098/hot_node",
    "category": "Node",
    "tracker_url": "https://github.com/Trantor2098/hot_node"
}


import bpy

from . import gui, operators, file, props_bl


def dev_reload():
    import importlib
    from . import utils, file, node_parser, node_setter, version_control, props_py
    importlib.reload(gui)
    importlib.reload(props_bl)
    importlib.reload(props_py)
    importlib.reload(operators)
    importlib.reload(node_parser)
    importlib.reload(node_setter)
    importlib.reload(utils)
    importlib.reload(file)
    importlib.reload(version_control)
    
    
# Functions for Calling Operators
def execute_refresh():
    try:
        bpy.ops.node.hot_node_refresh('EXEC_DEFAULT')
        return None
    except AttributeError:
        # '_RestrictContext' object has no attribute 'view_layer'
        # if the registing is not finished yet, bpy.app.timer will take another 0.1s wait to call this func again
        return 0.1


def register():
    dev_reload()
    
    file.init()

    gui.register()
    props_bl.register()
    operators.register()
    
    bpy.app.timers.register(execute_refresh, first_interval=0.1)


def unregister():
    file.finalize()
    
    gui.unregister()
    props_bl.unregister()
    operators.unregister()