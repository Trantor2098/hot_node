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

from . import file, props_py, props_bl, gui, ops_invoker, states


def sync(context: bpy.types.Context|None=None):
    # file.refresh_root_meta_cache()
    file.ensure_pack_root()
    pack_names = file.load_packs()
    file.refresh_root_meta_cache()
    pack_selected = props_py.gl_pack_selected
    if pack_selected is None or not pack_selected.name in pack_names:
        pack_selected_name = file.root_meta_cache["pack_selected"]
        pack_selected = props_py.gl_pack_selected = props_py.gl_packs.get(pack_selected_name, None)
    # we can't modify the bl props via gui's context. invoke ops instead to do it in another thread.
    if context is None:
        ops_invoker.late_call_helper_ops('PACK_SELECT', pack_selected.name)
    else:
        props_bl.select_pack(context, pack_selected)
    gui.ensure_existing_pack_menu()
    
    
def _ensure_sync(ops: bpy.types.Operator, context: bpy.types.Context):
    if not file.check_sync():
        sync(context)
        ops.report({'WARNING'}, "Out of sync, nothing happend but auto refreshing. Now it's READY!")
        return False
    return True