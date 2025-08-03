from . import context

def startup():
    """Initialize the context on Addon startup."""
    context.Context.initialize()
    
def shutdown():
    """Clean up the context on Addon shutdown."""
    context.Context.reset()