ChangeLog
========


[0.8.0] - 2024-xx-xx
--------

### Added
- Custom pack icon supported.

### Fixed
- Newly generated node group data cannot be cleared if cancelling `Get` action.
- Node groups data will always be newed if their name is like "XXX.001", rather than reuse the existing groups.


[0.7.X] - 2024-XX-XX
--------

### Fixed
- Nodes with editable sockets whose sockets are less than their by default (e.g. `Menu Switch` gets 2 menus by default) cannot be set correctly. (Who will do this?)
- If node `Menu Switch`'s first item called "B", it will be changed to "B.001" when getting the preset.


[0.7.5] - 2024-11-14
--------

### Fixed
- Empty name of socket in the Group Input/Output crashes blender when getting the node from add-on with `Overwrite Tree I/O` on.
- Unnecessary warnings occur when getting a preset with `Menu` socket in it's Group Input/Output.
- Some error infos when opening blender from the command line.


[0.7.4] - 2024-11-08
--------

### Changed
- Now the node groups with the same namebody and the different suffix will not be compared or reused (like "NG" and "NG.001") when getting preset. This enhances the speed.

### Fixed
- If the name of a node group in the .blend file is like "NG.001", but there is no node group called "NG" in the file and the preset happend to have a node group called "NG", error will be thrown.
- Unnecessary rewriting of file happens when getting preset, which slows down the speed.


[0.7.3] - 2024-10-30
--------

### Changed
- Allowed to install in Blender 4.4 (not fully tested, use by your own risk).

### Fixed
- Importing illegal .zip files brings error.
- Node `Node Reroute` throws useless warning.


[0.7.2] - 2024-10-23
--------

### Changed
- Some severe error informations will be more readable, instead of being thrown by a scary exception window with codes.
- Some tiny errors of getting preset will be shown by the yellow warning.
- Historical files may remain in the folder when blender crashes. Now history will be automaticlly deleted 2 days after creation.

### Fixed
- Node `Bake` cannot be set correctly.
- Nesting a `Node Group` inside itself throws an error. Now it will throw a prompt instead.
- `Node Group` with missing data-blocks cannot be saved.
- Some useless console info.


[0.7.1] - 2024-10-22
--------

### Fixed
- Node `Index Switch` can not be set correctly.
- Node `Menu Switch` can not be set/get to/from preset correctly when it only have 2 sockets. And getting preset including this kind of node may ruin the whole pack.
- `Copy to Pack` can not pop-up overwrite warning if called by the button in settings bar.


[0.7.0] - 2024-09-22
--------

### Added
- Now you can update & create preset to any of your pack in the `Right Click` menu in node editor.
- `Ctrl + Shift + A` in node editor to add your custom nodes.
- `Ctrl + Shift + Alt + A` in node editor to manage your presets.

### Changed
- Now `In One Menu` is opened by default.
- Some UI details.


[0.6.4] - 2024-09-12
--------

### Fixed
- Fall back of image setting mode `Stay Empty` can not success, instead when image setting is failed, error will be thrown.
- `Fast Create Preset` can not push history correctly.
- When trying to save a single node and there are "/" or "\" in it's name, error will be thrown.
- `Repeat Zone` & `Simulation Zone` cause error.
- Location of `Reroute` whose parent is `NodeFrame` can not be set correctly.


[0.6.3] - 2024-09-08
--------

### Fixed
- Cross-file undo error.
- Sometimes add-on leaves residual history file.
- Sometimes `Shift A` menu leaves pack that only contains other type of nodes which should not appear. Now this can be solved by re-open the add-on or the blender.
- Incorrect panels' order in node group when using preset.
- Changing the name of the unselected preset causes error.
- If there is a image data in the .blend file and it's lost in the disk and your preset happen to have that image, errors will be thrown.


[0.6.2] - 2024-09-07
--------

### Fixed
- `Set Texture` causes error.


[0.6.1] - 2024-09-07
--------

### Fixed
- Node `File Output` causes error.
- Node `Menu Switch` lost items sometimes.
- Improved performance and downward compatibility of presets.


[0.6.0] - 2024-09-06
--------

### Add
- Simplified Chinese supported / 全面支持简体中文.
- Move / copy preset into another pack.
- Optional UI setting: Bigger `Get` (`Apply` in previous) button, smaller `Set` (`Save` in previous) button (default open).
- Optional UI setting: Utilities Bar & Settings Bar.
- Improved performance.

### Changed
- `Apply` renamed to `Get`, `Save` renamed to `Set`.
- Other UI naming details.

### Fixed
- Changing name of the pack makes it disappear in `Shift A` menu.
- Node `Menu Switch` causes error.
- Undo redo of `Delete All Presets` causes error.
- Risk of losing history steps.


[0.5.3] - 2024-08-29
--------

### Changed
- Reduce data file size by 1/3 (by removing indents).
- UI layout changes.
- Improved stability.

### Fixed
- Undo redo cannot work on old blender files.
- Node `Color Balance` cannot be set correctly.
- Incorrect presets panel when opened a .blend file.
- Sometimes packs disappear on `Shift A` menu.
- Sometimes re-enabling add-on throws errors.

### Recent Features
- **Undo & Redo Supported.**


[0.5.2] - 2024-08-26
--------

### Fixed
- Error occurs when applying preset with ```Repeat Zone```.
- Emergency repaired pack import / recover error of 0.5.1.


[0.5.1] - 2024-08-26
--------

### Fixed
- Error occurs when applying preset with ```Repeat Zone```.


[0.5.0] - 2024-08-24
--------

### Added
- **Undo & Redo Supported.**
- Stability significantly improved.

### Changed
- Improved UI performance in ```Shift A``` menu.
Now you can see all your packs in ```Shift A``` and choose whether to join them into one menu.
- Preset name will be auto setted to the node name when creating preset with single selected node.

### Deprecated
- ```Extra Confirmation``` checker.

### Fixed
- Undo causes error.
- Node ```Capture Attribute``` causes error.
- Improved stability of ```Node Group```.
- Improved stability of exporting packs.


[0.4.2] - 2024-08-01
--------

### Fixed
- Applying textures will cause error. Now it won't.


[0.4.1] - 2024-08-05
--------

### Fixed
- Renaming presets will cause error. Now it's fixed.
- Nodes containing ```Curve``` can't be added correctly. Now it's fixed.


[0.4.0] - 2024-08-03
--------

### Added
- Auto sync supported. Now you don't need to click ```Refresh``` for most of the time.
- All node presets can be accessed in ```Shift + A``` menu without switching packs now.

### Changed
- Moved fast nodes saving to the right clicking menu of node editor.

### Removed
- ```Refresh``` button on the panel ```Nodes```.

### Fixed
- Rename pack to "" (empty) will cause error. Now pack & preset's name cannot be empty.
- Fast nodes saving can be executed when there is no pack selected. Now it can't.


[0.3.1] - 2024-08-01
--------

### Fixed
- Cannot find the path "...\hot_node_autosave"


[0.3.0] - 2024-07-30
--------

### Added
- ★ Packs won't be lost in the future version updating (for this time you still need to export all packs for backup!).
- Packs will be auto saved to system's TEMP folder when opening & closing blender and will remain 2 days, and can be recovered via ```Recover``` button.

### Changed
- Some UI details.

### Removed
- Removed CHANGELOG & README file in the add-on package. You can still find them on Hot Node's github repository.

### Fixed
- **Severe BUG:** When exporting all packs, if the directory exists a re-named pack.zip, your exported pack with a auto set unique name like pack.001.zip will be empty. Now it's fixed.


[0.2.1] - 2024-07-29
--------

### Fixed
- Now error info won't appear on console when selecting a pack.


[0.2.0] - 2024-07-25
--------

### Added
- Shift + A menu is now supported, use it just like adding a single node!
- Quick preset creation added to the Shift + A menu.
- Export all packs suppported.

### Changed
- When press ```Apply``` on the side bar, the newly created nodes will attach to the mouse for moving, rather than stay in a fixed location. 

### Fixed
- Node frames perform well now.
- Removed some useless console info.


[0.1.0] - 2024-07-17
--------

### Added
- Save node presets and keep them update across any .blend files in real-time.
- Load image by automaticlly seraching and set their color-space & alpha mode.
- Share nodes light-weightly without a big .blend file as it's library (usually a preset pack is smaller than 1 MiB).

### Security
- This add-on is currently in **beta**. For now it's safer not to join it into your important project workflow.
- Undo of Create, Save, Delete operations haven't been supported yet. For now you can turn on the Extra Comformation option in Node Preset Specials menu to prevent misoperation.
- If have ```NodeFrame``` as node's parent, the frame's ```location``` will be unpredictable.
- if have nested ```NodeFrame```, when first created and with auto create select, dragging will make them dance crazily. for now the solution is clicking some where then select them again...