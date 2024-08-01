Hot Node
========

Save nodes, then add nodes like adding node, without library.

Features
--------

- Save any nodes and their attributes, then add nodes just like adding a single node, fast and cross-file.
- Load image by automatically seraching and set their color-space & alpha mode.
- Store / share nodes packs light-weightly without a big .blend file as it's library (usually smaller than 1 MiB).


Requirement
--------

- Blender 4.2 compatible.
- For blender 4.0 - 4.1, 


Installation
--------

- In blender, at ```Edit``` > ```Preferences``` > ```Get Extensions```, search Hot Node and click ```Install```.
- Or Installing via [blender extension system](https://extensions.blender.org/about/).
- Or you can download the zip file and follow the [blender add-on installation guide](https://docs.blender.org/manual/en/4.2/extensions/addons.html).

After Hot Node was installed, you are able to see the Hot Node panel in node editor's sidebar.


Before Using It
--------

**EXPORT ALL NODE PRESET PACKS BEFORE UPDATING / UNINSTALL HOT NODE**

Because nodes data is stored in add-on's path and will be deleted by blender's extension system without warning.

Usage
--------

### Presets
Presets are nodes templetes that can be stored, modified, applied.

##### Manage & Apply Presets
You can manage & apply presets across .blend files:
- **Create**
    - Click ```Plus``` icon button on the right of the preset select window.
    - Or use ```Shift + A``` at node editor window then in ```Add``` > ```Nodes``` > ```Quick Menu``` > ```Fast Create Preset``` enter the new preset's name.
    Then a new preset recording the current selected nodes will be created:
- **Save** - select the nodes, click ```Save```, these selected nodes will be saved to the current selected preset.
- **Delete** - select the preset and click the ```Minus``` icon button on the right of the preset select window.
- **Reorder** - use the ```Up``` / ```Down``` icon button next to the preset select window.
- **Apply** - selected preset to the current editing node tree by pressing ```Apply``` or in ```Shift + A``` > ```Nodes```.

##### Textures in Preset
Hot Node supports automatically opening, settings image file for node containing image, and supports the modes below:
- ```Auto``` - Try to open image with mode ```Similar``` > ```Fixed Path``` > ```Stay Empty``` in order.
- ```Similar``` - Find the best matched image according to the name similarity algorithm in user set folder.
- ```Keys``` - Find the best matched image according to user defined keys in user set folder.
- ```Fixed Path``` - Open the same image with the original path.
- ```Stay Empty``` - Don't open image.

Settings of texutre applying:
- ```Tolerance``` - The tolerance of the image name comparation when the texture's mode is ```Similar```, higher means that more dissimilar images can pass the comparation and be loaded rather than using fixed path & stay empty. Default 0.50 as a moderate tolerance.
- ```Folder Path``` - The directory path to try find images when in ```Auto``` / ```Similar``` / ```Keys``` mode.

To modify texture preset:
1. Ensure your **last saved** preset contains the image node you want to edit.
2. Select the image node, then in ```Textures``` > ```Save```, select a ```Mode``` for this image.
3. If the mode is ```Keys```, you will need to enter key(s) for the image. You can have mutiple keys splited by ```/```, e.g. ```upper_body / base_color / .png```.
4. Click ```Save Texture``` button, and this image node will follow the new setting next time you apply the preset.


### Packs
Packs are folders storing presets.

##### Manage Packs
- **Create** - click the ```Plus``` icon button next to the pack slot.
- **Select** - click the ```Collecetion``` icon button on the left of the pack slot, choose one in the pop-up menu.
- **Rename** - just modify the pack name showed in the pack slot.
- **Delete** - click the ```Trash``` icon button, the current selected pack will be deleted.

##### Share Packs
Packs can be imported / exported as zip files. In ```Pack Sharing``` panel:
- **Import** - Click ```Import``` button to import pack(s). The waiting-for-import pack should be in .zip format.
- **Export** - Click ```Export``` button to export the current selected pack as a zip file.
- **Export All** - Click ```Export All``` button to export the all packs as zip files, useful for backup.


### Details of Usage
Here are some features in detail which may help you better using the Hot Node.

##### Undo & Redo
- ```Undo``` of ```Create```, ```Save```, ```Delete``` operations **haven't been supported yet**. For now you can turn on the ```Extra Comformation``` option in ```Node Preset Specials``` menu to prevent misoperation.

##### Keep Sync
When switched between .blend files and doing some operations, a warning may pop-up:
```
"Out of sync. Nothing happend but the add-on's auto refreshing. Now everything is ok!"
```
Just as the message said, Hot Node refreshed itself, and now you can do the things you want.
You can also refresh menually by clicking ```Refresh``` button.

##### Node Tree Interface Setup
If your preset contains nodes like ```NodeGroupInput```, or your preset type is geometry, a node tree interface containing IO sockets will be needed. Hot Node will check whether the tree interface is as same as the current edit tree's, and if not, check ```Overwrite Tree IO``` option in the ```Node Preset Specials``` menu to allow overwriting tree interface, or the links heading to IO nodes won't be created.

##### Texture Reuse
If exists a image having the same name with the auto matched image when applying preset, Hot Node will compare the file size and reuse the existing one if the size is the same, rather than loading the image with unique names like image.001.

##### Node Group Reuse
If exists a node group having the same name with the group that the preset is trying to setup, Hot Node will compare every inner node of them and reuse the existing one if the two groups are totally same, rather than create a new group with unique name like NodeGroup.001.


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