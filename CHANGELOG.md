ChangeLog
========

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