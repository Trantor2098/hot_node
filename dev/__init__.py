def register():
    from . import dev_ops, dev_ui
    try:
        dev_ops.register()
    except Exception as e:
        print(f"Error during dev_ops startup: {e}")
    try:
        dev_ui.register()
    except Exception as e:
        print(f"Error during dev_ui startup: {e}")


def unregister():
    from . import dev_ops, dev_ui
    try:
        dev_ops.unregister()
    except Exception as e:
        print(f"Error during dev_ops unregister: {e}")
    try:
        dev_ui.unregister()
    except Exception as e:
        print(f"Error during dev_ui unregister: {e}")