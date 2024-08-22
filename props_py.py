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


# ======== About Packs & Presets
# TODO put presets in packs
class Pack():
    
    contain_shader_tree = False
    contain_geometry_tree = False
    contain_compositor_tree = False
    contain_texture_tree = False
    
    def __init__(self, name):
        self.name = name
        
# packs will be loaded once the blender open
gl_packs = {}
# for script to get current selected pack, for CRUDing it.
gl_pack_selected: Pack = None
# only for checking rename as a name cache, wont be used to get preset
gl_preset_selected = ""


# ======== About Operators
# When invoking helper ops, these will be passed into the helper to decide helper's actions.
helper_mode = 'NONE'
helper_param = None
report_type = ''
report_message = ""
gui_info = ""


# ======== About History
# for undo_post and redo_post not to sync the checker and the checker cache
skip_step_checker_update = False


# ======== About Hot Node Props
skip_pack_rename_callback = False
skip_preset_rename_callback = False
skip_fast_create_preset_name_callback = False
skip_preset_selected_callback = False