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


from . import core
from . import services


bl_info = {
    "name": "Hot Node",
    "author": "Trantor",
    "version": (1, 0, 8),
    "blender": (4, 2, 0),
    "location": "Node Editor > Sidebar > Hot Node",
    "description": "Save nodes, add nodes as adding node",
    "warning": "",
    "wiki_url": "https://github.com/Trantor2098/hot_node",
    "category": "Node",
    "tracker_url": "https://github.com/Trantor2098/hot_node"
}


def register():
    core.startup()
    services.enable_all()


def unregister():
    services.disable_all()
    core.shutdown()