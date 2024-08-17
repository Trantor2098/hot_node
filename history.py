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

from . import file, ops_invoker


class Step():
    
    def __init__(self, context: bpy.types.Context, deleted_paths: list=[], changed_paths: list=[], created_paths: list=[]):
        global steps, undid_steps, step_num_cache
            
        self.deleted_paths = deleted_paths
        self.his_deleted_paths = file.push_history(deleted_paths, "delete")
        self.changed_paths = changed_paths
        self.his_changed_paths = file.push_history(changed_paths, "change")
        self.created_paths = created_paths
        self.his_created_paths = []
        
        steps.appendleft(self)
        step_num_cache += 1
        context.scene.hot_node_props.step_num += 1
        undid_steps.clear()
    
    def undo(self):
        self.his_created_paths = file.push_history(self.created_paths, "create")
        file.del_paths(self.created_paths)
        file.pull_history(self.deleted_paths, self.his_deleted_paths)
        file.pull_history(self.changed_paths, self.his_changed_paths)
        
    def redo(self):
        file.pull_history(self.created_paths, self.his_created_paths)
        file.pull_history(self.changed_paths, self.his_changed_paths)
        self.his_deleted_paths = file.push_history(self.deleted_paths, "delete")


steps: deque[Step] = deque(maxlen=16)
undid_steps: list[Step] = []
step_num_cache = 0


def undo(scene, _):
    global steps, step_num_cache
    step_num = scene.hot_node_props.step_num
    # if we are undoing hot node's operators, the step_num will decrease by one and be detected (blender did this), 
    # which will bring us into our undo logic
    if step_num_cache > step_num:
        # if step_num is bigger than 2147483647... but who cares?
        step_num_cache = step_num
        step = steps.popleft()
        undid_steps.append(step)
        step.undo()
        ops_invoker.refresh()
        
        
def redo(scene, _):
    global steps, step_num_cache
    props = scene.hot_node_props
    step_num = props.step_num
    # if we are undoing hot node's operators, the step_num will increase by one and be detected (blender did this), 
    # which will bring us into our undo logic
    print('============')
    print('I am redoing')
    if step_num > step_num_cache:
        scene.hot_node_props.step_num = step_num_cache
        step = undid_steps.pop()
        steps.appendleft(step)
        step.redo()
        ops_invoker.refresh()
        # props.step_num will be added back by blender's undo logic


def register():
    bpy.app.handlers.undo_post.append(undo)
    bpy.app.handlers.redo_post.append(redo)


def unregister():
    bpy.app.handlers.undo_post.remove(undo)
    bpy.app.handlers.redo_post.remove(redo)