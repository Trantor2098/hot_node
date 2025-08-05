def dev_reload():
    import importlib

    modules_to_reload = [
        "..core",
        "..core.blender",
        "..core.blender.keymap",
        "..core.blender.operators",
        "..core.blender.ui",
        "..core.blender.ui_context",
        "..core.blender.user_pref",
        # ..core.context.context", # issue with ui data-lacking if add this
        "..core.context",
        "..core.context.pack",
        "..core.context.preset",
        "..core.serialization.deserialize.adapter",
        "..core.serialization.deserialize.deserializer",
        "..core.serialization.deserialize.stg",
        "..core.serialization.serialize.adapter",
        "..core.serialization.serialize.serializer",
        "..core.serialization.serialize.stg",
        "..core.serialization.manager",
        "..services",
        "..services.autosave",
        "..services.history",
        "..services.sync",
        "..services.i18n",
        "..services.versioning",
        # "..utils.constants", # issue with path lacking if add this
        "..utils",
        "..utils.file_manager",
        "..utils.utils",
        "..utils.reporter",
        "..utils.legacy.node_parser",
        "..utils.legacy.node_setter",
        "..utils.legacy.versioning",
        ".dev_func",
        ".dev_ops",
        ".dev_ui",
        ".dev_utils",
    ]

    for mod in modules_to_reload:
        try:
            module = importlib.import_module(mod, __package__)
            importlib.reload(module)
        except Exception as e:
            print(f"[Hot Node Dev] Failed to reload {mod}: {e}")