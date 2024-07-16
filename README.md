Hot Node
========
Save, apply, share node presets across files in real-time, light-weight.

Requirement
--------
- Blender 4.2 compatible.

Features
--------
- Save node presets and keep them update across any .blend files in real-time.
- Load image by automaticlly seraching and set their color-space & alpha mode.
- Share nodes light-weightly without a big .blend file as it's library (usually a preset pack is smaller than 1 MiB).


Installation
--------
- Installing via [blender extension system](https://extensions.blender.org/about/).
- Or you can download the zip file and follow the [blender add-on installation guide](https://docs.blender.org/manual/en/4.2/extensions/addons.html).

After Hot Node was installed, you are able to see the Hot Node panel in node editor's sidebar.


Usage
--------
### Before Using It
- This add-on is currently in **beta**. For now it's safer not to join it into your important project workflow.
- ```Undo``` of ```Create```, ```Save```, ```Delete``` operations **haven't been supported yet**. For now you can turn on the ```Extra Comformation``` option in ```Node Preset Specials``` menu to prevent misoperation.

### Manage Preset Pack
Pack is a folder to store presets.
- To create a pack, click the ```Plus``` icon button next to the pack slot to create one.
- To select a pack, click the ```Collecetion``` icon button on the left of the pack slot, choose one in the pop-up menu.
- To rename a pack, just modify the pack name showed in the pack slot.
- To delete a pack, click the ```Trash``` icon button, the current selected pack will be deleted.

### Manage Preset
When you selected a pack:
- To create node preset, click the ```Plus``` icon button on the right of the preset select window, a new preset recording the current selected nodes will be created.
- To save node preset, select the nodes, click ```Save```, these selected nodes will be saved to the current selected preset.
- To delete preset, select the preset and click the ```Minus``` icon button on the right of the preset select window.
- To reorder presets, use the ```Up``` / ```Down``` icon button next to the preset select window.

### Apply Preset
Select a pack and a preset, click ```Apply``` button to setup nodes to the current edit tree. 
```Apply``` button will be greyed-out if node editor's window doesn't contain a node tree.

### Texture Preset Mode
Hot Node have several texture saving mode:
- ```Auto``` - Try to open image with mode ```Similar``` > ```Fixed Path``` > ```Stay Empty``` in order.
- ```Similar``` - Find the best matched image according to the name similarity algorithm in user set folder.
- ```Keys``` - Find the best matched image according to user defined keys in user set folder.
- ```Fixed Path``` - Open the same image with the original path.
- ```Stay Empty``` - Don't open image.

The default "default mode when save the preset" is ```Auto``` and can be changed in special menu.

### Texture Preset Apply Settings
In ```Textures``` > ```Apply``` panel, there are settings that influence how textures will be applied:
- ```Tolerance``` - The tolerance of the image name comparation when the texture's mode is ```Similar```, higher means that more dissimilar images can pass the comparation and be loaded rather than using fixed path & stay empty. Default 0.50 as a moderate tolerance.
- ```Folder Path``` - The directory path to try find images when in ```Auto``` / ```Similar``` / ```Keys``` mode.

### Save Texture Preset
In ```Textures``` > ```Save``` panel, you can change a image node's texture preset mode:
1. Ensure your **last saved** preset contains the image node you want to edit.
2. Select the image node, and select a ```Mode``` for this image.
3. If the mode is ```Keys```, you will need to enter key(s) for the image. You can have mutiple keys split by ```/```, e.g. ```upper_body / base_color / .png```.
4. Click ```Save Texture``` button, and this image node will follow the new setting next time you apply the preset.

### Keep Sync
When switched between .blend files and doing something to your preset in the new file, a warning may pop-up:
```
"Out of sync. Nothing happend but the add-on's auto refreshing. Now everything is ok!"
```
Just as the message said, Hot Node refreshed itself, and now you can do the things you want.
You can also refresh menually by clicking ```Refresh Data``` in Hot Node's side special menu.

### Pack Sharing
Packs can be imported / exported as zip files. In ```Pack Sharing``` panel:
- Import - Click ```Import``` button to import pack(s). The waiting-for-import pack should be in .zip format.
- Export - Click ```Export``` button to export the current selected pack as a zip file for sharing.


### Details of Usage
##### Node Tree Interface Setup
If your preset contains nodes like ```NodeGroupInput```, or your preset type is geometry, a node tree interface that contains IO sockets will be needed. But applying tree interface may destroy the current tree interface you had setted up. Hot Node will check whether the tree interface is as same as the current edit tree's, and if not, check ```Overwrite Tree IO``` option in the ```Node Preset Specials``` menu to allow overwriting tree interface, or the links heading to IO nodes won't be created.

##### Texture Reuse
If exists a image having the same name with the auto matched image when applying preset, Hot Node will compare the file size and reuse the existing one if the size is the same, rather than loading the image with unique names like image.001.

##### Node Group Reuse
If exists a node group having the same name with the group that the preset is trying to setup, Hot Node will compare every inner node of them and reuse the existing one if the two groups are totally same, rather than create a new group with unique name like NodeGroup.001.

Known Bugs
--------
- If have ```NodeFrame``` as node's parent, the frame's ```location``` will be unpredictable.


Future Plan
--------
- Maybe will support apply / save preset as a material or geometry node modifier directly on an viewport object.
- Maybe will support one-click inserting Hot Node as a module for other add-ons to easily generate nodes.
- Maybe will support undo, redo.
- Maybe will support adding linked object of the node socket if the object is simple enough.
- Maybe will support drivers of the node socket.
- Some other features...


License
--------

Hot Node as a whole is licensed under the GNU General Public License, Version 3.
Individual files may have a different, but compatible license.