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


from . import node_parser, file

# current Hot Node's version
version = [0, 2, 0]


def check_update_version(preset_name,cpreset):
    '''If trying to apply preset, CALL THIS FIRST'''
    cdata = cpreset["HN_preset_data"]
    preset_version = cdata["version"]
    if preset_version != version:
        if preset_version == [0, 1, 0]:
            cpreset = version_update_0_1_0(preset_name, cpreset)
    return cpreset
    
    
def version_update_0_1_0(preset_name, cpreset):
    cdata = cpreset["HN_preset_data"]
    pack_name = cdata["pack_name"]
    cpreset = node_parser.set_preset_data(preset_name, pack_name, cpreset=cpreset)
    file.update_preset(preset_name, cpreset)
    return cpreset