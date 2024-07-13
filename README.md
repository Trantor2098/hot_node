<!--
Keep this document short & concise,
linking to external resources instead of including content in-line.
See 'release/text/readme.html' for the end user read-me.
-->

Hot Node
========
Save, apply, share node presets across files in real-time, light-weightly.

Requirement
--------
- Blender 4.0 and later compatible.

Features
--------
- Save node presets and keep them update across any .blend files in real-time.
- Load image by automaticlly seraching and set their colorspace & alpha mode.
- Share nodes light-weightly without a big .blend file as it's library (usually a preset pack is smaller than 1 MiB).


Installation
--------
- For blender 4.2 and later, consider installing via [blender extension system](https://extensions.blender.org/about/).
- Or you can download the zip file and follow the [blender add-on installation guide](https://docs.blender.org/manual/en/4.2/extensions/addons.html).

After Hot Node was installed, you will be able to see the Hot Node Panel in node editor's sidebar.


Usage
--------
### Before Using It
- This add-on is currently in **beta**, for now it's safer not to join it into your important project workflow.
- Simulation zone input / output nodes **haven't been supported** yet. Applying them will throw an error.
- "Create", "Save", "Delete" operations **cannot be undo** in current version of Hot Node. For now you can open the "Extra Comformation" option in Node Preset Specials Menu to prevent misoperation.

### Refresh
When newly opened a .blend file / switched between .blend file / newly enabled hot node add-on, you should click Node Preset > Node Preset Specials (a drop-down menu next to the preset select window) > Refresh Presets & Packs, to let the preset data be in sync.

If not doing this, a warning may pupop: "Out of sync. Nothing happend but the add-on's auto refreshing. Now everything is ok!". This means your cross-file operation is out of sync. Nothing happend but the add-on's auto refreshing, and then you can do operations normally.

### Manage Preset Pack
- To create / select pack, in Node Preset panel, you can select a preset pack by clicking the collecetion box icon button on the left of the pack slot. If there is no pack yet, click the plus icon button next to the pack slot to create one.
- To rename pack, The pack slot shows the pack's name and you can rename the pack here.
- To delete pack, Click the trash icon button to delete the current pack.

### Manage Preset
- To create node preset, select the nodes, click the plus icon button on the right of the preset select window, a new preset recording the selected nodes will be created. Or you can just create an empty preset and save things to it later.
- To save node preset, select the nodes, click the button "Save" to save nodes to the current selected preset.
- To delete preset, select the preset and click the minus icon button on the right of the preset select window.
- To reorder presets, use the up / down icon button next to the preset select window.

### Apply Preset
Select a pack and a preset, click the button "Apply" to generate nodes. Operations like applying a Shader Node Preset to a Geometry Node Tree won't be successed.

### Texture Preset Mode
Hot Node have several texture saving mode:
- Auto - Try to open image with mode "Compare" > "Fixed Path" > "Stay Empty" in order.
- Compare - Find the best matched image according to the name similarity algorithm in user set folder.
- Keys - Find the best matched image according to user defined keys in user set folder.
- Fixed Path - Open the same image with the original path.
- Stay Empty - Don't open image.

The default "default mode when save the preset" is Auto and can be changed in special menu.

### Texture Preset Apply Settings
In Textures > Apply, there are two settings:
- Tolerance - The tolerance of the image name comparation, higher means that more dissimilar images can pass the comparation and be loaded rather than using fixed path & stay empty. Default 0.50 as a moderate tolerance.
- Folder Path - The directory path to try find images when in Auto / Compare / Key Words mode.

### Save Texture Preset
To save some image in specific mode, do:
1. Save the node preset first, ensure your last saved preset contains the image node you want to edit.
2. Select the image node, then in Textures > Save, select a mode for this image.
3. If the mode is "Keys", you will need to enter key(s) for the image.
4. Click button "Save Texture", this image node will follows the new settings next time you apply the preset.

### Pack Sharing
Packs can be imported / exported as zip files. 
- Import - Click the button "Import" to import pack(s).
- Export - Select the pack in the panel then click the button "Export" to export the pack as a zip file for sharing.


Known Bugs
--------
- Simulation zone input / output nodes haven't been supported yet. Applying them will throw an error.
- If have node frames as node's parent, the frame's location will be unpredictable.


Future Plan
--------
- Support apply / save preset as a material or geometry node modifier directly on an viewport object.
- Support one-click inserting Hot Node as a module for other add-ons to easily generate nodes.
- Support undo, redo.
- Support adding linked object of the node socket if the object is simple enough.
- Maybe will support drivers of the node socket.
- Some other features...


License
--------

Hot Node as a whole is licensed under the GNU General Public License, Version 3.
Individual files may have a different, but compatible license.