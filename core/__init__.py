from . import context, blender

def startup():
    """Called when the app starts, initializes the core components."""
    blender.user_pref.register()
    
    context.startup()
    
    blender.operators.register()
    blender.ui.register()
    blender.ui_context.register()
    
def shutdown():
    """Called when the app shuts down, cleans up the core components."""
    blender.ui.unregister()
    blender.ui_context.unregister()
    blender.operators.unregister()
    
    context.shutdown()
    
    blender.user_pref.unregister()