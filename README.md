# Hot Node 热节点

## ⭐ Features

⚡ **Save and add nodes across files in super fast speed.**

🖼️ Match image by name similarity and keyword.

📥 Import and export nodes pack.

📜 History system.

🌐 Language: English, 简体中文. (Welcome to translate! See the [Development Section](https://github.com/Trantor2098/hot_node/tree/main?tab=readme-ov-file#save-and-add-nodes) below.)

## ❤️ Donate
Via [Ko-fi](https://ko-fi.com/trantor) or [爱发电](https://afdian.com/a/trantor).

Hot Node takes a lot of time to develop. Your support really makes a difference.

## Usage
In Blender 4.2+, go `Edit` > `Preferences` > `Get Extensions`, search "Hot Node" and install.

Or, download zip via GitHub to install from disk.
### Save and add nodes
<img src="https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/1_Reuse_Cross_File.gif"/>


### Shift A to Add Nodes
<img src="https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/2_Shift_A_to_Access.gif"/>

### Match Image
<img src="https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/3_Match_Image.gif"/>

### History
<img src="https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/4_History.gif"/>

### Customize
<img src="https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/6_Customize.gif"/>

### More...
Hot Node features are easy to discover and understant, you can discover by your self. 

E.g. you can save nodes via context menu (right-click menu), import and export nodes pack, set node tree reuse mode, and disable the extend menu in preferences to have a orginal blender menu. etc. 

## Development

### Nodes Support
Hot Node has an code architecture with a relatively high degree of decoupling. It naturally supported some third-party nodes but does not guarantee 100% accuracy. 

You can add support for nodes and make adaptations for the new version of Blender by editing the module `core.serialization`, typically the `stg.py` and `adaptor.py` of each sub module. See [Blender Python API: bpy.types.Node](https://docs.blender.org/api/5.0/bpy.types.Node.html#bpy.types.Node) also.

### Add Translations
Hot Node uses `translations.csv` under `dev.tools` to store translations. You can add your language to it. See [Blender Locale Definiation](https://projects.staging.blender.org/blender/blender/src/branch/main/locale/languages) also.

## Credits

### Code Contributors
None for now. Join the development!

### Donors
None for now.

### Testing and Reporting
VictoryLuode, DKPress, m0dest-Wyp, 异次元学者, SatohamaUmika, cc, witty, Colin, ChyiZ_, 执念净化, et al.
There may be oversights on the name list, sincerely appreciate all of you again that helped to make Hot Node better :D


## License

Hot Node as a whole is licensed under the GNU General Public License, Version 3.
Individual files may have a different, but compatible license.