# Hot Node 热节点
## Features

🔥 **Save and add nodes across files in super fast speed.**

💡 Match Image / Share Nodes / Undo Redo / Custom Settings

🌐 English, 简体中文 - Welcome to translate! See [Development - Hot Node](https://github.com/Trantor2098/hot_node/tree/main?tab=readme-ov-file#save-and-add-nodes).

## Donate
**Via [Ko-fi](https://ko-fi.com/trantor) or [爱发电](https://afdian.com/a/trantor)**

**Hot Node takes a lot of time to maintain. Your support really makes a difference.**

## Usage
### Installation
In Blender 4.2+, go `Edit` > `Preferences` > `Get Extensions`, search "Hot Node" and install.

Or, download zip via GitHub to install from disk.

### Save and add nodes across files
![Save and add nodes](https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/1_Reuse_Cross_File.gif)


### Shift A to Add Nodes
Tip: click the icon, rather than click get.

![Shift A to Add Nodes](https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/2_Shift_A_to_Access.gif)


### Match Image
![Match Image](https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/3_Match_Image.gif)


### History
![History](https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/4_History.gif)


### Customize
![Customize](https://raw.githubusercontent.com/Trantor2098/hot_node/main/dev/git_attachments/6_Customize.gif)

### More
Hot Node features are easy to discover and understant, you can discover by your self. 

E.g. you can save nodes via context menu (right-click menu), import and export nodes pack, set node tree reuse mode, and disable the extend menu in preferences to have a orginal blender menu. etc. 

See also: [中文教程](https://www.bilibili.com/video/BV1LstpzkE5a/?spm_id_from=333.1387.homepage.video_card.click&vd_source=2168ae30c7a04aea1acec469c4a292a6)

## Development
### Nodes Support
Hot Node has an code architecture with a relatively high degree of decoupling. It naturally supported some third-party nodes but does not guarantee 100% accuracy. 

You can add support for nodes and make adaptations for the new version of Blender by editing the module `core.serialization`, typically the `stg.py` and `adaptor.py` of each sub module. See [Blender Python API: bpy.types.Node](https://docs.blender.org/api/5.0/bpy.types.Node.html#bpy.types.Node) also.

### Add Translations
Hot Node uses `translations.csv` under `dev.tools` to store translations. You can add your language to it. See [Blender Locale Definiation](https://projects.staging.blender.org/blender/blender/src/branch/main/locale/languages) also.

## Use Hot Node API
Feel free to use any code of Hot Node in your program.

### Parse and Set Nodes
1. Copy `core/serialization/` as a module into your package.
2. Search and replace the `utils`, `constants`, `file_manager`, and `user_prefs` with your implementation. These dependency can be easily reimplemented by reading their method name. You can also go to the relevant files to check the implementation.
3. In your main code, from `serialization/manager.py`, new a `SerializationManager` to get the singleton manager instance.
4. Use the method in `SerializationManager` such as `serialize_preset()`, `deserialize_preset()`.

## Credits
### Code Contributors
None for now. Join the development!

### Donors
热心B民, OR404NGE, 空物体blender, and others without leaving their name.

### Test and Report
VictoryLuode, DKPress, m0dest-Wyp, 异次元学者, SatohamaUmika, cc, witty, Colin, ChyiZ_, 执念净化, et al. And, others who were not recorded due to oversight.

## License
Hot Node as a whole is licensed under the GNU General Public License, Version 3.
Individual files may have a different, but compatible license.