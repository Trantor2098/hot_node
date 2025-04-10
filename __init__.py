# BEGIN GPL LICENSE BLOCK #####
#
# This file and the files staying in the folder containing this file
# are part of Hot Node.
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
    "version": (0, 7, 10),
    "blender": (4, 2, 0),
    "location": "Node Editor > Sidebar > Hot Node",
    "description": "Save nodes, add nodes as adding node",
    "warning": "",
    "wiki_url": "https://github.com/Trantor2098/hot_node",
    "category": "Node",
    "tracker_url": "https://github.com/Trantor2098/hot_node"
}

module_name = __name__

import bpy
from bpy.app.handlers import persistent


def dev_reload():
    import importlib
    from . import gui, operators, file, props_bl, ops_invoker, versioning, history, preferences, utils, node_parser, node_setter, props_py, sync, preferences, constants, keymap
    importlib.reload(props_bl)
    importlib.reload(props_py)
    importlib.reload(gui)
    importlib.reload(operators)
    importlib.reload(ops_invoker)
    importlib.reload(node_parser)
    importlib.reload(node_setter)
    importlib.reload(utils)
    importlib.reload(file)
    importlib.reload(sync)
    importlib.reload(history)
    importlib.reload(versioning)
    importlib.reload(preferences)
    importlib.reload(constants)
    importlib.reload(keymap)
    
    
@persistent
def load_handler(_):
    '''Will be called after a file is loaded.'''
    # ensure the bl props are correct
    from . import i18n
    i18n.select_language()
    from . import props_bl, ops_invoker, history, preferences
    preferences.unregister()
    props_bl.unregister()
    history.unregister()
    preferences.register()
    props_bl.register()
    history.register()
    
    ops_invoker.late_refresh()

    
def register():
    # dev_reload()
    
    from . import i18n
    i18n.select_language()
    
    from . import gui, operators, file, props_bl, ops_invoker, history, preferences, keymap
    
    file.init()
    
    preferences.register()
    props_bl.register()
    gui.register()
    operators.register()
    history.register()
    keymap.register()
    
    # for reloading add-on
    ops_invoker.late_refresh()
    # for opening a new file (maybe the file lasts some legacy hot node data)
    bpy.app.handlers.load_post.append(load_handler)


def unregister():
    from . import gui, operators, file, props_bl, history, preferences, keymap
    
    file.finalize()
    
    preferences.unregister()
    gui.unregister()
    operators.unregister()
    props_bl.unregister()
    history.unregister()
    keymap.unregister()
    
    bpy.app.handlers.load_post.remove(load_handler)
    dev_reload()